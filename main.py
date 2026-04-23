"""Main entry point for Agent Orchestrator."""
import os
import sys
import logging
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Config
from config.prompts import PROJECT_CONTEXT
from core.git_manager import GitManager
from core.project_context import ProjectContextScanner
from core.validator import Validator
from core.state_manager import StateManager
from agents import AgentManager
from tasks.definitions import TaskPlanner, TaskExecutor, TaskDefinition
from remote.telegram_bot import TelegramBot


# Setup logging
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
    """Main orchestrator that coordinates all components."""
    
    def __init__(self):
        logger.info("🚀 Initializing Agent Orchestrator...")
        
        # Validate configuration
        errors = Config.validate()
        if errors:
            logger.error("Configuration errors:")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError("Configuration validation failed")
        
        # Ensure directories exist
        Config.ensure_directories()
        
        # Initialize components
        self.git = GitManager(Config.PROJECT_PATH, Config.MAIN_BRANCH)
        self.validator = Validator(Config.PROJECT_PATH)
        self.state = StateManager(Config.STATE_FILE, Config.TASKS_FILE)
        self.agents = AgentManager(Config.PROJECT_PATH)
        self.task_planner = TaskPlanner(Config.PROJECT_PATH)
        
        # Initialize telegram bot (will be set up later)
        self.telegram: Optional[TelegramBot] = None
        self._task_counter = self._get_next_task_id()
        
        logger.info("✅ Orchestrator initialized successfully")
    
    def _get_next_task_id(self) -> int:
        """Get next task ID number."""
        existing_tasks = self.state.list_tasks()
        if not existing_tasks:
            return 1
        
        # Extract numbers from task IDs
        max_num = 0
        for task in existing_tasks:
            try:
                num = int(task.id.split('-')[1])
                max_num = max(max_num, num)
            except:
                pass
        
        return max_num + 1
    
    def generate_task_id(self) -> str:
        """Generate a new unique task ID."""
        task_id = f"TASK-{self._task_counter:04d}"
        self._task_counter += 1
        return task_id
    
    async def process_task(self, description: str, telegram_update=None, telegram_context=None) -> str:
        """Process a task from start to finish.
        
        Args:
            description: Task description
            telegram_update: Optional Telegram update for notifications
            telegram_context: Optional Telegram context
            
        Returns:
            Task ID
        """
        task_id = self.generate_task_id()
        logger.info(f"📋 Processing task {task_id}: {description}")
        
        # Notify start
        if telegram_update:
            await self._notify(
                telegram_update.effective_chat.id,
                f"🚀 Starting task {task_id}\n\n{description}"
            )
        
        try:
            # 1. Scan project for context
            logger.info("🔍 Scanning project context...")
            self.agents.scan_project()
            
            # 2. Create task plan
            logger.info("📋 Creating task plan...")
            task = self.task_planner.plan_task(task_id, description)
            
            # 3. Create git branch
            logger.info("🌿 Creating git branch...")
            branch_name = self.git.create_branch(task_id, "orchestrator")
            task.branch = branch_name
            
            # Save task to state
            self.state.create_task(task_id, description, branch_name)
            for subtask in task.subtasks:
                self.state.add_subtask(task_id, subtask.agent, subtask.description)
            
            logger.info(f"🌿 Created branch: {branch_name}")
            
            if telegram_update:
                await self._notify(
                    telegram_update.effective_chat.id,
                    f"📋 Task Plan for {task_id}:\n\n" + 
                    "\n".join([f"• [{s.agent}] {s.description[:40]}..." for s in task.subtasks])
                )
            
            # 4. Execute task
            logger.info("🤖 Executing task with agents...")
            
            executor = TaskExecutor(
                self.agents,
                self.git,
                self.validator,
                self.state
            )
            
            async def progress_callback(message):
                logger.info(message)
                if telegram_update:
                    await self._notify(telegram_update.effective_chat.id, message)
            
            await executor.execute_task(task, progress_callback)
            
            # 5. Get changed files
            changed_files = self.git.get_changed_files(branch_name)
            
            # 6. Validate changes
            if changed_files:
                logger.info(f"🔍 Validating {len(changed_files)} changed files...")
                
                if telegram_update:
                    await self._notify(
                        telegram_update.effective_chat.id,
                        f"🔍 Running validation on {len(changed_files)} files..."
                    )
                
                validation = self.validator.validate_all(changed_files)
                
                if not validation.success:
                    logger.error(f"❌ Validation failed: {validation.message}")
                    
                    if telegram_update:
                        await self._notify(
                            telegram_update.effective_chat.id,
                            f"❌ Validation failed:\n\n" + "\n".join(validation.errors[:5])
                        )
                    
                    # Rollback
                    if Config.ENABLE_ROLLBACK:
                        logger.info("🔄 Rolling back changes...")
                        self.git.rollback_branch(branch_name)
                        self.state.update_task_status(task_id, "failed", "Validation failed")
                        
                        if telegram_update:
                            await self._notify(
                                telegram_update.effective_chat.id,
                                f"🔄 Task {task_id} rolled back due to validation errors."
                            )
                    
                    return task_id
                
                logger.info("✅ Validation passed")
                
                if telegram_update:
                    await self._notify(
                        telegram_update.effective_chat.id,
                        f"✅ Validation passed!"
                    )
                
                # Commit changes
                commit_msg = f"Agent completed: {description[:50]}"
                self.git.stage_files(changed_files)
                self.git.commit(commit_msg, author_name="AgentOrchestrator")
                
                # Track files
                task.files_modified = changed_files
                
                logger.info(f"💾 Committed {len(changed_files)} files")
            
            # 7. Get diff for approval
            diff = self.git.get_diff(branch_name)
            self.state.set_changes_summary(task_id, diff[:5000])  # Truncate if needed
            
            # 8. Handle approval
            if Config.REQUIRE_APPROVAL:
                logger.info("⏸️ Waiting for user approval...")
                self.state.update_task_status(task_id, "waiting_approval")
                
                if telegram_update:
                    await self.telegram.notify_approval_request(
                        telegram_update.effective_chat.id,
                        task_id,
                        branch_name,
                        diff[:2000]  # Limit for Telegram
                    )
                
                # Wait for approval (handled by Telegram bot)
                logger.info(f"⏸️ Task {task_id} waiting for approval")
            
            elif Config.AUTO_MERGE_ON_TESTS_PASS:
                # Auto-merge
                logger.info("🔄 Auto-merging to main...")
                success, message = self.git.merge_branch(branch_name)
                
                if success:
                    self.state.update_task_status(task_id, "completed")
                    logger.info(f"✅ Task {task_id} completed and merged")
                    
                    if telegram_update:
                        await self._notify(
                            telegram_update.effective_chat.id,
                            f"✅ Task {task_id} completed and merged to {Config.MAIN_BRANCH}!"
                        )
                else:
                    self.state.update_task_status(task_id, "failed", message)
                    logger.error(f"❌ Merge failed: {message}")
                    
                    if telegram_update:
                        await self._notify(
                            telegram_update.effective_chat.id,
                            f"❌ Merge failed: {message}"
                        )
            
            return task_id
            
        except Exception as e:
            logger.exception(f"❌ Error processing task {task_id}: {e}")
            self.state.update_task_status(task_id, "failed", str(e))
            
            if telegram_update:
                await self._notify(
                    telegram_update.effective_chat.id,
                    f"❌ Task {task_id} failed:\n{str(e)[:500]}"
                )
            
            return task_id
    
    async def _notify(self, chat_id: int, message: str):
        """Send notification via Telegram."""
        if self.telegram and self.telegram.application:
            try:
                await self.telegram.application.bot.send_message(
                    chat_id=chat_id,
                    text=message[:4000],  # Telegram limit
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
    
    async def approve_task(self, task_id: str) -> bool:
        """Approve and merge a task.
        
        Args:
            task_id: Task to approve
            
        Returns:
            True if successful
        """
        task = self.state.get_task(task_id)
        if not task or task.status != "waiting_approval":
            logger.error(f"Task {task_id} not found or not waiting approval")
            return False
        
        try:
            logger.info(f"✅ Approving task {task_id}...")
            
            # Merge branch
            success, message = self.git.merge_branch(task.branch)
            
            if success:
                self.state.update_task_status(task_id, "completed")
                logger.info(f"✅ Task {task_id} approved and merged")
                
                # Clean up branch
                self.git.delete_branch(task.branch)
                
                return True
            else:
                logger.error(f"❌ Merge failed: {message}")
                return False
                
        except Exception as e:
            logger.exception(f"❌ Error approving task: {e}")
            return False
    
    async def reject_task(self, task_id: str) -> bool:
        """Reject and rollback a task.
        
        Args:
            task_id: Task to reject
            
        Returns:
            True if successful
        """
        task = self.state.get_task(task_id)
        if not task or task.status != "waiting_approval":
            logger.error(f"Task {task_id} not found or not waiting approval")
            return False
        
        try:
            logger.info(f"🚫 Rejecting task {task_id}...")
            
            # Rollback
            self.git.rollback_branch(task.branch)
            
            self.state.update_task_status(task_id, "rejected")
            logger.info(f"🚫 Task {task_id} rejected and rolled back")
            
            return True
            
        except Exception as e:
            logger.exception(f"❌ Error rejecting task: {e}")
            return False
    
    def setup_telegram(self):
        """Setup Telegram bot integration."""
        async def task_callback(description, update, context):
            await self.process_task(description, update, context)
        
        self.telegram = TelegramBot(
            state_manager=self.state,
            on_task_callback=task_callback
        )
    
    def run_cli(self):
        """Run in CLI mode (single task)."""
        print("=" * 60)
        print("🤖 Agent Orchestrator - CLI Mode")
        print("=" * 60)
        print()
        
        # Show project info
        print(f"Project: {Config.PROJECT_NAME}")
        print(f"Path: {Config.PROJECT_PATH}")
        print(f"Branch: {Config.MAIN_BRANCH}")
        print()
        
        # Get task description
        description = input("Enter task description: ").strip()
        
        if not description:
            print("❌ No task provided. Exiting.")
            return
        
        print()
        print(f"🚀 Processing: {description}")
        print("-" * 60)
        
        # Run task
        async def run():
            task_id = await self.process_task(description)
            print(f"\n✅ Task {task_id} initiated.")
            
            # Wait for completion or approval
            import time
            for _ in range(60):  # Wait up to 5 minutes
                await asyncio.sleep(5)
                task = self.state.get_task(task_id)
                if task.status in ["completed", "failed", "waiting_approval"]:
                    break
            
            task = self.state.get_task(task_id)
            print(f"\n📊 Final status: {task.status}")
            
            if task.status == "waiting_approval":
                print(f"\n⏸️ Task is waiting for approval.")
                print(f"Run: python main.py --approve {task_id}")
        
        asyncio.run(run())
    
    def run_telegram(self):
        """Run in Telegram bot mode."""
        print("=" * 60)
        print("🤖 Agent Orchestrator - Telegram Bot Mode")
        print("=" * 60)
        print()
        
        self.setup_telegram()
        
        print(f"Bot configured for project: {Config.PROJECT_NAME}")
        print("Send /start to your bot on Telegram")
        print("Press Ctrl+C to stop")
        print()
        
        self.telegram.run()
    
    def run_approve(self, task_id: str):
        """Approve a pending task."""
        async def run():
            success = await self.approve_task(task_id)
            if success:
                print(f"✅ Task {task_id} approved and merged!")
            else:
                print(f"❌ Failed to approve task {task_id}")
        
        asyncio.run(run())
    
    def run_reject(self, task_id: str):
        """Reject a pending task."""
        async def run():
            success = await self.reject_task(task_id)
            if success:
                print(f"🚫 Task {task_id} rejected and rolled back.")
            else:
                print(f"❌ Failed to reject task {task_id}")
        
        asyncio.run(run())


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agent Orchestrator - Multi-agent system for Laravel development"
    )
    parser.add_argument(
        '--mode',
        choices=['cli', 'telegram'],
        default='cli',
        help='Run mode: cli (single task) or telegram (bot mode)'
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
            orchestrator.run_approve(args.approve)
        elif args.reject:
            orchestrator.run_reject(args.reject)
        elif args.status:
            stats = orchestrator.state.get_stats()
            print("\n📊 System Status")
            print("-" * 40)
            for key, value in stats.items():
                print(f"  {key}: {value}")
            print()
        elif args.mode == 'telegram':
            orchestrator.run_telegram()
        else:
            orchestrator.run_cli()
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        logger.exception("Fatal error")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()