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
    filters,
    ConversationHandler
)

from config.settings import Config
from core.state_manager import StateManager


logger = logging.getLogger(__name__)

# Conversation states
CREATE_AGENT_NAME, CREATE_AGENT_ROLE, CREATE_AGENT_SKILLS = range(3)
SUBMIT_TASK_TITLE, SUBMIT_TASK_DESC, SUBMIT_TASK_PRIORITY = range(3, 6)


class TelegramBot:
    """Telegram bot for remote agent control."""
    
    def __init__(self, state_manager: StateManager, on_task_callback: Optional[Callable] = None, orchestrator=None):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.allowed_users = Config.TELEGRAM_ALLOWED_USERS
        self.state_manager = state_manager
        self.on_task_callback = on_task_callback
        self.orchestrator = orchestrator
        self.application: Optional[Application] = None
        
    def _is_authorized(self, user_id: str) -> bool:
        """Check if user is authorized."""
        return str(user_id) in self.allowed_users
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user_id = str(update.effective_user.id)
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        team_info = ""
        if self.orchestrator:
            summary = self.orchestrator.get_team_summary()
            team_info = f"\n*Team:* {summary['total_instances']} agents | {summary['available_agents']} available"
        
        welcome_message = f"""
*Agent Orchestrator Bot*

Welcome! Manage your development team remotely.

*Available Commands:*
/team - Show team overview
/agents - List all agents
/roles - List available roles
createagent - Create a new agent
/submit - Submit a new task
/tasks [status] - List tasks
/task <id> - Task details
/approve <id> - Approve task
/reject <id> - Reject task
/skills - List skills
/status - System status
/help - Show help

*Project:* {Config.PROJECT_NAME}{team_info}
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        user_id = str(update.effective_user.id)
        
        if not self._is_authorized(user_id):
            return
        
        help_text = """
*Commands:*

*/team*
Show team overview with all agents and roles.

*/agents*
List all agent instances with their status.

*/roles*
List all available roles you can assign to agents.

*/createagent*
Create a new agent instance interactively.

*/submit*
Submit a new task to the team.

*/tasks [status]*
List tasks. Optional filter: pending, running, completed, failed, under_review.

*/task <task_id>*
Show detailed information about a task.

*/approve <task_id>*
Approve a task waiting for review.

*/reject <task_id>*
Reject a task and return it for rework.

*/skills*
List all available skill modules.

*/status*
Show system status and statistics.
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    # Team & Agent Commands
    # -------------------------------------------------------------------------
    
    async def team_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /team command."""
        user_id = str(update.effective_user.id)
        if not self._is_authorized(user_id):
            return
        
        if not self.orchestrator:
            await update.message.reply_text("Orchestrator not initialized.")
            return
        
        summary = self.orchestrator.get_team_summary()
        
        status_text = f"""
*Team Overview*

*Stats:*
- Roles: {summary['total_roles']}
- Agents: {summary['total_instances']}
- Available: {summary['available_agents']}
- Busy: {summary['busy_agents']}

