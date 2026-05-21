"""Dynamic agent role and instance management system."""
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path

from skills.registry import SkillRegistry, SkillModule, get_skill_registry


@dataclass
class AgentRole:
    """Defines a role template for agents (e.g., CEO, CTO, Senior Engineer)."""
    
    role_id: str
    name: str
    description: str
    
    # Hierarchy: 1 = highest (CEO), 10 = lowest (Junior/Intern)
    hierarchy_level: int = 5
    
    # Skills this role possesses (skill_ids from SkillRegistry)
    skills: List[str] = field(default_factory=list)
    
    # What this agent is responsible for
    responsibilities: List[str] = field(default_factory=list)
    
    # Which roles this agent can delegate tasks to
    can_delegate_to: List[str] = field(default_factory=list)
    
    # Which roles can review/approve this agent's work
    reviewed_by: List[str] = field(default_factory=list)
    
    # Custom prompt additions beyond skills
    custom_prompt: str = ""
    
    # Whether this agent's work requires approval before completion
    approval_required: bool = False
    
    # Max tasks this agent can handle simultaneously
    max_concurrent_tasks: int = 3
    
    # Whether this agent can create subtasks for others
    can_create_subtasks: bool = True
    
    # Whether this agent can modify project files directly
    can_modify_files: bool = True
    
    # Created/updated timestamps
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AgentRole':
        # Filter only valid fields
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)
    
    def get_combined_skills_context(self, skill_registry: SkillRegistry) -> str:
        """Generate combined context from all skills."""
        contexts = []
        
        for skill_id in self.skills:
            skill = skill_registry.get_skill(skill_id)
            if skill:
                contexts.append(f"""
### {skill.name} ({skill.expertise_level})
{skill.description}

**Best Practices:**
{chr(10).join(['- ' + p for p in skill.best_practices[:5]])}

**Coding Standards:**
{chr(10).join(['- ' + s for s in skill.coding_standards[:3]])}
""")
        
        return "\n".join(contexts)
    
    def get_allowed_tools(self, skill_registry: SkillRegistry) -> List[str]:
        """Get all tools this agent can use based on skills."""
        tools = set()
        for skill_id in self.skills:
            skill = skill_registry.get_skill(skill_id)
            if skill:
                tools.update(skill.tools)
        return list(tools)
    
    def build_system_prompt(self, skill_registry: SkillRegistry) -> str:
        """Build the complete system prompt for this role."""
        lines = [
            f"# Role: {self.name}",
            f"",
            f"{self.description}",
            f"",
            f"## Hierarchy Level: {self.hierarchy_level} (1=Highest, 10=Lowest)",
            f"",
            f"## Responsibilities",
        ]
        
        for resp in self.responsibilities:
            lines.append(f"- {resp}")
        
        lines.extend([
            "",
            "## Expertise & Skills",
            self.get_combined_skills_context(skill_registry),
            "",
        ])
        
        if self.can_delegate_to:
            lines.extend([
                "## Delegation Authority",
                f"You can delegate tasks to: {', '.join(self.can_delegate_to)}",
                "",
            ])
        
        if self.reviewed_by:
            lines.extend([
                "## Review Process",
                f"Your work is reviewed by: {', '.join(self.reviewed_by)}",
                "",
            ])
        
        lines.extend([
            "## Rules",
            f"- Approval required before completing work: {'Yes' if self.approval_required else 'No'}",
            f"- Can create subtasks for others: {'Yes' if self.can_create_subtasks else 'No'}",
            f"- Can modify project files directly: {'Yes' if self.can_modify_files else 'No'}",
            f"- Max concurrent tasks: {self.max_concurrent_tasks}",
            "",
        ])
        
        if self.custom_prompt:
            lines.extend([
                "## Additional Instructions",
                self.custom_prompt,
                "",
            ])
        
        lines.append("Always act according to your role and expertise level.")
        
        return "\n".join(lines)


