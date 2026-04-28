# Agent Orchestrator - Developer Guide

This file contains information for developers and contributors working on the Agent Orchestrator codebase.

## Architecture Overview

```
User Input (CLI / Telegram / API)
    |
    v
Orchestrator (orchestrator.py)
    |-- Skill Registry (skills/registry.py)
    |-- Agent Role Manager (agents/roles.py)
    |-- Task Delegation Engine (agents/delegation.py)
    |-- CrewAI Agent Manager (agents/__init__.py)
    |-- Git Manager (core/git_manager.py)
    |-- Validator (core/validator.py)
    |-- State Manager (core/state_manager.py)
    |
    v
Project Files (git branch per task)
```

## Key Components

### 1. Skill Registry (`skills/registry.py`)

Pre-defined expertise modules with best practices, coding standards, and validation rules.

**To add a new built-in skill:**
1. Add a `SkillModule` instance to `SKILL_LIBRARY` dict
2. Use the `skill_id` as the key
3. Follow the existing structure for consistency

**To add a custom skill (user-level):**
Create a JSON file in `skills/custom/` - no code changes needed.

### 2. Agent Roles (`agents/roles.py`)

**AgentRole**: Defines a role template (CEO, CTO, Senior Engineer, etc.)
- `hierarchy_level`: 1=CEO (highest), 10=Junior (lowest)
- `skills`: List of skill_ids from SkillRegistry
- `can_delegate_to`: Which roles this agent can assign tasks to
- `reviewed_by`: Which roles must approve this agent's work
- `approval_required`: Whether work needs approval before completion

**AgentInstance**: A concrete agent created from a role
- Tracks status (idle/busy/offline/error)
- Maintains task history and performance metrics
- Can have skill overrides beyond the role's base skills

**AgentRoleManager**: Persists roles and instances to JSON files in `state/`

### 3. Task Delegation (`agents/delegation.py`)

**DelegatedTask**: Top-level task
- Can have multiple SubTasks
- Tracks full lifecycle: pending → assigned → in_progress → delegated → under_review → completed/failed
- Git branch name is stored here

**SubTask**: Individual work unit
- Assigned to a specific agent instance
- Can require review
- Deliverables are file paths

**TaskDelegationEngine**: Core logic
- Creates and assigns tasks
- Handles auto-assignment based on skill matching
- Manages delegation from senior to junior agents
- Triggers approval workflows
- Persists to `state/delegated_tasks.json`

### 4. Orchestrator (`orchestrator.py`)

Main coordinator that:
1. Initializes all subsystems
2. Sets up event callbacks between delegation engine and state manager
3. Provides CLI and Telegram interfaces
4. Manages the task execution pipeline

### 5. CLI Interface (`cli/interface.py`)

Interactive terminal interface with commands for:
- Team/agents/roles management
- Task submission and tracking
- Approval workflow
- System status

Command handlers follow naming convention: `cmd_<command_name>`

### 6. Telegram Bot (`remote/telegram_bot.py`)

Uses `python-telegram-bot` with:
- Command handlers for all operations
- Conversation handlers for multi-step flows (create-agent, submit-task)
- Inline keyboards for quick actions (approve/reject)
- Callback query handlers for button clicks

## Coding Conventions

### Python Style
- Follow PEP 8
- Max line length: 88 characters (Black formatter default)
- Use type hints for function signatures
- Use docstrings for all public modules, classes, methods
- Use f-strings for formatting

### File Organization
- One class per file (mostly)
- Group related functionality in packages
- `__init__.py` exports the public API

### Naming
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

### Error Handling
- Use specific exceptions, avoid bare `except:`
- Log errors with context
- Return boolean success + message pattern for operations
- Validate inputs early (fail fast)

### State Management
- All persistent state goes to `state/` directory
- JSON files with `.json` extension
- Use `indent=2` for readable files
- Keep backups if modifying state files directly

## Adding New Features

### Adding a New CLI Command

1. Add handler method to `cli/interface.py`:
```python
def cmd_mycommand(self, args: str):
    """Handle mycommand."""
    print("My command executed with:", args)
```

2. Add to help text in `cmd_help()`

3. Command names with hyphens are auto-converted: `my-command` → `cmd_my_command`

### Adding a New Telegram Command

1. Add handler method to `remote/telegram_bot.py`:
```python
async def mycommand_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mycommand."""
    await update.message.reply_text("My command!")
```

