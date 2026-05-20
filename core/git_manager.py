"""Git operations manager for safe agent collaboration."""
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
import git
from git.exc import GitCommandError

class GitManager:
    """Manages git operations for agent workflow."""
    
    def __init__(self, project_path: Path, main_branch: str = "main"):
        self.project_path = Path(project_path)
        self.main_branch = main_branch
        self.repo = None
        self._init_repo()
    
    def _init_repo(self):
        """Initialize git repository connection."""
        try:
            self.repo = git.Repo(self.project_path)
        except git.InvalidGitRepositoryError:
            raise ValueError(f"Not a git repository: {self.project_path}")
    
    def get_current_branch(self) -> str:
        """Get current branch name."""
        return self.repo.active_branch.name
    
    def is_clean(self) -> bool:
        """Check if working directory is clean."""
        return not self.repo.is_dirty(untracked_files=True)
    
    def create_branch(self, task_id: str, agent_name: str) -> str:
        """Create a new feature branch for a task.

        Args:
            task_id: Unique task identifier
            agent_name: Name of the agent working on this

        Returns:
            Branch name
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"agent/{agent_name}/{task_id}-{timestamp}"

        # Sanitize branch name
        branch_name = re.sub(r'[^a-zA-Z0-9/_-]', '-', branch_name)

        # Check for uncommitted changes before switching
        if not self.is_clean():
            self.stage_files()
            self.commit(f"Auto-commit before switching to {branch_name}")
            # If still dirty (e.g., stash needed), try stash
            if self.repo.is_dirty(untracked_files=True):
                self.repo.git.stash('push', '--include-untracked',
                                    '-m', f'Auto-stash before {branch_name}')

        # Checkout main first
        self.repo.git.checkout(self.main_branch)

        # Pull latest changes
        try:
            self.repo.git.pull('origin', self.main_branch)
        except GitCommandError:
            pass  # May fail if no remote

        # Create and checkout new branch
        self.repo.git.checkout('-b', branch_name)

        return branch_name
    
    def stage_files(self, files: Optional[List[str]] = None):
        """Stage files for commit.
        
        Args:
            files: List of file paths to stage. If None, stages all changes.
        """
        if files:
            self.repo.git.add(files)
        else:
            self.repo.git.add('-A')
    
    def commit(self, message: str, author_name: str = "Agent", author_email: str = "agent@orchestrator.local"):
        """Commit staged changes.
        
        Args:
            message: Commit message
            author_name: Author name
            author_email: Author email
        """
        # Configure commit author
        with self.repo.config_writer() as cw:
            cw.set_value("user", "name", author_name)
            cw.set_value("user", "email", author_email)
        
        self.repo.git.commit('-m', message)
    
    def commit_agent_changes(self, agent_name: str, task_description: str, files_changed: List[str]):
        """Commit changes made by an agent.
        
        Args:
            agent_name: Name of the agent
            task_description: Description of what was done
            files_changed: List of files that were changed
        """
        if not files_changed:
            return
        
        # Stage only the files the agent touched
        self.stage_files(files_changed)
        
        # Create commit message
        file_list = ', '.join([Path(f).name for f in files_changed[:5]])
        if len(files_changed) > 5:
            file_list += f' and {len(files_changed) - 5} more'
        
        message = f"[{agent_name}] {task_description}\n\nFiles: {file_list}"
        self.commit(message, author_name=agent_name)
    
    def get_diff(self, branch: Optional[str] = None) -> str:
        """Get diff of changes.
        
        Args:
            branch: Branch to compare. If None, compares current branch to main.
            
        Returns:
            Diff string
        """
        if branch is None:
            branch = self.get_current_branch()
        
        try:
            diff = self.repo.git.diff(f'{self.main_branch}...{branch}')
            return diff
        except GitCommandError as e:
            return f"Error getting diff: {e}"
    
    def get_changed_files(self, branch: Optional[str] = None) -> List[str]:
        """Get list of changed files.
        
        Args:
            branch: Branch to check. If None, uses current branch.
            
        Returns:
            List of changed file paths
        """
        if branch is None:
            branch = self.get_current_branch()
        
        try:
            output = self.repo.git.diff(f'{self.main_branch}...{branch}', '--name-only')
            return [f.strip() for f in output.split('\n') if f.strip()]
        except GitCommandError:
            return []
    
    def merge_branch(self, branch: str, message: Optional[str] = None) -> Tuple[bool, str]:
        """Merge a branch into main.

        Args:
            branch: Branch to merge
            message: Merge commit message

        Returns:
            Tuple of (success, message)
        """
        try:
            # Checkout main
            self.repo.git.checkout(self.main_branch)

            # Pull latest
            try:
                self.repo.git.pull('origin', self.main_branch)
            except GitCommandError:
                pass

            # Merge
            merge_msg = message or f"Merge {branch}"
            self.repo.git.merge(branch, '-m', merge_msg, '--no-ff')

            return True, f"Successfully merged {branch} into {self.main_branch}"

        except GitCommandError as e:
            try:
                self.repo.git.merge('--abort')
            except GitCommandError:
                pass
            return False, f"Merge failed: {e}"
    
    def delete_branch(self, branch: str, force: bool = False):
        """Delete a branch.
        
        Args:
            branch: Branch to delete
            force: Force delete even if not merged
        """
        try:
            # Checkout main first
            self.repo.git.checkout(self.main_branch)
            
            # Delete branch
            if force:
                self.repo.git.branch('-D', branch)
            else:
                self.repo.git.branch('-d', branch)
        
        except GitCommandError as e:
            raise ValueError(f"Failed to delete branch {branch}: {e}")
    
    def rollback_branch(self, branch: str):
        """Delete a branch and all its changes.
        
        Args:
            branch: Branch to rollback
        """
        # Checkout main
        self.repo.git.checkout(self.main_branch)
        
        # Force delete the branch
        self.delete_branch(branch, force=True)
    
    def get_commit_history(self, branch: Optional[str] = None, count: int = 10) -> List[dict]:
        """Get commit history for a branch.
        
        Args:
            branch: Branch to check. If None, uses current.
            count: Number of commits to retrieve
            
        Returns:
            List of commit info dicts
        """
        branch = branch or self.get_current_branch()
        commits = []
        
        for commit in self.repo.iter_commits(branch, max_count=count):
            commits.append({
                'hash': commit.hexsha[:8],
                'message': commit.message.strip(),
                'author': commit.author.name,
                'date': commit.committed_datetime.isoformat()
            })
        
        return commits
    
    def push_branch(self, branch: Optional[str] = None, remote: str = 'origin'):
        """Push branch to remote.
        
        Args:
            branch: Branch to push. If None, uses current.
            remote: Remote name
        """
        branch = branch or self.get_current_branch()
        
        try:
            self.repo.git.push(remote, branch)
        except GitCommandError as e:
            # Branch might not exist on remote yet
            try:
                self.repo.git.push('-u', remote, branch)
            except GitCommandError as e2:
                raise ValueError(f"Failed to push branch: {e2}")