@dataclass
class AgentInstance:
    """A concrete agent instance created from an AgentRole."""
    
    instance_id: str
    name: str  # e.g., "Alice - Senior Python Dev"
    role_id: str
    
    # Agent state
    status: str = "idle"  # idle, busy, offline, error
    current_task_ids: List[str] = field(default_factory=list)
    
    # Task history
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    
    # Performance metrics
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    average_task_time: float = 0.0
    
    # Custom overrides (can override role settings)
    skill_overrides: List[str] = field(default_factory=list)
    prompt_overrides: str = ""
    
    # Timestamps
    created_at: str = ""
    last_active: str = ""
    
    def __post_init__(self):
        if not self.instance_id:
            self.instance_id = f"agent-{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_active:
            self.last_active = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AgentInstance':
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)
    
    def is_available(self) -> bool:
        """Check if agent is available for new tasks."""
        if self.status in ("offline", "error"):
            return False
        return True
    
    def is_idle(self) -> bool:
        """Check if agent has no active tasks."""
        return len(self.current_task_ids) == 0
    
    def assign_task(self, task_id: str):
        """Assign a task to this agent."""
        if task_id not in self.current_task_ids:
            self.current_task_ids.append(task_id)
        self.status = "busy"
        self.last_active = datetime.now().isoformat()
    
    def complete_task(self, task_id: str, success: bool = True):
        """Mark task as completed."""
        if task_id in self.current_task_ids:
            self.current_task_ids.remove(task_id)
        if not self.current_task_ids:
            self.status = "idle"
        self.last_active = datetime.now().isoformat()
        
        if success:
            self.completed_tasks.append(task_id)
            self.total_tasks_completed += 1
        else:
            self.failed_tasks.append(task_id)
            self.total_tasks_failed += 1
    
    def get_skills(self, role: AgentRole) -> List[str]:
        """Get effective skills (role skills + overrides)."""
        skills = set(role.skills)
        skills.update(self.skill_overrides)
        return list(skills)


