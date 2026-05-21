"""Hierarchical task delegation engine for multi-agent teams."""
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import json

from agents.roles import AgentRoleManager, AgentRole, AgentInstance
from skills.registry import SkillRegistry


class TaskStatus(Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    DELEGATED = "delegated"  # Task has been broken into subtasks
    UNDER_REVIEW = "under_review"
    BLOCKED = "blocked"  # Waiting for human help
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class SubTaskStatus(Enum):
    """Subtask states."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"  # Waiting for human help
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


@dataclass
class SubTask:
    """A subtask within a larger task."""
    parent_task_id: str
    title: str
    description: str
    
    subtask_id: str = ""
    assigned_to: Optional[str] = None  # instance_id
    assigned_by: Optional[str] = None  # instance_id of delegator
    
    status: str = "pending"
    priority: str = "normal"  # low, normal, high, critical
    
    # Results
    result: str = ""
    deliverables: List[str] = field(default_factory=list)  # file paths
    
    # Timestamps
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Review
    review_required: bool = False
    reviewed_by: Optional[str] = None
    review_notes: str = ""
    
    # Human help / blocked
    block_reason: str = ""
    help_requested_at: Optional[str] = None
    human_response: str = ""
    resumed_at: Optional[str] = None
    
    def __post_init__(self):
        if not self.subtask_id:
            self.subtask_id = f"sub-{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SubTask':
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


@dataclass
class DelegatedTask:
    """A task in the delegation system."""
    title: str
    description: str
    
    task_id: str = ""
    
    # Original requester
    requested_by: str = "user"  # user, system, or agent instance_id
    
    # Assignment
    assigned_to: Optional[str] = None  # instance_id of primary assignee
    
    # Hierarchy tracking
    created_by_role: str = ""  # role_id that created this task
    delegation_depth: int = 0  # How many levels deep in delegation
    
    # Status
    status: str = "pending"
    priority: str = "normal"
    
    # Subtasks (for delegation)
    subtasks: List[SubTask] = field(default_factory=list)
    
    # Results
    result_summary: str = ""
    deliverables: List[str] = field(default_factory=list)
    
    # Error/rejection
    error_message: str = ""
    rejection_reason: str = ""
    
    # Timestamps
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Approval workflow
    approval_required: bool = False
    approved_by: Optional[str] = None
    approval_notes: str = ""
    
    # Git integration
    branch_name: str = ""
    
    # Multi-project support
    project_id: str = ""
    project_path: str = ""
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"TASK-{uuid.uuid4().hex[:8].upper()}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DelegatedTask':
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        # Handle subtasks specially
        if 'subtasks' in valid_fields and valid_fields['subtasks']:
            valid_fields['subtasks'] = [
                SubTask.from_dict(st) if isinstance(st, dict) else st
                for st in valid_fields['subtasks']
            ]
        return cls(**valid_fields)
    
    def is_complete(self) -> bool:
        """Check if task and all subtasks are complete."""
        if self.status in ["completed", "failed", "rejected", "rolled_back"]:
            return True
        if not self.subtasks:
            return False
        return all(
            st.status in ["completed", "failed"] 
            for st in self.subtasks
        )
    
    def get_progress(self) -> Dict[str, int]:
        """Get task progress counts."""
        if not self.subtasks:
            return {"total": 1, "completed": 1 if self.status == "completed" else 0}
        
        total = len(self.subtasks)
        completed = sum(1 for st in self.subtasks if st.status == "completed")
        failed = sum(1 for st in self.subtasks if st.status == "failed")
        in_progress = sum(1 for st in self.subtasks if st.status == "in_progress")
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": total - completed - failed - in_progress
        }


class TaskDelegationEngine:
    """Engine for hierarchical task delegation and management."""
    
    def __init__(self, state_dir: Path, role_manager: AgentRoleManager):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.state_dir / 'delegated_tasks.json'
        
        self.role_manager = role_manager
        self.tasks: Dict[str, DelegatedTask] = {}
        
        # Callbacks for events
        self._on_task_created: Optional[Callable] = None
        self._on_task_assigned: Optional[Callable] = None
        self._on_task_completed: Optional[Callable] = None
        self._on_task_failed: Optional[Callable] = None
        self._on_approval_needed: Optional[Callable] = None
        self._on_task_blocked: Optional[Callable] = None
        self._on_task_resumed: Optional[Callable] = None
        
        self._load()
    
    def _load(self):
        """Load tasks from disk."""
        if self.tasks_file.exists():
            try:
                data = json.loads(self.tasks_file.read_text())
                for task_id, task_data in data.items():
                    self.tasks[task_id] = DelegatedTask.from_dict(task_data)
            except Exception as e:
                print(f"Warning: Could not load tasks: {e}")
    
    def _save(self):
        """Save tasks to disk."""
        data = {
            task_id: task.to_dict()
            for task_id, task in self.tasks.items()
        }
        self.tasks_file.write_text(json.dumps(data, indent=2))
    
    # Task Creation
    # -------------------------------------------------------------------------
    
    def create_task(self, title: str, description: str, 
                   assigned_to: Optional[str] = None,
                   priority: str = "normal",
                   requested_by: str = "user",
                   project_id: str = "",
                   project_path: str = "") -> DelegatedTask:
        """Create a new task.
        
        Args:
            title: Short task title
            description: Detailed description
            assigned_to: Instance ID to assign to (optional - will auto-assign)
            priority: Task priority
            requested_by: Who requested the task
            project_id: Project ID this task belongs to
            project_path: Project filesystem path
        """
        task = DelegatedTask(
            task_id=f"TASK-{uuid.uuid4().hex[:8].upper()}",
            title=title,
            description=description,
            requested_by=requested_by,
            assigned_to=assigned_to,
            priority=priority,
            status="pending",
            project_id=project_id,
            project_path=project_path
        )
        
        self.tasks[task.task_id] = task
        self._save()
        
        if self._on_task_created:
            self._on_task_created(task)
        
        return task
    
    def assign_task(self, task_id: str, instance_id: str) -> bool:
        """Assign a task to an agent instance."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        instance = self.role_manager.get_instance(instance_id)
        if not instance:
            return False
        
        task.assigned_to = instance_id
        task.status = "assigned"
        task.started_at = datetime.now().isoformat()
        
        # Update agent status
        instance.assign_task(task_id)
        self.role_manager.update_instance(instance_id, status="busy")
        
        self._save()
        
        if self._on_task_assigned:
            self._on_task_assigned(task, instance)
        
        return True
    
    def auto_assign_task(self, task_id: str, skill_registry: SkillRegistry) -> Optional[str]:
        """Auto-assign task to best available agent. Returns instance_id or None."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        best_agent = self.role_manager.find_best_agent_for_task(
            task.description, skill_registry
        )
        
        if best_agent:
            self.assign_task(task_id, best_agent.instance_id)
            return best_agent.instance_id
        
        return None
    
    # Delegation
    # -------------------------------------------------------------------------
    
    def delegate_task(self, task_id: str, delegator_id: str,
                     subtask_defs: List[Dict[str, Any]]) -> List[SubTask]:
        """Break a task into subtasks and delegate them.
        
        Args:
            task_id: Parent task ID
            delegator_id: Instance ID of the agent doing the delegation
            subtask_defs: List of dicts with 'title', 'description', 'assign_to' (role_id)
        
        Returns:
            List of created subtasks
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        delegator = self.role_manager.get_instance(delegator_id)
        if not delegator:
            raise ValueError(f"Delegator not found: {delegator_id}")
        
        delegator_role = self.role_manager.get_role(delegator.role_id)
        if not delegator_role or not delegator_role.can_create_subtasks:
            raise ValueError(f"Agent {delegator_id} cannot create subtasks")
        
        created_subtasks = []
        
        for sub_def in subtask_defs:
            subtask = SubTask(
                parent_task_id=task_id,
                title=sub_def['title'],
                description=sub_def['description'],
                assigned_by=delegator_id,
                priority=sub_def.get('priority', task.priority),
                review_required=sub_def.get('review_required', False)
            )
            
            # Try to assign to specific agent if requested
            assign_to_role = sub_def.get('assign_to')
            if assign_to_role:
                # Find available agent with that role
                available = self.role_manager.get_available_instances(assign_to_role)
                if available:
                    subtask.assigned_to = available[0].instance_id
                    available[0].assign_task(subtask.subtask_id)
                    self.role_manager.update_instance(
                        available[0].instance_id,
                        status="busy"
                    )
            
            task.subtasks.append(subtask)
            created_subtasks.append(subtask)
        
        task.status = "delegated"
        task.delegation_depth += 1
        self._save()
        
        return created_subtasks
    
    def complete_subtask(self, subtask_id: str, result: str = "",
                        deliverables: List[str] = None) -> bool:
        """Mark a subtask as completed."""
        for task in self.tasks.values():
            for subtask in task.subtasks:
                if subtask.subtask_id == subtask_id:
                    subtask.status = "completed"
                    subtask.result = result
                    subtask.deliverables = deliverables or []
                    subtask.completed_at = datetime.now().isoformat()
                    
                    # Free up the agent
                    if subtask.assigned_to:
                        agent = self.role_manager.get_instance(subtask.assigned_to)
                        if agent:
                            agent.complete_task(subtask_id, success=True)
                            self.role_manager.update_instance(
                                agent.instance_id,
                                status="idle" if agent.is_idle() else "busy"
                            )
                    
                    self._save()
                    
                    # Check if parent task is now complete
                    self._check_parent_completion(task.task_id)
                    
                    return True
        
        return False
    
    def fail_subtask(self, subtask_id: str, error: str = "") -> bool:
        """Mark a subtask as failed."""
        for task in self.tasks.values():
            for subtask in task.subtasks:
                if subtask.subtask_id == subtask_id:
                    subtask.status = "failed"
                    subtask.result = error
                    subtask.completed_at = datetime.now().isoformat()
                    
                    # Free up the agent
                    if subtask.assigned_to:
                        agent = self.role_manager.get_instance(subtask.assigned_to)
                        if agent:
                            agent.complete_task(subtask_id, success=False)
                            self.role_manager.update_instance(
                                agent.instance_id,
                                status="idle" if agent.is_idle() else "busy"
                            )
                    
                    self._save()
                    
                    # Parent task might need attention
                    if self._on_task_failed:
                        self._on_task_failed(task)
                    
                    return True
        
        return False
    
    def _check_parent_completion(self, task_id: str):
        """Check if all subtasks are done and update parent status."""
        task = self.tasks.get(task_id)
        if not task or not task.subtasks:
            return
        
        all_done = all(st.status in ["completed", "failed"] for st in task.subtasks)
        if not all_done:
            return
        
        any_failed = any(st.status == "failed" for st in task.subtasks)
        
        if any_failed:
            task.status = "failed"
            task.error_message = "One or more subtasks failed"
            if self._on_task_failed:
                self._on_task_failed(task)
        else:
            # Check if approval is required
            role = None
            if task.assigned_to:
                agent = self.role_manager.get_instance(task.assigned_to)
                if agent:
                    role = self.role_manager.get_role(agent.role_id)
            
            if role and role.approval_required:
                task.status = "under_review"
                if self._on_approval_needed:
                    self._on_approval_needed(task)
            else:
                task.status = "completed"
                task.completed_at = datetime.now().isoformat()
                
                # Free up the primary agent
                if task.assigned_to:
                    agent = self.role_manager.get_instance(task.assigned_to)
                    if agent:
                        agent.complete_task(task_id, success=True)
                        self.role_manager.update_instance(
                            task.assigned_to,
                            status="idle" if agent.is_idle() else "busy"
                        )
                
                if self._on_task_completed:
                    self._on_task_completed(task)
        
        self._save()
    
    # Approval Workflow
    # -------------------------------------------------------------------------
    
    def request_approval(self, task_id: str, reviewer_id: str) -> bool:
        """Request approval for a completed task."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.status = "under_review"
        task.approved_by = None
        self._save()
        
        if self._on_approval_needed:
            self._on_approval_needed(task)
        
        return True
    
    def approve_task(self, task_id: str, approver_id: str, notes: str = "") -> bool:
        """Approve a task."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.status = "approved"
        task.approved_by = approver_id
        task.approval_notes = notes
        task.completed_at = datetime.now().isoformat()
        
        # Free up the agent
        if task.assigned_to:
            agent = self.role_manager.get_instance(task.assigned_to)
            if agent:
                agent.complete_task(task_id, success=True)
                self.role_manager.update_instance(
                    task.assigned_to,
                    status="idle" if agent.is_idle() else "busy"
                )
        
        self._save()
        
        if self._on_task_completed:
            self._on_task_completed(task)
        
        return True
    
    def reject_task(self, task_id: str, reviewer_id: str, reason: str = "") -> bool:
        """Reject a task and return it for rework."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.status = "rejected"
        task.rejection_reason = reason
        
        # Free up the agent (they'll get reassigned if needed)
        if task.assigned_to:
            agent = self.role_manager.get_instance(task.assigned_to)
            if agent:
                agent.complete_task(task_id, success=False)
                self.role_manager.update_instance(
                    task.assigned_to,
                    status="idle" if agent.is_idle() else "busy"
                )
        
        self._save()
        
        if self._on_task_failed:
            self._on_task_failed(task)
        
        return True
    
    # Human Help / Blocked Workflow
    # -------------------------------------------------------------------------
    
    def request_help(self, task_id: str, reason: str, subtask_id: str = None) -> bool:
        """Mark a task or subtask as blocked, requesting human help.
        
        This pauses execution. Agent will wait synchronously for human response.
        Fires on_task_blocked callback if set.
        
        Args:
            task_id: Task ID (or parent task ID if using subtask_id)
            reason: Why help is needed
            subtask_id: Optional subtask ID to block
            
        Returns:
            True if blocked successfully
        """
        if subtask_id:
            # Block a specific subtask
            for t in self.tasks.values():
                for subtask in t.subtasks:
                    if subtask.subtask_id == subtask_id:
                        subtask.status = "blocked"
                        subtask.block_reason = reason
                        subtask.help_requested_at = datetime.now().isoformat()
                        self._save()
                        if self._on_task_blocked:
                            self._on_task_blocked(
                                task=t,
                                reason=reason,
                                agent_id=subtask.assigned_to,
                                subtask=subtask
                            )
                        return True
            return False
        
        # Block the main task
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.status = "blocked"
        self._save()
        
        if self._on_task_blocked:
            self._on_task_blocked(
                task=task,
                reason=reason,
                agent_id=task.assigned_to
            )
        
        return True
    
    def resolve_help(self, task_id: str, response: str, subtask_id: str = None) -> bool:
        """Resolve a blocked task with human response.
        
        Fires on_task_resumed callback.
        
        Args:
            task_id: Task ID
            response: Human's response/instructions
            subtask_id: Optional subtask ID
            
        Returns:
            True if resolved
        """
        if subtask_id:
            for t in self.tasks.values():
                for subtask in t.subtasks:
                    if subtask.subtask_id == subtask_id:
                        subtask.status = "in_progress"
                        subtask.human_response = response
                        subtask.resumed_at = datetime.now().isoformat()
                        self._save()
                        if self._on_task_resumed:
                            self._on_task_resumed(task=t, response=response, subtask=subtask)
                        return True
            return False
        
        task = self.tasks.get(task_id)
        if not task or task.status != "blocked":
            return False
        
        task.status = "in_progress"
        self._save()
        
        if self._on_task_resumed:
            self._on_task_resumed(task=task, response=response)
        
        return True
    
    def list_blocked_tasks(self) -> List[DelegatedTask]:
        """Get all tasks currently blocked waiting for human help."""
        blocked = []
        for task in self.tasks.values():
            if task.status == "blocked":
                blocked.append(task)
            else:
                # Check subtasks
                for sub in task.subtasks:
                    if sub.status == "blocked":
                        blocked.append(task)
                        break
        return sorted(blocked, key=lambda t: t.created_at)
    
    # Task Queries
    # -------------------------------------------------------------------------
    
    def get_task(self, task_id: str) -> Optional[DelegatedTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(self, status: Optional[str] = None,
                  assigned_to: Optional[str] = None) -> List[DelegatedTask]:
        """List tasks with optional filtering."""
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]
        
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)
    
    def get_pending_approvals(self) -> List[DelegatedTask]:
        """Get tasks waiting for approval."""
        return self.list_tasks(status="under_review")
    
    def get_agent_tasks(self, instance_id: str) -> List[DelegatedTask]:
        """Get all tasks assigned to an agent."""
        return [
            t for t in self.tasks.values()
            if t.assigned_to == instance_id
        ]
    
    def get_subtasks_for_agent(self, instance_id: str) -> List[SubTask]:
        """Get all subtasks assigned to an agent."""
        subtasks = []
        for task in self.tasks.values():
            for subtask in task.subtasks:
                if subtask.assigned_to == instance_id:
                    subtasks.append(subtask)
        return subtasks
    
    def get_task_tree(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task with its full subtask tree."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            'task': task.to_dict(),
            'progress': task.get_progress(),
            'subtasks': [st.to_dict() for st in task.subtasks],
            'assignee': self._get_agent_info(task.assigned_to),
            'can_delegate': self._can_delegate(task)
        }
    
    def _get_agent_info(self, instance_id: Optional[str]) -> Optional[Dict]:
        """Get agent info for display."""
        if not instance_id:
            return None
        agent = self.role_manager.get_instance(instance_id)
        if not agent:
            return None
        role = self.role_manager.get_role(agent.role_id)
        return {
            'instance_id': agent.instance_id,
            'name': agent.name,
            'role': role.name if role else "Unknown",
            'status': agent.status
        }
    
    def _can_delegate(self, task: DelegatedTask) -> bool:
        """Check if the assigned agent can delegate this task."""
        if not task.assigned_to:
            return False
        agent = self.role_manager.get_instance(task.assigned_to)
        if not agent:
            return False
        role = self.role_manager.get_role(agent.role_id)
        if not role:
            return False
        return role.can_create_subtasks
    
    # Event Handlers
    # -------------------------------------------------------------------------
    
    def on_task_created(self, callback: Callable):
        """Set callback for task creation."""
        self._on_task_created = callback
    
    def on_task_assigned(self, callback: Callable):
        """Set callback for task assignment."""
        self._on_task_assigned = callback
    
    def on_task_completed(self, callback: Callable):
        """Set callback for task completion."""
        self._on_task_completed = callback
    
    def on_task_failed(self, callback: Callable):
        """Set callback for task failure."""
        self._on_task_failed = callback
    
    def on_approval_needed(self, callback: Callable):
        """Set callback for approval requests."""
        self._on_approval_needed = callback
    
    def on_task_blocked(self, callback: Callable):
        """Set callback for task blocked (needs human help)."""
        self._on_task_blocked = callback
    
    def on_task_resumed(self, callback: Callable):
        """Set callback for task resumed after human help."""
        self._on_task_resumed = callback
    
    # Statistics
    # -------------------------------------------------------------------------
    
    def get_stats(self) -> Dict[str, Any]:
        """Get delegation engine statistics."""
        all_tasks = list(self.tasks.values())
        
        return {
            'total_tasks': len(all_tasks),
            'pending': len([t for t in all_tasks if t.status == "pending"]),
            'assigned': len([t for t in all_tasks if t.status == "assigned"]),
            'in_progress': len([t for t in all_tasks if t.status == "in_progress"]),
            'delegated': len([t for t in all_tasks if t.status == "delegated"]),
            'under_review': len([t for t in all_tasks if t.status == "under_review"]),
            'blocked': len([t for t in all_tasks if t.status == "blocked"]),
            'completed': len([t for t in all_tasks if t.status == "completed"]),
            'failed': len([t for t in all_tasks if t.status == "failed"]),
            'rejected': len([t for t in all_tasks if t.status == "rejected"]),
            'total_subtasks': sum(len(t.subtasks) for t in all_tasks)
        }
