# Agent Orchestrator - Setup Guide

## Prerequisites

- Python 3.10 or higher
- Git (with your project in a git repository)
- OpenAI API key
- Telegram account (for bot control)

## Step-by-Step Setup

### 1. Get OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (you won't see it again!)

### 2. Create Telegram Bot

1. Open Telegram and search for @BotFather
2. Send `/newbot`
3. Follow instructions to name your bot
4. Copy the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 3. Get Your Telegram User ID

1. Search for @userinfobot on Telegram
2. Start the bot
3. It will reply with your user ID (e.g., `123456789`)

### 4. Run Setup Script

**On Windows:**
```cmd
cd agent_orchestrator
setup.bat
```

**Manual Setup:**
```bash
cd agent_orchestrator

# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Configure Environment

Edit the `.env` file:

```env
# Required
OPENAI_API_KEY=sk-your-openai-key-here
TELEGRAM_BOT_TOKEN=123456789:your-bot-token-here
TELEGRAM_ALLOWED_USERS=your-telegram-user-id

# Optional - usually correct by default
PROJECT_PATH=C:\xampp\htdocs\Office\glamdemy_admin_panel
MAIN_BRANCH=main
```

### 6. Test Installation

```bash
# Activate virtual environment
venv\Scripts\activate

# Check status
python main.py --status

# Test with a simple task
python main.py --mode cli
```

## Usage Examples

### CLI Mode (Quick Tasks)

```bash
python main.py --mode cli
# Enter task: "Create Contact model with migration"
```

### Telegram Bot Mode (Remote Control)

```bash
python main.py --mode telegram
```

Then in Telegram:
```
/task Create API endpoint for user login
/status
/approve TASK-0001
```

### Managing Tasks

```bash
# View status
python main.py --status

# Approve a task
python main.py --approve TASK-0001

# Reject a task
python main.py --reject TASK-0001
```

## Troubleshooting

### "Python not found"
- Add Python to your PATH
- Or use `py` instead of `python`

### "Git not found"
- Install Git: https://git-scm.com/download/win
- Or use Git Bash

### "OpenAI API error"
- Check your API key in .env
- Ensure you have API credits

### "Telegram bot not responding"
- Check bot token in .env
- Make sure you sent `/start` to your bot
- Verify your user ID is in ALLOWED_USERS

## Directory Structure

```
agent_orchestrator/
├── agents/          # Agent definitions
├── core/            # Core modules
│   ├── git_manager.py
│   ├── project_context.py
│   ├── validator.py
│   └── state_manager.py
├── remote/          # Telegram bot
├── config/          # Configuration
├── logs/            # Execution logs
├── state/           # Task states
├── main.py          # Entry point
├── requirements.txt # Dependencies
└── .env             # Configuration
```

## Next Steps

1. Try a simple task in CLI mode first
2. Test Telegram bot
3. Review the PLAN.md for detailed architecture
4. Customize agent prompts in config/prompts.py

## Support

If you encounter issues:
1. Check logs in `logs/orchestrator.log`
2. Review the PLAN.md for details
3. Ensure all API keys are valid
4. Test git operations manually