# Agent Orchestrator

A multi-agent system for automated Laravel development with remote control via Telegram.

## Features

- 🤖 **Multi-Agent System**: Specialized agents for Backend, Frontend, and Testing
- 📱 **Telegram Bot Control**: Manage agents remotely from your phone
- 🛡️ **Safe Git Workflow**: Each task creates a branch, requires approval before merge
- 🔍 **Automatic Validation**: Runs tests and validation before commits
- 📊 **State Tracking**: Persistent tracking of all tasks and activities

## Quick Start

### 1. Install Dependencies

```bash
cd agent_orchestrator
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env
```

Edit `.env` and add:
- `OPENAI_API_KEY` - Your OpenAI API key
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `TELEGRAM_ALLOWED_USERS` - Your Telegram user ID(s)

### 3. Run

**CLI Mode (single task):**
```bash
python main.py --mode cli
```

**Telegram Bot Mode:**
```bash
python main.py --mode telegram
```

## Usage

### Telegram Commands

- `/task <description>` - Submit a task
- `/status` - Check system status
- `/tasks` - List all tasks
- `/approve [task_id]` - Approve pending changes
- `/reject [task_id]` - Reject and rollback
- `/changes [task_id]` - View changes
- `/logs` - View activity

### CLI Commands

```bash
python main.py --mode cli              # Run single task
python main.py --mode telegram         # Start Telegram bot
python main.py --approve TASK-0001     # Approve task
python main.py --reject TASK-0001      # Reject task
python main.py --status                # Show status
```

## Architecture

```
User (Telegram) → Orchestrator → Agents (Backend/Frontend/Testing)
                                     ↓
                               Git Branch
                                     ↓
                               Validation
                                     ↓
                          Waiting Approval → Merge
```

## Safety

- ✅ Each task creates isolated git branch
- ✅ Automated validation before commits
- ✅ Tests must pass before approval
- ✅ Manual approval required before merge
- ✅ Automatic rollback on failure

## License

MIT