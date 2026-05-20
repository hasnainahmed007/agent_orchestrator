"""Tests for agent roles module."""
import json
import tempfile
from pathlib import Path
import pytest
from agents.roles import AgentRole, AgentInstance, AgentRoleManager
from skills.registry import SkillRegistry


class TestAgentRole:
    """Tests for AgentRole dataclass."""

    def test_create_role(self):
        """Create a basic AgentRole."""
        role = AgentRole(
            role_id='test_role',
            name='Test Role',
            description='A test role',
            hierarchy_level=5,
            skills=['python']
        )
        assert role.role_id == 'test_role'
        assert role.hierarchy_level == 5
        assert role.skills == ['python']
        assert role.approval_required is False

    def test_role_to_dict_and_from_dict(self):
        """Serialization round-trip."""
        role = AgentRole(
            role_id='roundtrip',
            name='Roundtrip Role',
            description='Testing',
            hierarchy_level=3,
            skills=['python', 'typescript'],
            responsibilities=['Code review', 'Mentoring'],
            can_delegate_to=['junior_engineer'],
            reviewed_by=['cto'],
            approval_required=True,
            can_create_subtasks=True
        )
        data = role.to_dict()
        restored = AgentRole.from_dict(data)
        assert restored.role_id == role.role_id
        assert restored.skills == role.skills
        assert restored.can_delegate_to == role.can_delegate_to
        assert restored.reviewed_by == role.reviewed_by
        assert restored.approval_required is True

    def test_get_combined_skills_context(self, tmp_path):
        """get_combined_skills_context returns skill descriptions."""
        from skills.registry import get_skill_registry, reset_skill_registry
        reset_skill_registry()
        reg = get_skill_registry()
        role = AgentRole(
            role_id='test', name='Test', description='Test',
            hierarchy_level=3, skills=['python']
        )
        context = role.get_combined_skills_context(reg)
        assert isinstance(context, str)
        assert len(context) > 0

    def test_get_allowed_tools(self, tmp_path):
        """get_allowed_tools returns tool names from role skills."""
        from skills.registry import get_skill_registry, reset_skill_registry
        reset_skill_registry()
        reg = get_skill_registry()
        role = AgentRole(
            role_id='test', name='Test', description='Test',
            hierarchy_level=3, skills=['python', 'docker']
        )
        tools = role.get_allowed_tools(reg)
        assert isinstance(tools, list)

    def test_build_system_prompt(self, tmp_path):
        """build_system_prompt returns a non-empty string."""
        from skills.registry import get_skill_registry, reset_skill_registry
        reset_skill_registry()
        reg = get_skill_registry()
        role = AgentRole(
            role_id='senior_engineer',
            name='Senior Engineer',
            description='Senior dev',
            hierarchy_level=3,
            skills=['python'],
            responsibilities=['Write code'],
            can_modify_files=True
        )
        prompt = role.build_system_prompt(reg)
        assert isinstance(prompt, str)
        assert len(prompt) > 100


class TestAgentInstance:
    """Tests for AgentInstance dataclass."""

    def test_create_instance(self):
        """Create an AgentInstance."""
        inst = AgentInstance(
            instance_id='inst-001',
            name='Alice',
            role_id='senior_engineer'
        )
        assert inst.status == 'idle'
        assert inst.instance_id == 'inst-001'
        assert inst.total_tasks_completed == 0

    def test_instance_to_dict_and_from_dict(self):
        """Serialization round-trip."""
        inst = AgentInstance(
            instance_id='inst-002',
            name='Bob',
            role_id='junior_engineer',
            status='busy',
            skill_overrides=['devops'],
            completed_tasks=['task-1', 'task-2'],
            total_tasks_completed=2
        )
        data = inst.to_dict()
        restored = AgentInstance.from_dict(data)
        assert restored.instance_id == inst.instance_id
        assert restored.name == inst.name
        assert restored.status == inst.status
        assert restored.skill_overrides == inst.skill_overrides
        assert restored.completed_tasks == inst.completed_tasks

    def test_is_available_when_idle(self):
        """is_available returns True for idle status."""
        inst = AgentInstance(instance_id='x', name='x', role_id='r')
        assert inst.is_available() is True

    def test_is_available_when_busy(self):
        """is_available returns False for busy status."""
        inst = AgentInstance(instance_id='x', name='x', role_id='r', status='busy')
        assert inst.is_available() is False

    def test_assign_task(self):
        """assign_task sets status to busy."""
        inst = AgentInstance(instance_id='x', name='x', role_id='r')
        inst.assign_task('task-3')
        assert inst.status == 'busy'
        assert inst.current_task_id == 'task-3'

    def test_complete_task_success(self):
        """complete_task with success updates metrics."""
        inst = AgentInstance(instance_id='x', name='x', role_id='r', status='busy')
        inst.complete_task('task-1', success=True)
        assert inst.total_tasks_completed == 1
        assert 'task-1' in inst.completed_tasks
        assert inst.total_tasks_failed == 0

    def test_complete_task_failure(self):
        """complete_task with failure updates metrics."""
        inst = AgentInstance(instance_id='x', name='x', role_id='r')
        inst.complete_task('task-err', success=False)
        assert inst.total_tasks_failed == 1
        assert 'task-err' in inst.failed_tasks

    def test_get_skills(self):
        """get_skills returns combined skills from role + overrides."""
        inst = AgentInstance(
            instance_id='x', name='x', role_id='senior_engineer',
            skill_overrides=['docker', 'devops']
        )
        role = AgentRole(
            role_id='senior_engineer', name='Senior', description='Senior',
            hierarchy_level=3, skills=['python', 'typescript']
        )
        skills = inst.get_skills(role)
        assert 'python' in skills
        assert 'docker' in skills
        assert 'devops' in skills


