"""Main orchestrator that coordinates dynamic multi-agent teams."""
import os
import sys
import logging
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Config
from config.prompts import PromptComposer, build_project_context
from skills.registry import get_skill_registry
from agents.roles import AgentRoleManager, AgentRole, AgentInstance
from agents.delegation import TaskDelegationEngine, DelegatedTask
from core.git_manager import GitManager
from core.project_context import ProjectContextScanner
from core.validator import Validator
from core.state_manager import StateManager
from core.cost_tracker import CostTracker
from core.rate_limiter import RateLimiter, TokenQuotaManager
from core.performance_tracker import PerformanceTracker
from agents import AgentManager


# Setup logging
log_dir = Config.LOG_FILE.parent
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Orchestrator:
    """Main orchestrator that coordinates dynamic multi-agent teams."""
    
    def __init__(self):
        logger.info("Initializing Agent Orchestrator...")

        # Validate configuration
        errors, warnings = Config.validate()
        if warnings:
            for warning in warnings:
                logger.warning(f"  - {warning}")
        if errors:
            logger.error("Configuration errors:")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError("Configuration validation failed")

        Config.ensure_directories()

        # Initialize skill registry
        self.skill_registry = get_skill_registry(Config.CUSTOM_SKILLS_DIR)

        # Initialize role manager
        self.role_manager = AgentRoleManager(Config.STATE_FILE.parent)

        # Initialize delegation engine
        self.delegation = TaskDelegationEngine(Config.STATE_FILE.parent, self.role_manager)
        self._setup_delegation_callbacks()

        # Initialize core components
        self.git = GitManager(Config.PROJECT_PATH, Config.MAIN_BRANCH)
        self.validator = Validator(Config.PROJECT_PATH, Config.PROJECT_TYPE)
        self.state = StateManager(Config.STATE_FILE, Config.TASKS_FILE)
        self.project_scanner = ProjectContextScanner(Config.PROJECT_PATH, Config.PROJECT_TYPE)

        # Agent manager (for CrewAI execution)
        self.agent_manager = AgentManager(Config.PROJECT_PATH)

        # Cost control and monitoring
        self.cost_tracker = CostTracker(Config.STATE_FILE.parent, Config.DAILY_BUDGET_LIMIT)
        self.rate_limiter = RateLimiter(Config.STATE_FILE.parent)
        self.quota_manager = TokenQuotaManager(Config.STATE_FILE.parent)
        self.perf_tracker = PerformanceTracker(Config.STATE_FILE.parent)

        # Telegram bot (initialized later)
        self.telegram: Optional[Any] = None

        logger.info("Orchestrator initialized successfully")
        logger.info(f"Loaded {len(self.role_manager.roles)} roles, {len(self.role_manager.instances)} agents")
    
    def _setup_delegation_callbacks(self):
        """Setup callbacks for delegation events."""
        self.delegation.on_task_created(self._on_task_created)
        self.delegation.on_task_assigned(self._on_task_assigned)
        self.delegation.on_task_completed(self._on_task_completed)
        self.delegation.on_task_failed(self._on_task_failed)
        self.delegation.on_approval_needed(self._on_approval_needed)
    
    def _on_task_created(self, task: DelegatedTask):
        """Handle task creation."""
        logger.info(f"Task created: {task.task_id} - {task.title}")
    
    def _on_task_assigned(self, task: DelegatedTask, agent: AgentInstance):
        """Handle task assignment."""
        logger.info(f"Task {task.task_id} assigned to {agent.name}")
    
    def _on_task_completed(self, task: DelegatedTask):
        """Handle task completion."""
        logger.info(f"Task {task.task_id} completed")
        
        # Legacy state tracking
        self.state.update_task_status(task.task_id, "completed")
        self.state.log_activity(task.task_id, "system", "completed", task.title)
    
    def _on_task_failed(self, task: DelegatedTask):
        """Handle task failure."""
        logger.error(f"Task {task.task_id} failed: {task.error_message}")
        self.state.update_task_status(task.task_id, "failed", task.error_message)
        self.state.log_activity(task.task_id, "system", "failed", task.error_message)
    
    def _on_approval_needed(self, task: DelegatedTask):
        """Handle approval request."""
        logger.info(f"Task {task.task_id} needs approval")
        
        # Notify via Telegram if available
        if self.telegram and hasattr(self.telegram, 'notify_approval_request'):
            asyncio.create_task(
                self.telegram.notify_approval_request(
                    chat_id=0,  # Will be set by Telegram bot
                    task_id=task.task_id,
                    branch=task.branch_name,
                    changes_summary=task.result_summary[:2000]
                )
            )
    
    # Agent & Role Management
    # -------------------------------------------------------------------------
    
    def create_agent(self, name: str, role_id: str, **overrides) -> AgentInstance:
        """Create a new agent instance."""
        instance = self.role_manager.create_instance(name, role_id, **overrides)
        logger.info(f"Created agent: {instance.name} ({instance.instance_id}) as {role_id}")
        return instance
    
    def create_role(self, role: AgentRole) -> str:
        """Create a new agent role."""
        role_id = self.role_manager.create_role(role)
        logger.info(f"Created role: {role.name} ({role_id})")
        return role_id
    
    def get_team_summary(self) -> Dict[str, Any]:
        """Get team summary."""
        return self.role_manager.get_team_summary()
    
    # Task Management
    # -------------------------------------------------------------------------
    
    async def submit_task(self, title: str, description: str,
                         assign_to: Optional[str] = None,
                         priority: str = "normal") -> DelegatedTask:
        """Submit a new task.
        
        Args:
            title: Task title
            description: Task description
            assign_to: Instance ID to assign to (optional, auto-assigns if None)
            priority: Task priority
        
        Returns:
            Created task
        """
        # Create task in delegation engine
        task = self.delegation.create_task(title, description, priority=priority)
        
        # Auto-assign or manual assign
        if assign_to:
            self.delegation.assign_task(task.task_id, assign_to)
        elif Config.ENABLE_AUTO_ASSIGN:
            agent_id = self.delegation.auto_assign_task(task.task_id, self.skill_registry)
            if agent_id:
                logger.info(f"Auto-assigned task {task.task_id} to agent {agent_id}")
        
        # Legacy tracking
        branch_name = self.git.create_branch(task.task_id, "orchestrator")
        task.branch_name = branch_name
        self.state.create_task(task.task_id, description, branch_name)
        
        self.delegation._save()
        
        return task
    
    async def process_task_with_agent(self, task_id: str) -> bool:
        """Process a task using CrewAI agents.
        
        This executes the actual work through the agent system.
        """
        task = self.delegation.get_task(task_id)
        if not task or not task.assigned_to:
            logger.error(f"Task {task_id} not found or not assigned")
            return False
        
        agent_instance = self.role_manager.get_instance(task.assigned_to)
        if not agent_instance:
            logger.error(f"Agent instance not found: {task.assigned_to}")
            return False
        
        role = self.role_manager.get_role(agent_instance.role_id)
        if not role:
            logger.error(f"Role not found: {agent_instance.role_id}")
            return False
        
        # Build prompt
        system_prompt = role.build_system_prompt(self.skill_registry)
        project_context = self._get_project_context()
        
        task_prompt = PromptComposer.compose_task_prompt(
            task.description,
            role.name,
            project_context,
            role.get_allowed_tools(self.skill_registry)
        )
        
        # Update status
        task.status = "in_progress"
        self.delegation._save()
        self.state.update_task_status(task_id, "running")
        
        try:
            # Rate limiting check
            limit_status = self.rate_limiter.check_rate_limit()
            if limit_status.is_limited:
                wait_time = limit_status.retry_after
                logger.info(f"Rate limited, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

            # Record task start
            self.perf_tracker.record_task_start(
                task_id=task_id,
                description=task.description,
                agents=[agent_instance.name]
            )

            # Check if agent should delegate
            if role.can_create_subtasks and Config.ENABLE_HIERARCHICAL_DELEGATION:
                # Analyze if task needs delegation
                subtasks = await self._analyze_and_delegate(task, agent_instance, role)
                if subtasks:
                    logger.info(f"Task {task_id} delegated into {len(subtasks)} subtasks")
                    return True

            # Execute directly with CrewAI
            logger.info(f"Executing task {task_id} with agent {agent_instance.name}")

            # Create CrewAI agent
            crew_agent = self.agent_manager.create_dynamic_agent(
                name=agent_instance.name,
                role=role.name,
                goal=f"Complete the task: {task.title}",
                backstory=system_prompt,
                tools=role.get_allowed_tools(self.skill_registry)
            )

            # Execute
            result = self.agent_manager.execute_agent_task(
                crew_agent,
                task_prompt,
                project_context
            )

            # Track cost
            estimated_tokens = (len(system_prompt) + len(task_prompt) + len(str(result))) // 4
            self.cost_tracker.record_usage(
                model=Config.OPENAI_MODEL,
                prompt_tokens=len(system_prompt) // 4,
                completion_tokens=len(str(result)) // 4,
                agent_name=agent_instance.name,
                task_id=task_id
            )

            # Update task
            task.result_summary = str(result)[:5000]
            task.status = "completed"
            task.completed_at = datetime.now().isoformat()
            
            # Get changed files
            changed_files = self.git.get_changed_files(task.branch_name)
            task.deliverables = changed_files
            validation_ok = True

            # Validate if files changed
            if changed_files:
                validation = self.validator.validate_all(changed_files)
                validation_ok = validation.success
                if not validation.success and Config.ENABLE_ROLLBACK:
                    logger.error(f"Validation failed for task {task_id}")
                    self.git.rollback_branch(task.branch_name)
                    task.status = "failed"
                    task.error_message = f"Validation failed: {validation.message}"
                    self.delegation._save()
                    return False
                
                # Commit changes
                self.git.stage_files(changed_files)
                self.git.commit(f"Agent completed: {task.title[:50]}", author_name=agent_instance.name)
            
            # Check approval requirement
            if role.approval_required:
                task.status = "under_review"
                self.delegation.request_approval(task_id, "system")
            else:
                agent_instance.complete_task(task_id, success=True)
                self.role_manager.update_instance(
                    agent_instance.instance_id,
                    status="idle",
                    current_task_id=None
                )
            
            self.delegation._save()
            self.state.update_task_status(task_id, task.status)

            # Record performance
            self.perf_tracker.record_task_complete(
                task_id=task_id,
                success=task.status not in ("failed", "rejected"),
                files_created=len([f for f in task.deliverables if (self.git.project_path / f).exists()]) if task.deliverables else 0,
                files_modified=len(task.deliverables) if task.deliverables else 0,
                tokens_used=estimated_tokens,
                cost=0.0,
                validation_passed=validation_ok,
                approved=(task.status == "completed")
            )
            self.rate_limiter.record_request()

            return True

        except Exception as e:
            logger.exception(f"Error processing task {task_id}: {e}")
            task.status = "failed"
            task.error_message = str(e)
            agent_instance.complete_task(task_id, success=False)
            self.role_manager.update_instance(
                agent_instance.instance_id,
                status="idle",
                current_task_id=None
            )
            self.delegation._save()
            self.state.update_task_status(task_id, "failed", str(e))

            # Record failure performance
            self.perf_tracker.record_task_complete(
                task_id=task_id,
                success=False,
                tokens_used=len(system_prompt) // 4 if 'system_prompt' in dir() else 0,
                cost=0.0,
                validation_passed=False,
                approved=False
            )
            return False
    
    async def _analyze_and_delegate(self, task: DelegatedTask,
                                   agent: AgentInstance,
                                   role: AgentRole) -> List[Dict]:
        """Analyze if a task should be delegated and create subtasks."""
        # Simple heuristic: check if task mentions multiple areas
        desc_lower = task.description.lower()
        
        subtask_defs = []
        
        # If task mentions backend + frontend, delegate separately
        has_backend = any(kw in desc_lower for kw in ['api', 'backend', 'server', 'database', 'model'])
        has_frontend = any(kw in desc_lower for kw in ['ui', 'frontend', 'page', 'component', 'html', 'css'])
        has_devops = any(kw in desc_lower for kw in ['deploy', 'ci/cd', 'pipeline', 'docker', 'infrastructure'])
        has_security = any(kw in desc_lower for kw in ['security', 'auth', 'vulnerability', 'audit'])
        
        if has_backend and has_frontend:
            subtask_defs.append({
                'title': f"Backend: {task.title}",
                'description': f"Implement backend for: {task.description}",
                'assign_to': 'senior_engineer',
                'priority': task.priority
            })
            subtask_defs.append({
                'title': f"Frontend: {task.title}",
                'description': f"Implement frontend for: {task.description}",
                'assign_to': 'senior_engineer',
                'priority': task.priority
            })
        
        if has_devops:
            subtask_defs.append({
                'title': f"DevOps: {task.title}",
                'description': f"Set up infrastructure for: {task.description}",
                'assign_to': 'devops_engineer',
                'priority': task.priority
            })
        
        if has_security:
            subtask_defs.append({
                'title': f"Security Review: {task.title}",
                'description': f"Review security aspects of: {task.description}",
                'assign_to': 'security_engineer',
                'priority': 'high'
            })
        
        if subtask_defs:
            self.delegation.delegate_task(task.task_id, agent.instance_id, subtask_defs)
        
        return subtask_defs
    
    def _get_project_context(self) -> str:
        """Get current project context."""
        try:
            context = self.project_scanner.scan()
            return context.to_summary()
        except Exception as e:
            logger.warning(f"Could not scan project context: {e}")
            return "Project context unavailable"
    
    # Approval Management
    # -------------------------------------------------------------------------
    
    async def approve_task(self, task_id: str, approver_id: str = "user", notes: str = "") -> bool:
        """Approve a pending task."""
        return self.delegation.approve_task(task_id, approver_id, notes)
    
    async def reject_task(self, task_id: str, reviewer_id: str = "user", reason: str = "") -> bool:
        """Reject a pending task."""
        return self.delegation.reject_task(task_id, reviewer_id, reason)
    
    # Status & Queries
    # -------------------------------------------------------------------------
    
    def get_status(self) -> Dict[str, Any]:
        """Get full system status."""
        return {
            'orchestrator': 'running',
            'team': self.get_team_summary(),
            'tasks': self.delegation.get_stats(),
            'project': Config.PROJECT_NAME,
            'project_type': Config.PROJECT_TYPE,
            'skills_loaded': len(self.skill_registry.skills),
            'costs': {
                'today': self.cost_tracker.get_remaining_budget(),
                'budget': Config.DAILY_BUDGET_LIMIT
            },
            'rate_limits': self.rate_limiter.get_status(),
            'performance': self.perf_tracker.get_system_summary()
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get detailed task status."""
        return self.delegation.get_task_tree(task_id)
    
    # CLI Interface Methods
    # -------------------------------------------------------------------------
    
    def run_cli(self):
        """Run interactive CLI mode."""
        from cli.interface import CLIInterface
        cli = CLIInterface(self)
        cli.run()
    
    def setup_telegram(self):
        """Setup Telegram bot integration."""
        from remote.telegram_bot import TelegramBot
        
        async def task_callback(description, update, context):
            # Parse title from description (first line or first 50 chars)
            title = description.split('\n')[0][:50]
            task = await self.submit_task(title, description)
            
            if update and update.effective_chat:
                await self._notify(
                    update.effective_chat.id,
                    f"Task created: {task.task_id}\nTitle: {title}\nStatus: {task.status}"
                )
                
                # Process the task
                await self.process_task_with_agent(task.task_id)
                
                # Update user
                task = self.delegation.get_task(task.task_id)
                await self._notify(
                    update.effective_chat.id,
                    f"Task {task.task_id} status: {task.status}"
                )
        
        self.telegram = TelegramBot(
            state_manager=self.state,
            on_task_callback=task_callback,
            orchestrator=self
        )
    
    def run_telegram(self):
        """Run in Telegram bot mode."""
        print("=" * 60)
        print("Agent Orchestrator - Telegram Bot Mode")
        print("=" * 60)
        print()
        
        self.setup_telegram()
        
        print(f"Bot configured for project: {Config.PROJECT_NAME}")
        print(f"Team: {len(self.role_manager.instances)} agents ready")
        print("Send /start to your bot on Telegram")
        print("Press Ctrl+C to stop")
        print()
        
        self.telegram.run()
    
    async def _notify(self, chat_id: int, message: str):
        """Send notification via Telegram."""
        if self.telegram and self.telegram.application:
            try:
                await self.telegram.application.bot.send_message(
                    chat_id=chat_id,
                    text=message[:4000],
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agent Orchestrator - Multi-agent system for software development"
    )
    parser.add_argument(
        '--mode',
        choices=['cli', 'telegram'],
        default='cli',
        help='Run mode: cli (interactive) or telegram (bot mode)'
    )
    parser.add_argument(
        '--approve',
        metavar='TASK_ID',
        help='Approve a pending task'
    )
    parser.add_argument(
        '--reject',
        metavar='TASK_ID',
        help='Reject a pending task'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show system status'
    )
    
    args = parser.parse_args()
    
    try:
        orchestrator = Orchestrator()
        
        if args.approve:
            asyncio.run(orchestrator.approve_task(args.approve))
            print(f"Task {args.approve} approved")
        elif args.reject:
            asyncio.run(orchestrator.reject_task(args.reject))
            print(f"Task {args.reject} rejected")
        elif args.status:
            status = orchestrator.get_status()
            import json
            print(json.dumps(status, indent=2, default=str))
        elif args.mode == 'telegram':
            orchestrator.run_telegram()
        else:
            orchestrator.run_cli()
            
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        logger.exception("Fatal error")
        print(f"\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