class AgentRoleManager:
    """Manages agent roles and instances."""
    
    # Pre-defined role templates
    DEFAULT_ROLES: Dict[str, AgentRole] = {
        'ceo': AgentRole(
            role_id='ceo',
            name='Chief Executive Officer',
            description='Strategic leader who defines vision, prioritizes initiatives, and makes final decisions.',
            hierarchy_level=1,
            skills=['system_design'],
            responsibilities=[
                'Define project vision and goals',
                'Prioritize tasks and allocate resources',
                'Make final decisions on architecture and approach',
                'Review high-level deliverables',
                'Coordinate between departments/teams'
            ],
            can_delegate_to=['cto', 'senior_engineer', 'devops_lead'],
            reviewed_by=[],
            approval_required=False,
            max_concurrent_tasks=5,
            can_create_subtasks=True,
            can_modify_files=False
        ),
        
        'cto': AgentRole(
            role_id='cto',
            name='Chief Technology Officer',
            description='Technical leader responsible for architecture decisions, technology stack, and engineering standards.',
            hierarchy_level=2,
            skills=['system_design', 'security'],
            responsibilities=[
                'Define technical architecture',
                'Choose technology stack and tools',
                'Set coding standards and best practices',
                'Review critical technical decisions',
                'Mentor senior engineers',
                'Ensure security and scalability'
            ],
            can_delegate_to=['senior_engineer', 'devops_lead', 'security_engineer'],
            reviewed_by=['ceo'],
            approval_required=False,
            max_concurrent_tasks=4,
            can_create_subtasks=True,
            can_modify_files=True
        ),
        
        'senior_engineer': AgentRole(
            role_id='senior_engineer',
            name='Senior Software Engineer',
            description='Experienced engineer who designs complex features, mentors juniors, and ensures code quality.',
            hierarchy_level=3,
            skills=['python', 'typescript', 'system_design', 'security'],
            responsibilities=[
                'Design and implement complex features',
                'Write high-quality, maintainable code',
                'Code review for junior engineers',
                'Mentor and guide junior team members',
                'Refactor and optimize existing code',
                'Write comprehensive tests'
            ],
            can_delegate_to=['junior_engineer'],
            reviewed_by=['cto', 'senior_engineer'],
            approval_required=False,
            max_concurrent_tasks=3,
            can_create_subtasks=True,
            can_modify_files=True
        ),
        
        'junior_engineer': AgentRole(
            role_id='junior_engineer',
            name='Junior Software Engineer',
            description='Entry-level engineer who implements well-defined tasks under senior guidance.',
            hierarchy_level=4,
            skills=['python', 'javascript'],
            responsibilities=[
                'Implement well-defined features',
                'Write unit tests',
                'Fix bugs and minor issues',
                'Learn and follow team conventions',
                'Ask for help when blocked',
                'Document code and processes'
            ],
            can_delegate_to=[],
            reviewed_by=['senior_engineer', 'cto'],
            approval_required=True,
            max_concurrent_tasks=2,
            can_create_subtasks=False,
            can_modify_files=True
        ),
        
        'devops_lead': AgentRole(
            role_id='devops_lead',
            name='DevOps Lead',
            description='Infrastructure and deployment expert responsible for CI/CD, cloud, and operational excellence.',
            hierarchy_level=3,
            skills=['docker', 'devops', 'system_design', 'security'],
            responsibilities=[
                'Design and maintain CI/CD pipelines',
                'Manage cloud infrastructure',
                'Implement monitoring and alerting',
                'Ensure deployment reliability',
                'Optimize build and deployment times',
                'Maintain infrastructure as code'
            ],
            can_delegate_to=['devops_engineer'],
            reviewed_by=['cto'],
            approval_required=False,
            max_concurrent_tasks=3,
            can_create_subtasks=True,
            can_modify_files=True
        ),
        
        'devops_engineer': AgentRole(
            role_id='devops_engineer',
            name='DevOps Engineer',
            description='Implements infrastructure changes, maintains pipelines, and supports deployments.',
            hierarchy_level=4,
            skills=['docker', 'devops'],
            responsibilities=[
                'Implement infrastructure changes',
                'Troubleshoot deployment issues',
                'Maintain CI/CD configurations',
                'Monitor system health',
                'Document operational procedures'
            ],
            can_delegate_to=[],
            reviewed_by=['devops_lead', 'cto'],
            approval_required=True,
            max_concurrent_tasks=2,
            can_create_subtasks=False,
            can_modify_files=True
        ),
        
        'security_engineer': AgentRole(
            role_id='security_engineer',
            name='Security Engineer',
            description='Application security specialist who audits code, implements security controls, and conducts reviews.',
            hierarchy_level=3,
            skills=['security', 'system_design', 'python', 'typescript'],
            responsibilities=[
                'Conduct security audits',
                'Implement security controls',
                'Review code for vulnerabilities',
                'Maintain security documentation',
                'Respond to security incidents',
                'Train team on secure coding'
            ],
            can_delegate_to=[],
            reviewed_by=['cto'],
            approval_required=False,
            max_concurrent_tasks=2,
            can_create_subtasks=False,
            can_modify_files=True
        ),
        
        'qa_engineer': AgentRole(
            role_id='qa_engineer',
            name='QA Engineer',
            description='Quality assurance specialist who writes tests, performs testing, and ensures software quality.',
            hierarchy_level=4,
            skills=['python', 'javascript', 'typescript'],
            responsibilities=[
                'Write automated tests',
                'Perform manual testing',
                'Create test plans and cases',
                'Report and track bugs',
                'Validate fixes',
                'Maintain test documentation'
            ],
            can_delegate_to=[],
            reviewed_by=['senior_engineer'],
            approval_required=False,
            max_concurrent_tasks=3,
            can_create_subtasks=False,
            can_modify_files=True
        )
    }
    
    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.roles_file = self.state_dir / 'agent_roles.json'
        self.instances_file = self.state_dir / 'agent_instances.json'
        
        self.roles: Dict[str, AgentRole] = {**self.DEFAULT_ROLES}
        self.instances: Dict[str, AgentInstance] = {}
        
        self._load()
    
    def _load(self):
        """Load roles and instances from disk."""
        # Load custom roles
        if self.roles_file.exists():
            try:
                data = json.loads(self.roles_file.read_text())
                for role_id, role_data in data.items():
                    self.roles[role_id] = AgentRole.from_dict(role_data)
            except Exception as e:
                print(f"Warning: Could not load roles: {e}")
        
        # Load instances
        if self.instances_file.exists():
            try:
                data = json.loads(self.instances_file.read_text())
                for inst_id, inst_data in data.items():
                    self.instances[inst_id] = AgentInstance.from_dict(inst_data)
            except Exception as e:
                print(f"Warning: Could not load instances: {e}")
    
    def _save(self):
        """Save custom roles and instances to disk.
        Default roles are never persisted to avoid accidental overwrite.
        """
        custom_roles = {
            role_id: role.to_dict()
            for role_id, role in self.roles.items()
            if role_id not in self.DEFAULT_ROLES
        }
        self.roles_file.write_text(json.dumps(custom_roles, indent=2))

        instances_data = {
            inst_id: inst.to_dict()
            for inst_id, inst in self.instances.items()
        }
        self.instances_file.write_text(json.dumps(instances_data, indent=2))
    
    # Role Management
    # -------------------------------------------------------------------------
    
    def create_role(self, role: AgentRole) -> str:
        """Create a new role. Returns role_id."""
        if role.role_id in self.roles:
            raise ValueError(f"Role already exists: {role.role_id}")
        
        role.created_at = datetime.now().isoformat()
        role.updated_at = datetime.now().isoformat()
        self.roles[role.role_id] = role
        self._save()
        return role.role_id
    
    def get_role(self, role_id: str) -> Optional[AgentRole]:
        """Get a role by ID."""
        return self.roles.get(role_id)
    
    def update_role(self, role_id: str, **kwargs) -> bool:
        """Update role fields."""
        if role_id not in self.roles:
            return False
        
        role = self.roles[role_id]
        for key, value in kwargs.items():
            if hasattr(role, key):
                setattr(role, key, value)
        
        role.updated_at = datetime.now().isoformat()
        self._save()
        return True
    
    def delete_role(self, role_id: str) -> bool:
        """Delete a custom role. Cannot delete default roles."""
        if role_id in self.DEFAULT_ROLES:
            raise ValueError(f"Cannot delete default role: {role_id}")

        if role_id in self.roles:
            del self.roles[role_id]
            self._save()
            return True
        return False
    
    def list_roles(self) -> List[AgentRole]:
        """List all roles."""
        return list(self.roles.values())
    
    def get_roles_by_hierarchy(self) -> List[AgentRole]:
        """Get roles sorted by hierarchy level (highest first)."""
        return sorted(self.roles.values(), key=lambda r: r.hierarchy_level)
    
    def _get_custom_role_ids(self) -> set:
        """Get IDs of custom (non-default) roles."""
        if not self.roles_file.exists():
            return set()
        try:
            data = json.loads(self.roles_file.read_text())
            return set(data.keys())
        except:
            return set()
    
    # Instance Management
    # -------------------------------------------------------------------------
    
    def create_instance(self, name: str, role_id: str, **overrides) -> AgentInstance:
        """Create a new agent instance from a role."""
        if role_id not in self.roles:
            raise ValueError(f"Role not found: {role_id}")
        
        instance = AgentInstance(
            instance_id=f"agent-{uuid.uuid4().hex[:8]}",
            name=name,
            role_id=role_id,
            **overrides
        )
        
        self.instances[instance.instance_id] = instance
        self._save()
        return instance
    
    def get_instance(self, instance_id: str) -> Optional[AgentInstance]:
        """Get an agent instance."""
        return self.instances.get(instance_id)
    
    def get_instances_by_role(self, role_id: str) -> List[AgentInstance]:
        """Get all instances for a role."""
        return [i for i in self.instances.values() if i.role_id == role_id]
    
    def get_available_instances(self, role_id: Optional[str] = None) -> List[AgentInstance]:
        """Get available instances with capacity."""
        instances = list(self.instances.values())
        if role_id:
            instances = [i for i in instances if i.role_id == role_id]
        available = []
        for i in instances:
            if i.status in ("offline", "error"):
                continue
            role = self.roles.get(i.role_id)
            if role and role.max_concurrent_tasks is not None:
                if self._count_active_tasks(i.instance_id) >= role.max_concurrent_tasks:
                    continue
            available.append(i)
        return available
    
    def delete_instance(self, instance_id: str) -> bool:
        """Delete an agent instance."""
        if instance_id in self.instances:
            del self.instances[instance_id]
            self._save()
            return True
        return False
    
    def list_instances(self) -> List[AgentInstance]:
        """List all instances."""
        return list(self.instances.values())
    
    def update_instance(self, instance_id: str, **kwargs) -> bool:
        """Update instance fields."""
        if instance_id not in self.instances:
            return False
        
        instance = self.instances[instance_id]
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        instance.last_active = datetime.now().isoformat()
        self._save()
        return True
    
    # Hierarchy & Delegation Helpers
    # -------------------------------------------------------------------------
    
    def get_delegation_chain(self, from_role_id: str) -> List[AgentRole]:
        """Get the delegation chain from a role (who they can delegate to)."""
        role = self.roles.get(from_role_id)
        if not role:
            return []
        
        chain = []
        for target_id in role.can_delegate_to:
            target = self.roles.get(target_id)
            if target:
                chain.append(target)
        
        # Sort by hierarchy (lower level = more junior)
        return sorted(chain, key=lambda r: r.hierarchy_level)
    
    def get_reviewers(self, role_id: str) -> List[AgentRole]:
        """Get roles that can review a given role's work."""
        role = self.roles.get(role_id)
        if not role:
            return []
        
        reviewers = []
        for reviewer_id in role.reviewed_by:
            reviewer = self.roles.get(reviewer_id)
            if reviewer:
                reviewers.append(reviewer)
        
        return reviewers
    
    def find_best_agent_for_task(self, task_description: str, skill_registry: SkillRegistry) -> Optional[AgentInstance]:
        """Find the best available agent for a task based on skills and capacity."""
        desc_lower = task_description.lower()

        best_agent = None
        best_score = -1

        for instance in self.get_available_instances():
            role = self.roles.get(instance.role_id)
            if not role:
                continue

            # Check max concurrent tasks limit (None = unlimited, 0 = blocked)
            if role.max_concurrent_tasks is not None:
                active_count = self._count_active_tasks(instance.instance_id)
                if active_count >= role.max_concurrent_tasks:
                    continue

            score = 0
            for skill_id in role.skills:
                skill = skill_registry.get_skill(skill_id)
                if skill:
                    skill_keywords = skill.name.lower().split() + skill.description.lower().split()
                    for kw in skill_keywords:
                        if len(kw) > 3 and kw in desc_lower:
                            score += 1

            # Prefer higher hierarchy for complex tasks
            score += (5 - role.hierarchy_level) * 0.5

            if score > best_score:
                best_score = score
                best_agent = instance

        return best_agent

    def _count_active_tasks(self, instance_id: str) -> int:
        """Count active tasks for an agent instance."""
        inst = self.instances.get(instance_id)
        if not inst:
            return 0
        return len(inst.current_task_ids)
    
    def get_team_summary(self) -> Dict[str, Any]:
        """Get summary of the entire team."""
        return {
            'total_roles': len(self.roles),
            'total_instances': len(self.instances),
            'available_agents': len([i for i in self.instances.values() if i.is_idle()]),
            'busy_agents': len([i for i in self.instances.values() if not i.is_idle()]),
            'roles': [
                {
                    'role_id': r.role_id,
                    'name': r.name,
                    'hierarchy_level': r.hierarchy_level,
                    'instance_count': len(self.get_instances_by_role(r.role_id))
                }
                for r in self.get_roles_by_hierarchy()
            ],
            'agents': [
                {
                    'instance_id': i.instance_id,
                    'name': i.name,
                    'role': self.roles.get(i.role_id, AgentRole('unknown', 'Unknown', '')).name,
                    'status': i.status,
                    'tasks_completed': i.total_tasks_completed
                }
                for i in self.instances.values()
            ]
        }
