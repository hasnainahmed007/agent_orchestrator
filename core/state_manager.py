"""State management for tasks and agent activities."""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class TaskState:
    """Represents a task and its state."""
    id: str
    description: str
    status: str  # pending, running, completed, failed, waiting_approval
    branch: str
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    subtasks: List[Dict] = None
    changes_summary: str = ""
    error_message: str = ""
    
    def __post_init__(self):
        if self.subtasks is None:
            self.subtasks = []


class StateManager:
    """Manages persistent state for tasks."""
    
    def __init__(self, state_file: Path, tasks_file: Path):
        self.state_file = Path(state_file)
        self.tasks_file = Path(tasks_file)
        self.state: Dict[str, Any] = {}
        self.tasks: Dict[str, TaskState] = {}
        self._load()
    
    def _load(self):
        """Load state from files."""
        # Load general state
        if self.state_file.exists():
            try:
                self.state = json.loads(self.state_file.read_text())
            except:
                self.state = {}
        
        # Load tasks
        if self.tasks_file.exists():
            try:
                tasks_data = json.loads(self.tasks_file.read_text())
                self.tasks = {
                    task_id: TaskState(**task_data)
                    for task_id, task_data in tasks_data.items()
                }
            except:
                self.tasks = {}
    
    def _save(self):
        """Save state to files."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2))
        
        self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
        tasks_data = {
            task_id: asdict(task)
            for task_id, task in self.tasks.items()
        }
        self.tasks_file.write_text(json.dumps(tasks_data, indent=2))
    
    def create_task(self, task_id: str, description: str, branch: str) -> TaskState:
        """Create a new task."""
        now = datetime.now().isoformat()
        task = TaskState(
            id=task_id,
            description=description,
            status="pending",
            branch=branch,
            created_at=now,
            updated_at=now
        )
        self.tasks[task_id] = task
        self._save()
        return task
    
    def get_task(self, task_id: str) -> Optional[TaskState]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: str, error: str = ""):
        """Update task status."""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            self.tasks[task_id].updated_at = datetime.now().isoformat()
            if error:
                self.tasks[task_id].error_message = error
            if status in ["completed", "failed", "rejected"]:
                self.tasks[task_id].completed_at = datetime.now().isoformat()
            self._save()
    
    def add_subtask(self, task_id: str, agent: str, description: str):
        """Add a subtask to a task."""
        if task_id in self.tasks:
            subtask = {
                "agent": agent,
                "description": description,
                "status": "pending",
                "started_at": None,
                "completed_at": None
            }
            self.tasks[task_id].subtasks.append(subtask)
            self._save()
    
    def update_subtask(self, task_id: str, agent: str, status: str):
        """Update subtask status."""
        if task_id in self.tasks:
            for subtask in self.tasks[task_id].subtasks:
                if subtask["agent"] == agent and subtask["status"] != "completed":
                    subtask["status"] = status
                    if status == "running":
                        subtask["started_at"] = datetime.now().isoformat()
                    elif status in ["completed", "failed"]:
                        subtask["completed_at"] = datetime.now().isoformat()
                    self._save()
                    break
    
    def set_changes_summary(self, task_id: str, summary: str):
        """Set summary of changes for approval."""
        if task_id in self.tasks:
            self.tasks[task_id].changes_summary = summary
            self._save()
    
    def list_tasks(self, status: Optional[str] = None) -> List[TaskState]:
        """List tasks, optionally filtered by status."""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)
    
    def get_pending_approvals(self) -> List[TaskState]:
        """Get tasks waiting for approval."""
        return self.list_tasks("waiting_approval")
    
    def get_active_tasks(self) -> List[TaskState]:
        """Get currently running tasks."""
        return [t for t in self.tasks.values() if t.status == "running"]
    
    def set(self, key: str, value: Any):
        """Set a state value."""
        self.state[key] = value
        self._save()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        return self.state.get(key, default)
    
    def log_activity(self, task_id: str, agent: str, action: str, details: str = ""):
        """Log an activity."""
        if "activities" not in self.state:
            self.state["activities"] = []
        
        activity = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "agent": agent,
            "action": action,
            "details": details
        }
        
        self.state["activities"].append(activity)
        
        # Keep only last 100 activities
        self.state["activities"] = self.state["activities"][-100:]
        self._save()
    
    def get_recent_activities(self, count: int = 20) -> List[Dict]:
        """Get recent activities."""
        activities = self.state.get("activities", [])
        return activities[-count:][::-1]
    
    def get_stats(self) -> Dict:
        """Get task statistics."""
        all_tasks = list(self.tasks.values())
        return {
            "total": len(all_tasks),
            "pending": len([t for t in all_tasks if t.status == "pending"]),
            "running": len([t for t in all_tasks if t.status == "running"]),
            "completed": len([t for t in all_tasks if t.status == "completed"]),
            "failed": len([t for t in all_tasks if t.status == "failed"]),
            "waiting_approval": len([t for t in all_tasks if t.status == "waiting_approval"])
        }