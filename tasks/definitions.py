"""Task definitions and execution logic."""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class SubTask:
    """A subtask for an agent."""
    agent: str
    description: str
    status: str = "pending"  # pending, running, completed, failed
    result: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class TaskDefinition:
    """Complete task definition."""
    id: str
    description: str
    subtasks: List[SubTask] = field(default_factory=list)
    branch: str = ""
    status: str = "pending"
    created_at: str = ""
    completed_at: Optional[str] = None
    error_message: str = ""
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class TaskPlanner:
    """Plans and breaks down tasks for agents."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
    
    def plan_task(self, task_id: str, description: str) -> TaskDefinition:
        """Create a task plan based on description.
        
        Args:
            task_id: Unique task ID
            description: Task description
            
        Returns:
            TaskDefinition with subtasks
        """
        task = TaskDefinition(id=task_id, description=description)
        
        desc_lower = description.lower()
        
        # Determine task type and create subtasks
        if self._is_create_api_task(desc_lower):
            task.subtasks = self._create_api_subtasks(description)
        elif self._is_create_page_task(desc_lower):
            task.subtasks = self._create_page_subtasks(description)
        elif self._is_testing_task(desc_lower):
            task.subtasks = self._create_testing_subtasks(description)
        else:
            # Generic task - all agents
            task.subtasks = self._create_full_stack_subtasks(description)
        
        return task
    
    def _is_create_api_task(self, desc_lower: str) -> bool:
        """Check if task is API creation."""
        api_keywords = ['api', 'endpoint', 'rest', 'json', 'resource']
        has_api_kw = any(kw in desc_lower for kw in api_keywords)
        no_ui_kw = all(kw not in desc_lower for kw in ['page', 'ui', 'blade', 'view', 'form'])
        return has_api_kw and no_ui_kw
    
    def _is_create_page_task(self, desc_lower: str) -> bool:
        """Check if task is web page creation."""
        page_keywords = ['page', 'view', 'blade', 'form', 'ui', 'interface']
        return any(kw in desc_lower for kw in page_keywords)
    
    def _is_testing_task(self, desc_lower: str) -> bool:
        """Check if task is testing only."""
        test_keywords = ['test', 'testing', 'spec', 'phpunit']
        return any(kw in desc_lower for kw in test_keywords) and 'create' not in desc_lower
    
    def _create_api_subtasks(self, description: str) -> List[SubTask]:
        """Create subtasks for API development."""
        return [
            SubTask(
                agent="backend",
                description=f"Create API for: {description}\n\n"
                           f"1. Analyze if model/migration is needed\n"
                           f"2. Create or update the model\n"
                           f"3. Create service class for business logic\n"
                           f"4. Create API controller with CRUD methods\n"
                           f"5. Create API Resource class\n"
                           f"6. Add routes to routes/api.php\n"
                           f"7. Ensure proper validation and error handling"
            ),
            SubTask(
                agent="testing",
                description=f"Write tests for the API: {description}\n\n"
                           f"1. Create feature tests for all endpoints\n"
                           f"2. Test validation rules\n"
                           f"3. Test happy path and error cases\n"
                           f"4. Run tests and ensure they pass"
            )
        ]
    
    def _create_page_subtasks(self, description: str) -> List[SubTask]:
        """Create subtasks for page development."""
        return [
            SubTask(
                agent="backend",
                description=f"Create backend for: {description}\n\n"
                           f"1. Analyze requirements\n"
                           f"2. Create/update model if needed\n"
                           f"3. Create controller with methods\n"
                           f"4. Add validation rules\n"
                           f"5. Add routes to routes/web.php"
            ),
            SubTask(
                agent="frontend",
                description=f"Create frontend for: {description}\n\n"
                           f"1. Create Blade view templates\n"
                           f"2. Use Tailwind CSS for styling\n"
                           f"3. Create forms with validation error display\n"
                           f"4. Ensure responsive design\n"
                           f"5. Follow existing UI patterns"
            ),
            SubTask(
                agent="testing",
                description=f"Write tests for: {description}\n\n"
                           f"1. Create feature tests for the page\n"
                           f"2. Test form submissions\n"
                           f"3. Test validation\n"
                           f"4. Run tests and ensure they pass"
            )
        ]
    
    def _create_testing_subtasks(self, description: str) -> List[SubTask]:
        """Create subtasks for testing work."""
        return [
            SubTask(
                agent="testing",
                description=f"Write comprehensive tests: {description}\n\n"
                           f"1. Identify what needs testing\n"
                           f"2. Write unit tests for business logic\n"
                           f"3. Write feature tests for endpoints/pages\n"
                           f"4. Ensure high test coverage\n"
                           f"5. Run full test suite and report results"
            )
        ]
    
    def _create_full_stack_subtasks(self, description: str) -> List[SubTask]:
        """Create subtasks for full-stack development."""
        return [
            SubTask(
                agent="backend",
                description=f"Create backend implementation: {description}\n\n"
                           f"1. Analyze requirements\n"
                           f"2. Create/update models and migrations\n"
                           f"3. Create service classes\n"
                           f"4. Create controllers\n"
                           f"5. Add proper validation\n"
                           f"6. Add routes"
            ),
            SubTask(
                agent="frontend",
                description=f"Create frontend implementation: {description}\n\n"
                           f"1. Create necessary Blade views\n"
                           f"2. Style with Tailwind CSS\n"
                           f"3. Create forms and UI components\n"
                           f"4. Ensure mobile responsiveness"
            ),
            SubTask(
                agent="testing",
                description=f"Write tests: {description}\n\n"
                           f"1. Test backend logic\n"
                           f"2. Test API endpoints or pages\n"
                           f"3. Run all tests\n"
                           f"4. Report results"
            )
        ]
    
    def get_task_summary(self, task: TaskDefinition) -> str:
        """Generate a summary of the task."""
        lines = [
            f"Task: {task.id}",
            f"Description: {task.description}",
            f"Status: {task.status}",
            f"Branch: {task.branch}",
            "",
            "Subtasks:"
        ]
        
        for i, subtask in enumerate(task.subtasks, 1):
            status_emoji = {
                'pending': '⏳',
                'running': '🔄',
                'completed': '✅',
                'failed': '❌'
            }.get(subtask.status, '❓')
            
            lines.append(f"  {i}. {status_emoji} [{subtask.agent}] {subtask.description[:50]}...")
        
        if task.files_created:
            lines.extend(["", f"Files Created ({len(task.files_created)}):"])
            for f in task.files_created[:10]:
                lines.append(f"  + {f}")
        
        if task.files_modified:
            lines.extend(["", f"Files Modified ({len(task.files_modified)}):"])
            for f in task.files_modified[:10]:
                lines.append(f"  ~ {f}")
        
        return '\n'.join(lines)


class TaskExecutor:
    """Executes tasks with agents."""
    
    def __init__(self, agent_manager, git_manager, validator, state_manager):
        self.agent_manager = agent_manager
        self.git_manager = git_manager
        self.validator = validator
        self.state_manager = state_manager
    
    async def execute_task(self, task: TaskDefinition, progress_callback=None):
        """Execute a task through all its subtasks.
        
        Args:
            task: TaskDefinition to execute
            progress_callback: Optional callback for progress updates
        """
        # Update status
        task.status = "running"
        self.state_manager.update_task_status(task.id, "running")
        
        # Get agents
        backend_agent = self.agent_manager.create_backend_agent()
        frontend_agent = self.agent_manager.create_frontend_agent()
        testing_agent = self.agent_manager.create_testing_agent()
        
        agent_map = {
            'backend': backend_agent,
            'frontend': frontend_agent,
            'testing': testing_agent
        }
        
        # Execute subtasks
        for i, subtask in enumerate(task.subtasks):
            subtask.status = "running"
            subtask.started_at = datetime.now().isoformat()
            self.state_manager.update_subtask(task.id, subtask.agent, "running")
            
            if progress_callback:
                await progress_callback(
                    f"🔄 Executing: [{subtask.agent}] {subtask.description[:50]}..."
                )
            
            try:
                # Get the agent
                agent = agent_map.get(subtask.agent)
                if not agent:
                    raise ValueError(f"Unknown agent: {subtask.agent}")
                
                # Get project context
                context = ""
                if self.agent_manager.project_context:
                    context = self.agent_manager.project_context.to_summary()
                
                # Execute with agent
                result = self.agent_manager.execute_agent_task(
                    agent, 
                    subtask.description,
                    context
                )
                
                subtask.result = result
                subtask.status = "completed"
                subtask.completed_at = datetime.now().isoformat()
                
                self.state_manager.update_subtask(task.id, subtask.agent, "completed")
                self.state_manager.log_activity(
                    task.id, subtask.agent, "completed", subtask.description[:100]
                )
                
                if progress_callback:
                    await progress_callback(f"✅ [{subtask.agent}] Completed")
                
            except Exception as e:
                subtask.status = "failed"
                subtask.result = str(e)
                subtask.completed_at = datetime.now().isoformat()
                
                self.state_manager.update_subtask(task.id, subtask.agent, "failed")
                self.state_manager.log_activity(
                    task.id, subtask.agent, "failed", str(e)
                )
                
                if progress_callback:
                    await progress_callback(f"❌ [{subtask.agent}] Failed: {str(e)}")
                
                # Stop execution on failure
                task.status = "failed"
                task.error_message = str(e)
                self.state_manager.update_task_status(task.id, "failed", str(e))
                return
        
        # All subtasks completed
        task.status = "completed"
        task.completed_at = datetime.now().isoformat()
        self.state_manager.update_task_status(task.id, "completed")
        
        if progress_callback:
            await progress_callback("✅ All subtasks completed successfully!")


# Export
__all__ = ['TaskDefinition', 'SubTask', 'TaskPlanner', 'TaskExecutor']