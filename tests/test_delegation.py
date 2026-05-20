"""Tests for task delegation engine."""
import tempfile
from pathlib import Path
import pytest
from agents.roles import AgentRoleManager, AgentRole
from agents.delegation import (
    TaskDelegationEngine, DelegatedTask, SubTask, TaskStatus, SubTaskStatus
)
from skills.registry import get_skill_registry, reset_skill_registry


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_status_values(self):
        assert TaskStatus.PENDING.value == 'pending'
        assert TaskStatus.COMPLETED.value == 'completed'
        assert TaskStatus.FAILED.value == 'failed'


class TestDelegatedTask:
    """Tests for DelegatedTask dataclass."""

    def test_create_task(self):
        """Create a basic delegated task."""
        task = DelegatedTask(
            task_id='TASK-TEST001',
            title='Test Task',
            description='Test description'
        )
        assert task.task_id == 'TASK-TEST001'
        assert task.status == 'pending'
        assert task.priority == 'normal'
        assert task.subtasks == []
        assert task.delegation_depth == 0

    def test_task_to_dict_and_from_dict(self):
        """Serialization round-trip."""
        task = DelegatedTask(
            task_id='TASK-RT001',
            title='Roundtrip',
            description='Testing',
            priority='high',
            assigned_to='agent-1',
            created_by_role='ceo',
            delegation_depth=1,
            branch_name='agent/test/branch'
        )
        data = task.to_dict()
        restored = DelegatedTask.from_dict(data)
        assert restored.task_id == task.task_id
        assert restored.title == task.title
        assert restored.priority == task.priority
        assert restored.assigned_to == task.assigned_to
        assert restored.branch_name == task.branch_name

    def test_is_complete_when_done(self):
        """is_complete returns True for completed status."""
        task = DelegatedTask(task_id='T1', title='T', description='D', status='completed')
        assert task.is_complete() is True

    def test_is_complete_when_pending(self):
        """is_complete returns False for pending status."""
        task = DelegatedTask(task_id='T1', title='T', description='D')
        assert task.is_complete() is False

    def test_get_progress_no_subtasks(self):
        """get_progress returns 0/1 for no subtasks (task itself counts as 1 item)."""
        task = DelegatedTask(task_id='T1', title='T', description='D')
        progress = task.get_progress()
        assert progress['completed'] == 0
        assert progress['total'] == 1

    def test_get_progress_with_subtasks(self):
        """get_progress counts completed subtasks."""
        task = DelegatedTask(task_id='T1', title='T', description='D')
        task.subtasks = [
            SubTask(subtask_id='S1', parent_task_id='T1', title='S1',
                    description='', assigned_to='a', assigned_by='b',
                    status='completed'),
            SubTask(subtask_id='S2', parent_task_id='T1', title='S2',
                    description='', assigned_to='a', assigned_by='b',
                    status='pending'),
            SubTask(subtask_id='S3', parent_task_id='T1', title='S3',
                    description='', assigned_to='a', assigned_by='b',
                    status='completed'),
        ]
        progress = task.get_progress()
        assert progress['completed'] == 2
        assert progress['total'] == 3