*Agents:*
"""
        for agent in summary['agents'][:10]:
            status_icon = '\U0001F7E2' if agent['status'] == 'idle' else '\U0001F7E1'
            status_text += f"\n{status_icon} {agent['name']} ({agent['role']})"
            status_text += f"\n   Tasks: {agent['tasks_completed']}"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def agents_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /agents command."""
        user_id = str(update.effective_user.id)
        if not self._is_authorized(user_id):
            return
        
        if not self.orchestrator:
            await update.message.reply_text("Orchestrator not initialized.")
            return
        
        instances = self.orchestrator.role_manager.list_instances()
        if not instances:
            await update.message.reply_text("No agents created yet. Use /createagent to create one.")
            return
        
        text = "*Agent Instances*\n\n"
        for inst in instances:
            role = self.orchestrator.role_manager.get_role(inst.role_id)
            role_name = role.name if role else "Unknown"
            
            status_icon = {
                'idle': '\U0001F7E2',
                'busy': '\U0001F7E1',
                'offline': '\U000026AB'
            }.get(inst.status, '\U000026AB')
            
            text += f"{status_icon} *{inst.name}*\n"
            text += f"   Role: {role_name}\n"
            text += f"   Tasks: {inst.total_tasks_completed} done\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def roles_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /roles command."""
        user_id = str(update.effective_user.id)
        if not self._is_authorized(user_id):
            return
        
        if not self.orchestrator:
            await update.message.reply_text("Orchestrator not initialized.")
            return
        
        roles = self.orchestrator.role_manager.get_roles_by_hierarchy()
        
        text = "*Available Roles*\n\n"
        for role in roles:
            instance_count = len(self.orchestrator.role_manager.get_instances_by_role(role.role_id))
            text += f"[{role.hierarchy_level}] *{role.name}*\n"
            text += f"   ID: `{role.role_id}`\n"
            text += f"   Skills: {', '.join(role.skills[:3])}\n"
            text += f"   Agents: {instance_count}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def skills_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /skills command."""
        user_id = str(update.effective_user.id)
        if not self._is_authorized(user_id):
            return
        
        if not self.orchestrator:
            await update.message.reply_text("Orchestrator not initialized.")
            return
        
        skills = self.orchestrator.skill_registry.get_skills_by_category()
        
        text = "*Available Skills*\n\n"
        for category, skill_list in skills.items():
            text += f"*{category.upper()}*\n"
            for skill in skill_list:
                text += f"  - {skill.name} (`{skill.skill_id}`)\n"
            text += "\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # Create Agent Conversation
    # -------------------------------------------------------------------------
    
    async def createagent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start create agent conversation."""
        user_id = str(update.effective_user.id)
        if not self._is_authorized(user_id):
            return
        
        await update.message.reply_text("Let's create a new agent!\n\nWhat's the agent's name?")
        return CREATE_AGENT_NAME
    
    async def createagent_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle agent name input."""
        context.user_data['agent_name'] = update.message.text.strip()
        
        roles = self.orchestrator.role_manager.get_roles_by_hierarchy()
        text = "Choose a role:\n\n"
        for i, role in enumerate(roles, 1):
            text += f"{i}. {role.name} ({role.role_id})\n"
        
        await update.message.reply_text(text)
        return CREATE_AGENT_ROLE
    
    async def createagent_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle role selection."""
        text = update.message.text.strip()
        
        roles = self.orchestrator.role_manager.get_roles_by_hierarchy()
        selected_role = None
        
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(roles):
                selected_role = roles[idx]
        else:
            selected_role = self.orchestrator.role_manager.get_role(text)
        
        if not selected_role:
            await update.message.reply_text("Invalid role. Please try again or /cancel.")
            return CREATE_AGENT_ROLE
        
        context.user_data['agent_role_id'] = selected_role.role_id
        
        await update.message.reply_text(
            f"Selected role: {selected_role.name}\n\n"
            f"Add extra skills? (comma-separated skill IDs, or 'none'):"
        )
        return CREATE_AGENT_SKILLS
    
    async def createagent_skills(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle skills input and create agent."""
        text = update.message.text.strip()
        
        skill_overrides = []
        if text.lower() != 'none':
            skill_overrides = [s.strip() for s in text.split(',') if s.strip()]
        
        name = context.user_data['agent_name']
        role_id = context.user_data['agent_role_id']
        
        try:
            instance = self.orchestrator.create_agent(
                name=name,
                role_id=role_id,
                skill_overrides=skill_overrides
            )
            
            await update.message.reply_text(
                f"Agent created successfully!\n\n"
                f"Name: {instance.name}\n"
                f"ID: `{instance.instance_id}`\n"
                f"Role: {role_id}",
                parse_mode='Markdown'
            )
        except Exception as e:
            await update.message.reply_text(f"Error creating agent: {e}")
        
        return ConversationHandler.END
    
    async def cancel_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current conversation."""
        await update.message.reply_text("Cancelled.")
        return ConversationHandler.END
    
    # Task Commands
    # -------------------------------------------------------------------------
    
    async def submit_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start submit task conversation."""
        user_id = str(update.effective_user.id)
        if not self._is_authorized(user_id):
            return
        
        await update.message.reply_text("Submit a new task.\n\nWhat's the task title?")
        return SUBMIT_TASK_TITLE
    
    async def submit_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle task title."""
        context.user_data['task_title'] = update.message.text.strip()
        await update.message.reply_text("Task description:")
        return SUBMIT_TASK_DESC
    
    async def submit_desc(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle task description."""
        context.user_data['task_desc'] = update.message.text.strip()
        await update.message.reply_text("Priority? (low/normal/high/critical)")
        return SUBMIT_TASK_PRIORITY
    
    async def submit_priority(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle priority and create task."""
        priority = update.message.text.strip().lower()
        if priority not in ['low', 'normal', 'high', 'critical']:
            priority = 'normal'
        
        title = context.user_data['task_title']
        desc = context.user_data['task_desc']
        
        try:
            task = await self.orchestrator.submit_task(
                title=title,
                description=desc,
                priority=priority
            )
            
            await update.message.reply_text(
                f"Task submitted!\n\n"
                f"ID: `{task.task_id}`\n"
                f"Title: {task.title}\n"
                f"Status: {task.status}\n"
                f"Priority: {task.priority}",
                parse_mode='Markdown'
            )
            
            # Auto-process if possible
            if task.assigned_to:
                await update.message.reply_text("Processing task...")
                await self.orchestrator.process_task_with_agent(task.task_id)
                task = self.orchestrator.delegation.get_task(task.task_id)
                await update.message.reply_text(f"Task status: {task.status}")
            
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")
        
        return ConversationHandler.END
    
    async def tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tasks command."""
        user_id = str(update.effective_user.id)
        if not self._is_authorized(user_id):
            return
        
        status_filter = context.args[0] if context.args else None
        tasks = self.orchestrator.delegation.list_tasks(status=status_filter)
        
        if not tasks:
            await update.message.reply_text("No tasks found.")
            return
        
        text = "*Tasks*\n\n"
        for task in tasks[:15]:
            status_icon = {
                'pending': '\u23F3',
                'assigned': '\U0001F4CB',
                'in_progress': '\U0001F504',
                'delegated': '\U0001F465',
                'under_review': '\U0001F50D',
                'completed': '\u2705',
                'failed': '\u274C'
            }.get(task.status, '\u2753')
            
            text += f"{status_icon} `{task.task_id}` - {task.title}\n"
            text += f"   Status: {task.status}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /task command."""
        user_id = str(update.effective_user.id)
        if not self._is_authorized(user_id):
            return
        
        task_id = context.args[0] if context.args else None
        if not task_id:
            await update.message.reply_text("Usage: /task <task_id>")
            return
        
        tree = self.orchestrator.delegation.get_task_tree(task_id)
        if not tree:
            await update.message.reply_text(f"Task not found: {task_id}")
            return
        
        task = tree['task']
        text = f"""
*Task: {task['task_id']}*

Title: {task['title']}
Status: {task['status']}
Priority: {task['priority']}

Description:
{task['description'][:200]}
"""
        if tree['assignee']:
            text += f"\nAssigned: {tree['assignee']['name']}"
        
        if task['subtasks']:
            text += f"\n\nSubtasks ({len(task['subtasks'])}):"
            for sub in task['subtasks']:
                icon = '\u2705' if sub['status'] == 'completed' else '\u23F3'
                text += f"\n{icon} {sub['title']}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def approve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /approve command."""
        user_id = str(update.effective_user.id)
        if not self._is_authorized(user_id):
            return
        
        task_id = context.args[0] if context.args else None
        if not task_id:
            # Show pending approvals
            pending = self.orchestrator.delegation.get_pending_approvals()
            if not pending:
                await update.message.reply_text("No tasks waiting for approval.")
                return
            
            keyboard = [
                [InlineKeyboardButton(f"Approve {t.task_id}", callback_data=f"approve_{t.task_id}")]
                for t in pending[:5]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Pending Approvals:\n\nSelect a task:",
                reply_markup=reply_markup
            )
            return
        
        success = await self.orchestrator.approve_task(task_id, str(user_id))
        if success:
            await update.message.reply_text(f"Task {task_id} approved.")
        else:
            await update.message.reply_text(f"Failed to approve {task_id}.")
    
    async def reject_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reject command."""
        user_id = str(update.effective_user.id)
        if not self._is_authorized(user_id):
            return
        
        task_id = context.args[0] if context.args else None
        if not task_id:
            await update.message.reply_text("Usage: /reject <task_id>")
            return
        
        success = await self.orchestrator.reject_task(task_id, str(user_id))
        if success:
            await update.message.reply_text(f"Task {task_id} rejected.")
        else:
            await update.message.reply_text(f"Failed to reject {task_id}.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        user_id = str(update.effective_user.id)
        if not self._is_authorized(user_id):
            return
        
        status = self.orchestrator.get_status()
        
        text = f"""
*System Status*

Project: {status['project']}
Type: {status['project_type']}
Skills: {status['skills_loaded']}

*Tasks:*
- Total: {status['tasks']['total_tasks']}
- Pending: {status['tasks']['pending']}
- In Progress: {status['tasks']['in_progress']}
- Under Review: {status['tasks']['under_review']}
- Completed: {status['tasks']['completed']}
- Failed: {status['tasks']['failed']}

*Team:*
- Agents: {status['team']['total_instances']}
- Available: {status['team']['available_agents']}
"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith('approve_'):
            task_id = data.replace('approve_', '')
            success = await self.orchestrator.approve_task(task_id, str(query.from_user.id))
            if success:
                await query.edit_message_text(f"Task {task_id} approved.")
            else:
                await query.edit_message_text(f"Failed to approve {task_id}.")
        
        elif data.startswith('reject_'):
            task_id = data.replace('reject_', '')
            success = await self.orchestrator.reject_task(task_id, str(query.from_user.id))
            if success:
                await query.edit_message_text(f"Task {task_id} rejected.")
            else:
                await query.edit_message_text(f"Failed to reject {task_id}.")
    
    async def notify_approval_request(self, chat_id: int, task_id: str, branch: str, changes_summary: str):
        """Send approval request notification."""
        if not self.application:
            return
        
        keyboard = [
            [
                InlineKeyboardButton("Approve", callback_data=f"approve_{task_id}"),
                InlineKeyboardButton("Reject", callback_data=f"reject_{task_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"""
*Approval Required*

Task: `{task_id}`
Branch: `{branch}`

Review the changes and approve or reject.
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
        
        # Simple command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("team", self.team_command))
        self.application.add_handler(CommandHandler("agents", self.agents_command))
        self.application.add_handler(CommandHandler("roles", self.roles_command))
        self.application.add_handler(CommandHandler("skills", self.skills_command))
        self.application.add_handler(CommandHandler("tasks", self.tasks_command))
        self.application.add_handler(CommandHandler("task", self.task_command))
        self.application.add_handler(CommandHandler("approve", self.approve_command))
        self.application.add_handler(CommandHandler("reject", self.reject_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Conversation handlers
        create_agent_conv = ConversationHandler(
            entry_points=[CommandHandler("createagent", self.createagent_command)],
            states={
                CREATE_AGENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.createagent_name)],
                CREATE_AGENT_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.createagent_role)],
                CREATE_AGENT_SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.createagent_skills)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_conversation)]
        )
        
        submit_conv = ConversationHandler(
            entry_points=[CommandHandler("submit", self.submit_command)],
            states={
                SUBMIT_TASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.submit_title)],
                SUBMIT_TASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.submit_desc)],
                SUBMIT_TASK_PRIORITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.submit_priority)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_conversation)]
        )
        
        self.application.add_handler(create_agent_conv)
        self.application.add_handler(submit_conv)
        
        # Callback handler
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Update {update} caused error: {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "An error occurred. Please try again."
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
