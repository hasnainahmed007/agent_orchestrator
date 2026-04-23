"""Telegram bot for remote control of agents."""
import logging
from pathlib import Path
from typing import Optional, Callable
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config.settings import Config
from core.state_manager import StateManager


logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for remote agent control."""
    
    def __init__(self, state_manager: StateManager, on_task_callback: Optional[Callable] = None):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.allowed_users = Config.TELEGRAM_ALLOWED_USERS
        self.state_manager = state_manager
        self.on_task_callback = on_task_callback
        self.application: Optional[Application] = None
        
    def _is_authorized(self, user_id: str) -> bool:
        """Check if user is authorized."""
        return str(user_id) in self.allowed_users
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user_id = str(update.effective_user.id)
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
        
        welcome_message = f"""
🤖 *Agent Orchestrator Bot*

Welcome! I'm here to help you manage your Laravel project remotely.

*Available Commands:*
/task <description> - Submit a new task
/status - Check current status
/tasks - List all tasks
/approve - Approve pending changes
/reject - Reject pending changes
/changes - View pending changes
/logs - View recent activity
/help - Show this help

*Project:* {Config.PROJECT_NAME}
*Status:* Ready to work
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        user_id = str(update.effective_user.id)
        
        if not self._is_authorized(user_id):
            return
        
        help_text = """
*Commands:*

*/task <description>*
Submit a task to the agents.
Example: `/task Create API endpoint for user registration`

*/status*
Show current agent activity and system status.

*/tasks*
List all tasks (pending, running, completed, waiting approval).

*/approve [task_id]*
Approve and merge changes from a completed task.

*/reject [task_id]*
Reject changes and rollback the task.

*/changes [task_id]*
View the diff of changes for a pending task.

*/logs [count]*
View recent agent activity logs.

*/stop*
Pause all agent activities (currently running tasks will complete).
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /task command."""
        user_id = str(update.effective_user.id)
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("⛔ Not authorized.")
            return
        
        # Get task description
        task_description = ' '.join(context.args)
        
        if not task_description:
            await update.message.reply_text(
                "❌ Please provide a task description.\n"
                "Example: `/task Create API endpoint for user registration`",
                parse_mode='Markdown'
            )
            return
        
        # Send confirmation
        await update.message.reply_text(
            f"📋 *Task Received*\n\n{task_description}\n\n⏳ Processing...",
            parse_mode='Markdown'
        )
        
        # Log activity
        self.state_manager.log_activity(
            task_id="pending",
            agent="user",
            action="task_submitted",
            details=task_description
        )
        
        # Call callback if provided
        if self.on_task_callback:
            try:
                await self.on_task_callback(task_description, update, context)
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await update.message.reply_text(
                    f"❌ Error processing task: {str(e)[:200]}"
                )
        else:
            await update.message.reply_text(
                "✅ Task queued. Agents will start working on it shortly."
            )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        user_id = str(update.effective_user.id)
        
        if not self._is_authorized(user_id):
            return
        
        stats = self.state_manager.get_stats()
        pending = self.state_manager.get_pending_approvals()
        active = self.state_manager.get_active_tasks()
        
        status_text = f"""
📊 *System Status*

*Tasks:*
- Pending: {stats['pending']}
- Running: {stats['running']}
- Completed: {stats['completed']}
- Failed: {stats['failed']}
- Waiting Approval: {stats['waiting_approval']}

*Active Tasks:*
{chr(10).join([f"- {t.id}: {t.description[:50]}..." for t in active]) if active else "None"}

*Pending Approvals:*
{chr(10).join([f"- {t.id}: {t.description[:50]}..." for t in pending]) if pending else "None"}
        """
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tasks command."""
        user_id = str(update.effective_user.id)
        
        if not self._is_authorized(user_id):
            return
        
        tasks = self.state_manager.list_tasks()
        
        if not tasks:
            await update.message.reply_text("📭 No tasks found.")
            return
        
        # Show last 10 tasks
        task_list = []
        for task in tasks[:10]:
            status_emoji = {
                'pending': '⏳',
                'running': '🔄',
                'completed': '✅',
                'failed': '❌',
                'waiting_approval': '⏸️',
                'rejected': '🚫'
            }.get(task.status, '❓')
            
            task_list.append(
                f"{status_emoji} *{task.id}*\n"
                f"   Status: {task.status}\n"
                f"   {task.description[:60]}..."
            )
        
        tasks_text = "📋 *Recent Tasks*\n\n" + "\n\n".join(task_list)
        
        await update.message.reply_text(tasks_text, parse_mode='Markdown')
    
    async def approve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /approve command."""
        user_id = str(update.effective_user.id)
        
        if not self._is_authorized(user_id):
            return
        
        task_id = context.args[0] if context.args else None
        
        if not task_id:
            # Show pending approvals
            pending = self.state_manager.get_pending_approvals()
            if not pending:
                await update.message.reply_text("✅ No tasks waiting for approval.")
                return
            
            # Create buttons for pending tasks
            keyboard = [
                [InlineKeyboardButton(f"Approve {t.id}", callback_data=f"approve_{t.id}")]
                for t in pending[:5]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "⏸️ *Pending Approvals*\n\nSelect a task to approve:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        # Approve specific task
        task = self.state_manager.get_task(task_id)
        if not task:
            await update.message.reply_text(f"❌ Task {task_id} not found.")
            return
        
        if task.status != 'waiting_approval':
            await update.message.reply_text(f"⚠️ Task {task_id} is not waiting for approval (status: {task.status}).")
            return
        
        await update.message.reply_text(f"⏳ Approving task {task_id}...")
        
        # This would trigger the merge - actual implementation in main
        self.state_manager.log_activity(task_id, "user", "approve_requested")
        
        await update.message.reply_text(f"✅ Task {task_id} approved for merge.")
    
    async def reject_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reject command."""
        user_id = str(update.effective_user.id)
        
        if not self._is_authorized(user_id):
            return
        
        task_id = context.args[0] if context.args else None
        
        if not task_id:
            await update.message.reply_text("❌ Please specify a task ID: `/reject TASK-001`", parse_mode='Markdown')
            return
        
        task = self.state_manager.get_task(task_id)
        if not task:
            await update.message.reply_text(f"❌ Task {task_id} not found.")
            return
        
        if task.status != 'waiting_approval':
            await update.message.reply_text(f"⚠️ Task {task_id} cannot be rejected (status: {task.status}).")
            return
        
        await update.message.reply_text(f"🚫 Rejecting task {task_id} and rolling back changes...")
        
        self.state_manager.log_activity(task_id, "user", "reject_requested")
        
        await update.message.reply_text(f"✅ Task {task_id} rejected and changes rolled back.")
    
    async def changes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /changes command."""
        user_id = str(update.effective_user.id)
        
        if not self._is_authorized(user_id):
            return
        
        task_id = context.args[0] if context.args else None
        
        if not task_id:
            await update.message.reply_text("❌ Please specify a task ID: `/changes TASK-001`", parse_mode='Markdown')
            return
        
        task = self.state_manager.get_task(task_id)
        if not task:
            await update.message.reply_text(f"❌ Task {task_id} not found.")
            return
        
        changes = task.changes_summary or "No changes recorded."
        
        # Truncate if too long
        if len(changes) > 4000:
            changes = changes[:4000] + "\n\n... (truncated)"
        
        await update.message.reply_text(
            f"📄 *Changes for {task_id}*\n\n```\n{changes}\n```",
            parse_mode='Markdown'
        )
    
    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /logs command."""
        user_id = str(update.effective_user.id)
        
        if not self._is_authorized(user_id):
            return
        
        count = int(context.args[0]) if context.args and context.args[0].isdigit() else 10
        count = min(count, 50)  # Limit to 50
        
        activities = self.state_manager.get_recent_activities(count)
        
        if not activities:
            await update.message.reply_text("📭 No recent activity.")
            return
        
        log_lines = []
        for activity in activities:
            time = activity['timestamp'][11:19]  # HH:MM:SS
            log_lines.append(
                f"`{time}` *{activity['agent']}*: {activity['action']}"
            )
        
        logs_text = "📝 *Recent Activity*\n\n" + "\n".join(log_lines)
        
        await update.message.reply_text(logs_text, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith('approve_'):
            task_id = data.replace('approve_', '')
            await query.edit_message_text(f"⏳ Approving task {task_id}...")
            self.state_manager.log_activity(task_id, "user", "approve_requested")
            await query.edit_message_text(f"✅ Task {task_id} approved for merge.")
        
        elif data.startswith('reject_'):
            task_id = data.replace('reject_', '')
            await query.edit_message_text(f"🚫 Rejecting task {task_id}...")
            self.state_manager.log_activity(task_id, "user", "reject_requested")
            await query.edit_message_text(f"✅ Task {task_id} rejected.")
    
    async def notify_task_update(self, chat_id: int, task_id: str, status: str, message: str):
        """Send notification about task update.
        
        Args:
            chat_id: Telegram chat ID
            task_id: Task ID
            status: Status emoji/indicator
            message: Message to send
        """
        if not self.application:
            return
        
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=f"{status} *Task {task_id}*\n\n{message}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    async def notify_approval_request(self, chat_id: int, task_id: str, branch: str, changes_summary: str):
        """Send approval request notification.
        
        Args:
            chat_id: Telegram chat ID
            task_id: Task ID
            branch: Git branch name
            changes_summary: Summary of changes
        """
        if not self.application:
            return
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{task_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{task_id}")
            ],
            [InlineKeyboardButton("📄 View Changes", callback_data=f"changes_{task_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Get changed files count
        files_changed = len([line for line in changes_summary.split('\n') if line.startswith('+') or line.startswith('-')])
        
        message = f"""
⏸️ *Approval Required*

Task: *{task_id}*
Branch: `{branch}`
Files Modified: ~{files_changed} lines

Use the buttons below to approve or reject.
        """
        
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send approval request: {e}")
    
    def setup_handlers(self):
        """Set up command handlers."""
        self.application = Application.builder().token(self.token).build()
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("task", self.task_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("tasks", self.tasks_command))
        self.application.add_handler(CommandHandler("approve", self.approve_command))
        self.application.add_handler(CommandHandler("reject", self.reject_command))
        self.application.add_handler(CommandHandler("changes", self.changes_command))
        self.application.add_handler(CommandHandler("logs", self.logs_command))
        
        # Callback handler
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Update {update} caused error: {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again."
            )
    
    def run(self):
        """Start the bot (blocking)."""
        if not self.token or self.token == 'your_telegram_bot_token_here':
            raise ValueError("Telegram bot token not configured. Set TELEGRAM_BOT_TOKEN in .env")
        
        self.setup_handlers()
        logger.info("Starting Telegram bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    async def start(self):
        """Start the bot (non-blocking for async)."""
        if not self.token or self.token == 'your_telegram_bot_token_here':
            raise ValueError("Telegram bot token not configured. Set TELEGRAM_BOT_TOKEN in .env")
        
        self.setup_handlers()
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    async def stop(self):
        """Stop the bot."""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()