"""Tests for orchestrator core operations."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestOrchestratorInit:
    """Test orchestrator initialization."""

    def test_smoke_init(self, monkeypatch, tmp_path):
        """Orchestrator initializes without errors."""
        import os, subprocess, importlib
        import config.settings
        project_dir = tmp_path / "projects" / "default"
        project_dir.mkdir(parents=True)
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        # Setup minimal env
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test12345")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
        monkeypatch.setenv("PROJECT_PATH", str(project_dir))
        monkeypatch.setenv("PROJECT_TYPE", "generic")
        monkeypatch.setenv("STATE_FILE", str(state_dir / "orchestrator_state.json"))
        monkeypatch.setenv("TASKS_FILE", str(state_dir / "tasks.json"))
        monkeypatch.setenv("LOG_FILE", str(state_dir / "logs" / "orchestrator.log"))
        monkeypatch.setenv("CUSTOM_SKILLS_DIR", str(state_dir / "skills" / "custom"))

        # Create empty git repo to satisfy GitManager
        import subprocess
        subprocess.run(
            ["git", "init", "--initial-branch=main"],
            cwd=str(project_dir), capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(project_dir), capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=str(project_dir), capture_output=True
        )
        (project_dir / "README.md").write_text("# Test\n")
        subprocess.run(
            ["git", "add", "."],
            cwd=str(project_dir), capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=str(project_dir), capture_output=True
        )

        from config.settings import Config

        # Force-reload Config
        import importlib
        import config.settings
        importlib.reload(config.settings)
        from config.settings import Config as FreshConfig

        # Set test paths directly
        FreshConfig.PROJECT_PATH = Path(project_dir)
        FreshConfig.STATE_FILE = state_dir / "orchestrator_state.json"
        FreshConfig.TASKS_FILE = state_dir / "tasks.json"
        FreshConfig.LOG_FILE = state_dir / "logs" / "orchestrator.log"
        FreshConfig.CUSTOM_SKILLS_DIR = state_dir / "skills" / "custom"
        FreshConfig.OPENAI_API_KEY = "sk-test12345"
        FreshConfig.TELEGRAM_BOT_TOKEN = ""
        FreshConfig.PROJECT_TYPE = "generic"

        # Ensure dirs
        FreshConfig.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        FreshConfig.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        FreshConfig.CUSTOM_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

        from orchestrator import Orchestrator
        orch = Orchestrator()

        assert orch is not None
        assert orch.role_manager is not None
        assert orch.delegation is not None
        assert orch.git is not None
        assert orch.validator is not None
        assert orch.state is not None
        assert orch.cost_tracker is not None
        assert orch.rate_limiter is not None
        assert orch.quota_manager is not None
        assert orch.perf_tracker is not None
        assert orch.audit_logger is not None

        # Audit logger logged startup
        entries = orch.audit_logger.entries
        assert len(entries) >= 1
        assert entries[0]["event_type"] == "system"
        assert entries[0]["action"] == "orchestrator_started"


class TestOrchHelpers:
    """Test orchestrator helper methods."""

    def test_audit_logger_events(self, monkeypatch, tmp_path):
        """Audit logger captures task lifecycle events."""
        import os, subprocess, importlib
        import config.settings

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        subprocess.run(
            ["git", "init", "--initial-branch=main"],
            cwd=str(project_dir), capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=str(project_dir), capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=str(project_dir), capture_output=True
        )
        (project_dir / "file.txt").write_text("x")
        subprocess.run(["git", "add", "."], cwd=str(project_dir), capture_output=True)
        subprocess.run(["git", "commit", "-m", "x"], cwd=str(project_dir), capture_output=True)

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
        monkeypatch.setenv("PROJECT_PATH", str(project_dir))
        monkeypatch.setenv("STATE_FILE", str(state_dir / "orchestrator_state.json"))
        monkeypatch.setenv("TASKS_FILE", str(state_dir / "tasks.json"))
        monkeypatch.setenv("LOG_FILE", str(state_dir / "logs" / "orchestrator.log"))
        monkeypatch.setenv("CUSTOM_SKILLS_DIR", str(state_dir / "skills" / "custom"))

        importlib.reload(config.settings)
        from config.settings import Config as Cfg

        Cfg.PROJECT_PATH = Path(project_dir)
        Cfg.STATE_FILE = state_dir / "orchestrator_state.json"
        Cfg.TASKS_FILE = state_dir / "tasks.json"
        Cfg.LOG_FILE = state_dir / "logs" / "orchestrator.log"
        Cfg.CUSTOM_SKILLS_DIR = state_dir / "skills" / "custom"
        Cfg.OPENAI_API_KEY = "sk-test"
        Cfg.TELEGRAM_BOT_TOKEN = ""
        Cfg.PROJECT_TYPE = "generic"
        Cfg.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        Cfg.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        Cfg.CUSTOM_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

        from orchestrator import Orchestrator
        orch = Orchestrator()

        # Manually trigger callbacks to test audit logging
        from agents.roles import AgentRole, AgentInstance
        from agents.delegation import DelegatedTask

        role = AgentRole(role_id="test", name="Test", description="Test role")
        agent = AgentInstance(
            instance_id="test-agent",
            name="Test Agent",
            role_id="test"
        )
        task = DelegatedTask(
            task_id="audit-task-1",
            title="Audit Test Task",
            description="Test audit logging",
        )

        orch.role_manager.roles["test"] = role
        orch.role_manager.instances["test-agent"] = agent

        orch._on_task_created(task)
        orch._on_task_assigned(task, agent)
        orch._on_task_completed(task)

        entries = orch.audit_logger.get_entries(event_type="task")
        assert len(entries) >= 2  # created + completed

        created_events = [e for e in entries if e["action"] == "created"]
        completed_events = [e for e in entries if e["action"] == "completed"]

        assert len(created_events) >= 1
        assert len(completed_events) >= 1

        # Assignment is an agent-level event
        agent_entries = orch.audit_logger.get_entries(event_type="agent")
        assigned_events = [e for e in agent_entries if e["action"] == "assigned"]
        assert len(assigned_events) >= 1


class TestQuotaManagement:
    """Test TokenQuotaManager operations."""

    def test_check_quota_within_limit(self):
        from core.rate_limiter import TokenQuotaManager
        qm = TokenQuotaManager(max_tokens_per_request=4000, max_tokens_per_task=50000)
        assert qm.check_task_quota("task-1") is True

    def test_record_and_check_quota(self):
        from core.rate_limiter import TokenQuotaManager
        qm = TokenQuotaManager(max_tokens_per_task=100)
        qm.record_token_usage("task-1", 80)
        assert qm.check_task_quota("task-1") is True
        qm.record_token_usage("task-1", 30)
        assert qm.check_task_quota("task-1") is False

    def test_remaining_tokens(self):
        from core.rate_limiter import TokenQuotaManager
        qm = TokenQuotaManager(max_tokens_per_task=1000)
        qm.record_token_usage("task-x", 300)
        assert qm.get_remaining_task_tokens("task-x") == 700

    def test_get_task_usage(self):
        from core.rate_limiter import TokenQuotaManager
        qm = TokenQuotaManager(max_tokens_per_task=500)
        qm.record_token_usage("task-a", 100)
        usage = qm.get_task_usage("task-a")
        assert usage["tokens_used"] == 100
        assert usage["tokens_remaining"] == 400
        assert usage["quota_limit"] == 500

    def test_reset_task(self):
        from core.rate_limiter import TokenQuotaManager
        qm = TokenQuotaManager(max_tokens_per_task=500)
        qm.record_token_usage("task-b", 200)
        qm.reset_task("task-b")
        assert qm.get_remaining_task_tokens("task-b") == 500


class TestCostTracking:
    """Test cost tracking integration."""

    def test_record_usage_returns_cost(self, tmp_path):
        from core.cost_tracker import CostTracker
        ct = CostTracker(tmp_path, daily_budget_limit=10.0)
        cost = ct.record_usage(
            model="gpt-4o",
            prompt_tokens=100,
            completion_tokens=50,
            agent_name="test",
            task_id="test-task"
        )
        assert isinstance(cost, float)
        assert cost >= 0
        assert len(ct.usage_log) == 1


class TestRoleDeletionGuard:
    """Test role deletion guards."""

    def test_cannot_delete_default_role(self, tmp_path):
        from agents.roles import AgentRoleManager
        rm = AgentRoleManager(tmp_path)
        with pytest.raises(ValueError, match="Cannot delete default role"):
            rm.delete_role("ceo")

    def test_can_delete_custom_role(self, tmp_path):
        from agents.roles import AgentRole, AgentRoleManager
        rm = AgentRoleManager(tmp_path)
        custom = AgentRole(
            role_id="custom_role",
            name="Custom",
            description="A custom role",
        )
        rm.create_role(custom)
        assert rm.delete_role("custom_role") is True
        assert rm.get_role("custom_role") is None

    def test_defaults_not_in_file_after_save(self, tmp_path):
        """Default roles are NOT persisted to file."""
        from agents.roles import AgentRole, AgentRoleManager
        import json

        rm = AgentRoleManager(tmp_path)
        custom = AgentRole(
            role_id="my_custom",
            name="My Custom",
            description="Test",
        )
        rm.create_role(custom)

        # Reload the file
        data = json.loads(rm.roles_file.read_text())
        assert "ceo" not in data
        assert "cto" not in data
        assert "senior_engineer" not in data
        assert "my_custom" in data


class TestMaxConcurrentTasks:
    """Test max_concurrent_tasks enforcement."""

    def test_busy_agent_skipped(self, tmp_path):
        from agents.roles import AgentRoleManager, AgentRole, AgentInstance
        from skills.registry import SkillRegistry, SkillModule, get_skill_registry

        rm = AgentRoleManager(tmp_path)
        registry = SkillRegistry()

        role = AgentRole(
            role_id="worker",
            name="Worker",
            description="Does work",
            skills=["python"],
            max_concurrent_tasks=0,  # Can never take tasks
        )
        rm.roles["worker"] = role

        agent = AgentInstance(
            instance_id="busy-agent",
            name="Busy Agent",
            role_id="worker",
            status="idle",
        )
        rm.instances["busy-agent"] = agent

        result = rm.find_best_agent_for_task("write python code", registry)
        # Should return None because max_concurrent_tasks=0 blocks all
        assert result is None