class TestTaskDelegationEngine:
    """Tests for TaskDelegationEngine."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create engine with empty state."""
        role_mgr = AgentRoleManager(tmp_path)
        engine = TaskDelegationEngine(tmp_path, role_mgr)
        return engine

    def test_create_task(self, engine):
        """create_task returns a valid DelegatedTask."""
        task = engine.create_task('My Task', 'Do something', priority='high')
        assert task.task_id.startswith('TASK-')
        assert task.title == 'My Task'
        assert task.priority == 'high'
        assert task.status == 'pending'

    def test_create_task_default_priority(self, engine):
        """create_task defaults to normal priority."""
        task = engine.create_task('Task', 'Desc')
        assert task.priority == 'normal'

    def test_assign_task(self, engine):
        """assign_task sets task status to assigned."""
        task = engine.create_task('T', 'D')
        # Create an agent instance first (assign_task validates instance exists)
        inst = engine.role_manager.create_instance('test-agent', 'senior_engineer')
        assert engine.assign_task(task.task_id, inst.instance_id) is True
        task = engine.get_task(task.task_id)
        assert task.assigned_to == inst.instance_id
        assert task.status == 'assigned'

    def test_assign_task_not_found(self, engine):
        """assign_task returns False for missing task."""
        inst = engine.role_manager.create_instance('test-agent', 'senior_engineer')
        assert engine.assign_task('NONEXISTENT', inst.instance_id) is False

    def test_get_task(self, engine):
        """get_task retrieves created task."""
        task = engine.create_task('Get this', 'Description')
        retrieved = engine.get_task(task.task_id)
        assert retrieved is not None
        assert retrieved.task_id == task.task_id
        assert retrieved.title == 'Get this'

    def test_get_task_not_found(self, engine):
        """get_task returns None for missing ID."""
        assert engine.get_task('NONEXISTENT') is None

    def test_list_tasks(self, engine):
        """list_tasks returns all created tasks."""
        t1 = engine.create_task('Task 1', 'Desc 1')
        t2 = engine.create_task('Task 2', 'Desc 2')
        tasks = engine.list_tasks()
        assert len(tasks) >= 2
        ids = [t.task_id for t in tasks]
        assert t1.task_id in ids
        assert t2.task_id in ids

    def test_list_tasks_filter_by_status(self, engine):
        """list_tasks filters by status."""
        inst = engine.role_manager.create_instance('filter-agent', 'senior_engineer')
        t1 = engine.create_task('T1', 'D1')
        t2 = engine.create_task('T2', 'D2')
        t3 = engine.create_task('T3', 'D3')
        engine.assign_task(t1.task_id, inst.instance_id)

        completed = engine.list_tasks(status='assigned')
        assert len(completed) >= 1
        assert all(t.status == 'assigned' for t in completed)

    def test_delegate_task(self, engine):
        """delegate_task creates subtasks when delegator role can delegate."""
        inst = engine.role_manager.create_instance('ceo-instance', 'ceo')
        task = engine.create_task('Parent', 'Parent desc')
        engine.assign_task(task.task_id, inst.instance_id)

        subtask_defs = [
            {'title': 'Sub A', 'description': 'Desc A', 'assign_to': 'senior_engineer', 'priority': 'high'},
            {'title': 'Sub B', 'description': 'Desc B', 'assign_to': 'junior_engineer', 'priority': 'normal'},
        ]
        # delegate_task expects valid delegator_id (agent instance id), returns subtask list
        result = engine.delegate_task(task.task_id, inst.instance_id, subtask_defs)
        assert isinstance(result, list)
        assert len(result) == 2

        task = engine.get_task(task.task_id)
        assert task.status == 'delegated'
        assert len(task.subtasks) == 2
        assert task.delegation_depth == 1

    def test_delegate_task_not_found(self, engine):
        """delegate_task raises ValueError for missing task."""
        import pytest as pytest_mod
        from agents.delegation import TaskDelegationEngine
        with pytest_mod.raises(ValueError, match="Task not found"):
            engine.delegate_task('NONEXISTENT', 'agent', [])

    def test_request_approval(self, engine):
        """request_approval sets status to under_review."""
        task = engine.create_task('T', 'D')
        rv = engine.request_approval(task.task_id, 'reviewer')
        assert rv is True
        task = engine.get_task(task.task_id)
        assert task.status == 'under_review'

    def test_approve_task(self, engine):
        """approve_task approves under_review task."""
        task = engine.create_task('T', 'D')
        engine.request_approval(task.task_id, 'reviewer')
        rv = engine.approve_task(task.task_id, 'approver', 'Looks good')
        assert rv is True
        task = engine.get_task(task.task_id)
        assert task.status == 'approved'

    def test_reject_task(self, engine):
        """reject_task rejects under_review task."""
        task = engine.create_task('T', 'D')
        engine.request_approval(task.task_id, 'reviewer')
        rv = engine.reject_task(task.task_id, 'reviewer', 'Needs work')
        assert rv is True
        task = engine.get_task(task.task_id)
        assert task.status == 'rejected'
        assert task.rejection_reason == 'Needs work'

    def test_get_pending_approvals(self, engine):
        """get_pending_approvals returns tasks under review."""
        t1 = engine.create_task('T1', 'D1')
        t2 = engine.create_task('T2', 'D2')
        engine.request_approval(t1.task_id, 'r')
        engine.request_approval(t2.task_id, 'r')

        pending = engine.get_pending_approvals()
        assert len(pending) == 2

    def test_get_stats(self, engine):
        """get_stats returns summary statistics."""
        engine.create_task('T1', 'D1', priority='high')
        engine.create_task('T2', 'D2')

        stats = engine.get_stats()
        assert stats['total_tasks'] == 2
        assert stats['pending'] >= 2
        # Completed should be 0
        assert stats.get('completed', 0) == 0

    def test_get_task_tree(self, engine):
        """get_task_tree returns structured task data."""
        inst = engine.role_manager.create_instance('tree-agent', 'senior_engineer')
        task = engine.create_task('Parent', 'Parent desc')
        engine.assign_task(task.task_id, inst.instance_id)

        tree = engine.get_task_tree(task.task_id)
        assert tree is not None
        assert 'task' in tree
        assert 'subtasks' in tree
        assert tree['task']['task_id'] == task.task_id

    def test_callback_on_task_created(self, engine):
        """on_task_created callback fires on task creation."""
        called_with = []

        def callback(task):
            called_with.append(task.task_id)

        engine.on_task_created(callback)
        task = engine.create_task('Callback', 'Test callback')
        assert task.task_id in called_with

    def test_persistence_across_instances(self, tmp_path):
        """Tasks persist to file and load from file."""
        mgr = AgentRoleManager(tmp_path)
        e1 = TaskDelegationEngine(tmp_path, mgr)
        task = e1.create_task('Persist me', 'Testing persistence')

        e2 = TaskDelegationEngine(tmp_path, mgr)
        retrieved = e2.get_task(task.task_id)
        assert retrieved is not None
        assert retrieved.title == 'Persist me'
