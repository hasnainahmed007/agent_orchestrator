"""Tests for git manager module."""
import pytest
from pathlib import Path


class TestGitManager:
    """Test GitManager operations (requires git)."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary git repository."""
        import subprocess
        from core.git_manager import GitManager

        repo_path = tmp_path / "test_project"
        repo_path.mkdir()

        # Initialize git repo with main branch
        subprocess.run(
            ["git", "init", "--initial-branch=main"],
            cwd=str(repo_path), capture_output=True, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(repo_path), capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(repo_path), capture_output=True
        )
        # Create initial commit so branches work
        (repo_path / "README.md").write_text("# Test\n")
        subprocess.run(
            ["git", "add", "."],
            cwd=str(repo_path), capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=str(repo_path), capture_output=True
        )

        return GitManager(repo_path)

    def test_init_repo(self, temp_repo):
        """GitManager initializes with a valid repo."""
        assert temp_repo.repo is not None

    def test_init_non_git_dir(self, tmp_path):
        """GitManager raises on non-git directory."""
        from core.git_manager import GitManager
        empty_dir = tmp_path / "not_repo"
        empty_dir.mkdir()
        with pytest.raises(ValueError, match="Not a git repository"):
            GitManager(empty_dir)

    def test_get_current_branch(self, temp_repo):
        """Current branch is main."""
        assert temp_repo.get_current_branch() == "main"

    def test_is_clean(self, temp_repo):
        """Fresh repo is clean."""
        assert temp_repo.is_clean() is True

    def test_is_dirty_after_file_change(self, temp_repo):
        """Repo becomes dirty after file change."""
        (temp_repo.project_path / "new_file.txt").write_text("hello")
        assert temp_repo.is_clean() is False

    def test_create_branch(self, temp_repo):
        """Create a feature branch."""
        branch = temp_repo.create_branch("task-001", "test-agent")
        assert branch.startswith("agent/test-agent/task-001-")
        assert temp_repo.get_current_branch() == branch

    def test_create_branch_with_dirty_tree(self, temp_repo):
        """Create branch autocleans dirty tree."""
        (temp_repo.project_path / "dirty.txt").write_text("uncommitted")
        branch = temp_repo.create_branch("task-002", "agent-x")
        assert branch.startswith("agent/agent-x/task-002-")
        assert temp_repo.is_clean() is True

    def test_stage_and_commit(self, temp_repo):
        """Stage and commit changes."""
        (temp_repo.project_path / "code.py").write_text("print('hello')")
        temp_repo.stage_files(["code.py"])
        temp_repo.commit("Add code.py", author_name="TestAgent")
        assert temp_repo.is_clean() is True

    def test_stage_all(self, temp_repo):
        """Stage all changes with -A."""
        (temp_repo.project_path / "a.py").write_text("a")
        (temp_repo.project_path / "b.py").write_text("b")
        temp_repo.stage_files()
        temp_repo.commit("Add all", author_name="Bot")
        assert temp_repo.is_clean() is True

    def test_commit_agent_changes(self, temp_repo):
        """Commit agent changes helper."""
        (temp_repo.project_path / "agent_work.py").write_text("work")
        temp_repo.commit_agent_changes(
            "Alice", "Implemented feature X", ["agent_work.py"]
        )
        assert temp_repo.is_clean() is True

    def test_commit_agent_changes_no_files(self, temp_repo):
        """Commit with no files is a no-op."""
        temp_repo.commit_agent_changes("Alice", "Nothing done", [])
        assert temp_repo.is_clean() is True

    def test_get_diff(self, temp_repo):
        """Get diff between branches."""
        branch = temp_repo.create_branch("task-003", "agent")
        (temp_repo.project_path / "changed.py").write_text("changed")
        temp_repo.stage_files()
        temp_repo.commit("Changes", author_name="Agent")
        diff = temp_repo.get_diff(branch)
        assert "changed.py" in diff or "+changed" in diff

    def test_get_changed_files(self, temp_repo):
        """Get list of changed files between branches."""
        branch = temp_repo.create_branch("task-004", "agent")
        (temp_repo.project_path / "feature.py").write_text("feature")
        temp_repo.stage_files()
        temp_repo.commit("Feature", author_name="Agent")
        files = temp_repo.get_changed_files(branch)
        assert len(files) > 0
        assert "feature.py" in files

    def test_merge_branch_success(self, temp_repo):
        """Merge a branch into main."""
        branch = temp_repo.create_branch("task-005", "agent")
        (temp_repo.project_path / "merged.py").write_text("merged")
        temp_repo.stage_files()
        temp_repo.commit("Mergeable", author_name="Agent")
        success, msg = temp_repo.merge_branch(branch)
        assert success is True
        assert "Successfully merged" in msg
        assert temp_repo.get_current_branch() == "main"

    def test_merge_branch_conflict(self, temp_repo):
        """Merge conflict returns failure (does not leave mid-merge)."""
        import subprocess

        branch = temp_repo.create_branch("task-conflict", "agent")
        (temp_repo.project_path / "conflict.py").write_text("branch-version")
        temp_repo.stage_files()
        temp_repo.commit("Branch version", author_name="Agent")

        # Go back to main, make conflicting change
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=str(temp_repo.project_path), capture_output=True
        )
        (temp_repo.project_path / "conflict.py").write_text("main-version")
        temp_repo.stage_files()
        temp_repo.commit("Main version", author_name="Other")

        success, msg = temp_repo.merge_branch(branch)
        assert success is False
        assert "Merge failed" in msg
        # Git should be aborted, back on main
        assert temp_repo.get_current_branch() == "main"

    def test_delete_branch(self, temp_repo):
        """Delete a merged branch."""
        branch = temp_repo.create_branch("task-006", "agent")
        (temp_repo.project_path / "tmp.py").write_text("tmp")
        temp_repo.stage_files()
        temp_repo.commit("Temp", author_name="Agent")
        # Merge first so branch can be deleted without force
        import subprocess
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=str(temp_repo.project_path), capture_output=True
        )
        subprocess.run(
            ["git", "merge", branch, "--no-ff", "-m", "merge"],
            cwd=str(temp_repo.project_path), capture_output=True
        )
        temp_repo.delete_branch(branch)

    def test_delete_branch_force(self, temp_repo):
        """Force delete an unmerged branch."""
        branch = temp_repo.create_branch("task-007", "agent")
        (temp_repo.project_path / "unmerged.py").write_text("unmerged")
        temp_repo.stage_files()
        temp_repo.commit("Unmerged", author_name="Agent")
        temp_repo.delete_branch(branch, force=True)

    def test_rollback_branch(self, temp_repo):
        """Rollback deletes branch and returns to main."""
        branch = temp_repo.create_branch("task-rollback", "agent")
        (temp_repo.project_path / "bad.py").write_text("bad code")
        temp_repo.stage_files()
        temp_repo.commit("Bad", author_name="Agent")
        temp_repo.rollback_branch(branch)
        assert temp_repo.get_current_branch() == "main"

    def test_get_commit_history(self, temp_repo):
        """Get commit history."""
        history = temp_repo.get_commit_history("main", count=5)
        assert len(history) >= 1
        assert "hash" in history[0]
        assert "message" in history[0]
        assert "author" in history[0]

    def test_sanitize_branch_name(self, temp_repo):
        """Branch names are sanitized."""
        branch = temp_repo.create_branch("task with spaces!", "bad@name")
        assert " " not in branch
        assert "@" not in branch

    def test_push_pull_no_remote(self, temp_repo):
        """push_branch gracefully handles missing remote."""
        branch = temp_repo.get_current_branch()
        with pytest.raises(ValueError):
            temp_repo.push_branch(branch)