2. Register in `setup_handlers()`:
```python
self.application.add_handler(CommandHandler("mycommand", self.mycommand_command))
```

3. For multi-step flows, use `ConversationHandler`

### Adding a New Skill

See SETUP.md "Adding Custom Skills" section. For built-in skills:

1. Add `SkillModule` to `SKILL_LIBRARY` in `skills/registry.py`
2. Include all fields: best_practices, coding_standards, tools, file_patterns, etc.
3. The skill will be automatically available

### Adding a New Default Role

1. Add `AgentRole` to `AgentRoleManager.DEFAULT_ROLES` in `agents/roles.py`
2. Assign appropriate skills, hierarchy_level, and delegation rules
3. Existing users won't see it until they reset their state or you add migration logic

## Testing

### Run Syntax Checks
```bash
python -m py_compile agents/*.py cli/*.py config/*.py core/*.py skills/*.py remote/*.py
```

### Integration Test
```bash
python -c "
from skills.registry import get_skill_registry
from agents.roles import AgentRoleManager
from agents.delegation import TaskDelegationEngine
# ... test code
"
```

### Manual Testing
```bash
# Start CLI
python main.py --mode cli

# Test commands:
# team, agents, roles, skills, create-agent, submit, tasks, status
```

## Configuration Files

### `.env` (User Configuration)
- Created from `.env.example`
- Never commit to version control
- Contains secrets (API keys, tokens)

### `state/*.json` (Runtime State)
- Auto-generated, do not edit manually
- Can be deleted to reset (will recreate defaults)
- Files:
  - `agent_roles.json` - Custom roles
  - `agent_instances.json` - Agent instances
  - `delegated_tasks.json` - Task history
  - `orchestrator_state.json` - General state
  - `performance_metrics.json` - Performance data
  - `cost_tracking.json` - API usage costs

### `skills/custom/*.json` (Custom Skills)
- User-created skill definitions
- Auto-loaded on startup
- JSON format matching SkillModule structure

## Common Patterns

### Event Callbacks
The delegation engine uses callbacks for async notifications:
```python
def _on_task_completed(self, task: DelegatedTask):
    logger.info(f"Task {task.task_id} completed")
    # Notify Telegram, update state, etc.
```

### Skill Matching
Auto-assignment scores agents based on skill keywords matching task description:
```python
def find_best_agent_for_task(self, task_description: str, skill_registry: SkillRegistry):
    # Score = keyword matches + hierarchy bonus
    # Returns best available AgentInstance
```

### Git Workflow
Each task creates a branch: `agent/{role}/{task_id}-{timestamp}`
1. Create branch from main
2. Agent makes changes
3. Validate changes
4. Commit with agent name as author
5. Wait for approval
6. Merge to main and delete branch

## Performance Considerations

- Rate limiting is built-in (`core/rate_limiter.py`)
- Cost tracking per task and per day (`core/cost_tracker.py`)
- Token quotas prevent runaway API usage
- Daily budget limit stops execution if exceeded

## Security Notes

- `.env` contains secrets - never commit it
- Telegram bot restricts access by user ID
- Git branches isolate changes
- Approval workflow prevents unauthorized merges
- Audit trail logs all actions (`core/audit_logger.py`)

## Migration Notes

### From Old Laravel-Only System
The system is now fully generic. To migrate:
1. Update `.env`: change `PROJECT_TYPE` to your type
2. Update `PROJECT_PATH` to your project
3. Create new agents with appropriate skills
4. Old task history remains in `state/` but may reference old IDs

### Resetting State
To completely reset:
```bash
rm -rf state/* logs/*
# Re-run: agents, roles, and tasks will be recreated as defaults
```

## Useful Commands

```bash
# View logs
tail -f logs/orchestrator.log

# View state
jq '.' state/agent_instances.json

# Check Python syntax
python -m py_compile <file.py>

# Run in debug mode
LOG_LEVEL=DEBUG python main.py --mode cli

# Check git status of project
cd $PROJECT_PATH && git status
```

## Contributing

1. Follow the coding conventions above
2. Test your changes with both CLI and integration tests
3. Update this file if you change architecture
4. Update SETUP.md if you add user-facing features
5. Ensure backward compatibility where possible

## Resources

- [CrewAI Documentation](https://docs.crewai.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## Contact

For issues or feature requests, please use the project's issue tracker.