class TestAgentRoleManager:
    """Tests for AgentRoleManager."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create AgentRoleManager with temp directory."""
        return AgentRoleManager(tmp_path)

    def test_default_roles_loaded(self, manager):
        """Manager loads 8 default roles."""
        assert len(manager.roles) == 8
        assert 'ceo' in manager.roles
        assert 'cto' in manager.roles
        assert 'senior_engineer' in manager.roles
        assert 'junior_engineer' in manager.roles

    def test_create_role(self, manager):
        """create_role adds a new role."""
        role = AgentRole(
            role_id='tech_lead',
            name='Tech Lead',
            description='Lead role',
            hierarchy_level=3,
            skills=['python']
        )
        role_id = manager.create_role(role)
        assert role_id == 'tech_lead'
        assert 'tech_lead' in manager.roles

    def test_get_role(self, manager):
        """get_role returns correct role."""
        role = manager.get_role('ceo')
        assert role is not None
        assert role.name == 'Chief Executive Officer'
        assert role.hierarchy_level == 1

    def test_get_role_nonexistent(self, manager):
        """get_role returns None for missing role."""
        assert manager.get_role('nonexistent') is None

    def test_list_roles(self, manager):
        """list_roles returns all role objects."""
        roles = manager.list_roles()
        role_ids = [r.role_id for r in roles]
        assert 'ceo' in role_ids
        assert 'junior_engineer' in role_ids

    def test_create_instance(self, manager):
        """create_instance creates a new agent instance."""
        inst = manager.create_instance('Alice', 'senior_engineer')
        assert inst.name == 'Alice'
        assert inst.role_id == 'senior_engineer'
        assert inst.status == 'idle'
        assert inst.instance_id.startswith('agent-')

    def test_get_instance(self, manager):
        """get_instance returns created instance."""
        inst = manager.create_instance('Bob', 'devops_engineer')
        retrieved = manager.get_instance(inst.instance_id)
        assert retrieved is not None
        assert retrieved.name == 'Bob'

    def test_get_instances_by_role(self, manager):
        """get_instances_by_role filters correctly."""
        manager.create_instance('A1', 'senior_engineer')
        manager.create_instance('A2', 'senior_engineer')
        manager.create_instance('B1', 'junior_engineer')

        senior_instances = manager.get_instances_by_role('senior_engineer')
        assert len(senior_instances) == 2

        junior_instances = manager.get_instances_by_role('junior_engineer')
        assert len(junior_instances) == 1

    def test_get_available_instances(self, manager):
        """get_available_instances returns only idle agents."""
        inst1 = manager.create_instance('Idle', 'senior_engineer')
        inst2 = manager.create_instance('Busy', 'senior_engineer')
        manager.update_instance(inst2.instance_id, status='busy')

        available = manager.get_available_instances()
        assert any(a.instance_id == inst1.instance_id for a in available)
        assert not any(a.instance_id == inst2.instance_id for a in available)

    def test_delete_instance(self, manager):
        """delete_instance removes the instance."""
        inst = manager.create_instance('DeleteMe', 'qa_engineer')
        assert manager.delete_instance(inst.instance_id) is True
        assert manager.get_instance(inst.instance_id) is None

    def test_get_roles_by_hierarchy(self, manager):
        """get_roles_by_hierarchy returns roles sorted by level."""
        roles = manager.get_roles_by_hierarchy()
        # CEO (level 1) should be first
        assert roles[0].hierarchy_level <= roles[-1].hierarchy_level
        assert roles[0].role_id == 'ceo'

    def test_get_delegation_chain(self, manager):
        """get_delegation_chain returns roles CEO can delegate to."""
        chain = manager.get_delegation_chain('ceo')
        chain_ids = [r.role_id for r in chain]
        assert 'cto' in chain_ids
        assert 'senior_engineer' in chain_ids

    def test_get_reviewers(self, manager):
        """get_reviewers returns reviewing role objects."""
        reviewers = manager.get_reviewers('junior_engineer')
        reviewer_ids = [r.role_id for r in reviewers]
        assert 'senior_engineer' in reviewer_ids

    def test_get_team_summary(self, manager):
        """get_team_summary returns structured data."""
        manager.create_instance('Agent1', 'senior_engineer')
        manager.create_instance('Agent2', 'junior_engineer')

        summary = manager.get_team_summary()
        assert summary['total_roles'] == 8
        assert summary['total_instances'] == 2
        assert summary['available_agents'] == 2

    def test_find_best_agent_for_task(self, manager, tmp_path):
        """find_best_agent_for_task returns agent matching skills."""
        from skills.registry import get_skill_registry, reset_skill_registry
        reset_skill_registry()
        reg = get_skill_registry()

        manager.create_instance('PythonDev', 'senior_engineer')
        manager.create_instance('ReactDev', 'senior_engineer')

        agent_id = manager.find_best_agent_for_task(
            'Create a Python REST API', reg
        )
        assert agent_id is not None

    def test_state_persistence(self, tmp_path):
        """Roles and instances persist to JSON files."""
        mgr1 = AgentRoleManager(tmp_path)
        mgr1.create_instance('Persistent', 'junior_engineer')

        mgr2 = AgentRoleManager(tmp_path)
        inst = mgr2.get_instance('Persistent')
        # Instance should be retrievable by checking list
        instances = mgr2.list_instances()
        assert any(i.name == 'Persistent' for i in instances)
