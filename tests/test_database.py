"""Tests for database layer (SQLite mode)."""
import json
import pytest
from pathlib import Path


class TestDatabaseSQLite:
    """Test DatabaseManager with SQLite backend."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a temporary SQLite database."""
        from core.database import DatabaseManager
        db_path = tmp_path / "test.db"
        return DatabaseManager(f"sqlite:///{db_path}")

    def test_save_and_get_role(self, db):
        role_data = {"name": "Test Role", "skills": ["python"]}
        db.save_role("test_role", role_data)
        result = db.get_role("test_role")
        assert result is not None
        assert result["name"] == "Test Role"
        assert result["skills"] == ["python"]

    def test_save_role_updates(self, db):
        db.save_role("update_role", {"name": "Old"})
        db.save_role("update_role", {"name": "New", "extra": True})
        result = db.get_role("update_role")
        assert result["name"] == "New"
        assert result["extra"] is True

    def test_get_all_roles(self, db):
        db.save_role("r1", {"name": "R1"})
        db.save_role("r2", {"name": "R2"})
        roles = db.get_all_roles()
        assert len(roles) == 2
        role_ids = {r[0] for r in roles}
        assert "r1" in role_ids
        assert "r2" in role_ids

    def test_delete_role(self, db):
        db.save_role("del_me", {"name": "Temp"})
        assert db.get_role("del_me") is not None
        db.delete_role("del_me")
        assert db.get_role("del_me") is None

    def test_get_nonexistent_role(self, db):
        assert db.get_role("nope") is None

    def test_save_and_get_instance(self, db):
        data = {"name": "Test Agent", "role_id": "senior", "status": "idle"}
        db.save_instance("inst_1", data)
        result = db.get_instance("inst_1")
        assert result is not None
        assert result["name"] == "Test Agent"

    def test_get_all_instances(self, db):
        db.save_instance("i1", {"name": "A", "role_id": "r1"})
        db.save_instance("i2", {"name": "B", "role_id": "r2"})
        instances = db.get_all_instances()
        assert len(instances) == 2

    def test_delete_instance(self, db):
        db.save_instance("del_inst", {"name": "Temp"})
        db.delete_instance("del_inst")
        assert db.get_instance("del_inst") is None

    def test_get_instances_by_role(self, db):
        db.save_instance("i1", {"name": "A", "role_id": "senior"})
        db.save_instance("i2", {"name": "B", "role_id": "junior"})
        db.save_instance("i3", {"name": "C", "role_id": "senior"})
        seniors = db.get_instances_by_role("senior")
        assert len(seniors) == 2

    def test_save_and_get_task(self, db):
        data = {
            "title": "Test Task",
            "description": "Do something",
            "status": "pending",
            "priority": "high",
            "assigned_to": "agent_1",
            "created_by_role": "ceo",
            "delegation_depth": 0,
            "branch_name": "feature/test",
        }
        db.save_task("task_1", data)
        result = db.get_task("task_1")
        assert result is not None
        assert result["title"] == "Test Task"
        assert result["status"] == "pending"

    def test_get_all_tasks(self, db):
        db.save_task("t1", {"title": "T1", "status": "pending"})
        db.save_task("t2", {"title": "T2", "status": "completed"})
        all_tasks = db.get_all_tasks()
        assert len(all_tasks) == 2
        pending = db.get_all_tasks(status="pending")
        assert len(pending) == 1

    def test_get_tasks_by_agent(self, db):
        db.save_task("t1", {"title": "T1", "assigned_to": "agent_a"})
        db.save_task("t2", {"title": "T2", "assigned_to": "agent_b"})
        agent_tasks = db.get_tasks_by_agent("agent_a")
        assert len(agent_tasks) == 1
        assert agent_tasks[0]["title"] == "T1"

    def test_get_pending_approvals(self, db):
        db.save_task("t1", {"title": "T1", "status": "under_review"})
        db.save_task("t2", {"title": "T2", "status": "pending"})
        approvals = db.get_pending_approvals()
        assert len(approvals) == 1

    def test_save_and_get_subtasks(self, db):
        # Subtasks reference parent task - create parent first
        db.save_task("task_1", {"title": "Parent Task", "status": "pending"})
        db.save_subtask("sub_1", "task_1", {
            "title": "Sub Task",
            "description": "Part of bigger task",
            "assigned_to": "agent_x",
            "assigned_by": "agent_y",
            "status": "pending",
        })
        subtasks = db.get_subtasks("task_1")
        assert len(subtasks) == 1
        assert subtasks[0]["title"] == "Sub Task"

    def test_state_kv(self, db):
        db.set_state("config_key", {"theme": "dark", "version": 1})
        value = db.get_state("config_key")
        assert value["theme"] == "dark"
        assert value["version"] == 1

    def test_state_kv_default(self, db):
        assert db.get_state("missing", default={"fallback": True})["fallback"] is True

    def test_state_kv_update(self, db):
        db.set_state("counter", 1)
        db.set_state("counter", 2)
        assert db.get_state("counter") == 2

    def test_set_state_with_string(self, db):
        db.set_state("string_val", "hello")
        assert db.get_state("string_val") == "hello"

    def test_activity_log(self, db):
        db.log_activity("task_1", "Agent Alice", "created", {"branch": "feat/x"})
        db.log_activity("task_1", "Agent Alice", "completed", {"files": 3})
        activities = db.get_activities()
        assert len(activities) == 2

    def test_cost_tracking(self, db):
        db.record_cost("gpt-4o", 100, 50, 150, 0.005, "alice", "task_1")
        db.record_cost("gpt-4o", 200, 100, 300, 0.010, "bob", "task_2")
        summary = db.get_daily_cost()
        assert summary["total_cost"] > 0
        assert summary["total_requests"] == 2

    def test_cost_summary(self, db):
        db.record_cost("gpt-4o", 100, 50, 150, 0.005, "alice", "t1")
        summary = db.get_cost_summary(days=7)
        assert "total_cost" in summary
        assert "total_requests" in summary

    def test_task_stats(self, db):
        db.save_task("t1", {"title": "T1", "status": "pending"})
        db.save_task("t2", {"title": "T2", "status": "completed"})
        db.save_task("t3", {"title": "T3", "status": "in_progress"})
        stats = db.get_task_stats()
        assert stats["pending"] == 1
        assert stats["completed"] == 1
        assert stats["in_progress"] == 1
        assert stats["total_tasks"] == 3

    def test_close(self, db):
        db.close()
        # Should not raise

    def test_serialize_deserialize_complex(self, db):
        """Test that complex nested data survives round-trip."""
        data = {"key": "value", "nested": {"a": [1, 2, 3]}, "bool": True}
        db.save_role("complex", data)
        result = db.get_role("complex")
        assert result["nested"]["a"] == [1, 2, 3]
        assert result["bool"] is True

    def test_dry_run_save_does_not_persist(self, db):
        """Saving empty data should still work as a valid operation."""
        db.save_role("empty_test", {})
        result = db.get_role("empty_test")
        assert isinstance(result, dict)
