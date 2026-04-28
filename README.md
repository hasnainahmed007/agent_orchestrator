# Agent Orchestrator

A **multi-agent AI system** for software development with **hierarchical team management**, **skill-based task delegation**, and **remote control via Telegram**.

## Features

- 🤖 **Dynamic Multi-Agent Teams**: Create roles like CEO, CTO, Senior Engineer, Junior Engineer, DevOps, Security, QA
- 🎓 **Pre-defined Skill Modules**: Python, JavaScript, TypeScript, React, Django, Docker, PostgreSQL, System Design, Security
- 📋 **Hierarchical Task Delegation**: Senior agents auto-delegate subtasks to juniors based on expertise
- ✅ **Approval Workflow**: Junior work requires senior review before merging
- 📱 **Telegram Bot Control**: Manage your entire team remotely from your phone
- 🛡️ **Safe Git Workflow**: Each task creates an isolated branch, requires approval before merge
- 🔍 **Automatic Validation**: Syntax checks, tests, and linting before commits
- 💰 **Cost Tracking**: Per-task and daily budget limits for API usage
- 📊 **State Tracking**: Persistent tracking of all tasks, agents, and activities
- 🧩 **Custom Skills & Roles**: Add your own expertise modules and team roles

## Architecture

```
User (CLI / Telegram)
    |
    v
Orchestrator
    |-- Skill Registry (pre-defined + custom expertise)
    |-- Agent Role Manager (CEO → CTO → Senior → Junior)
    |-- Task Delegation Engine (auto-assign, delegate, review)
    |-- CrewAI Agent Manager (AI execution)
    |-- Git Manager (branch per task)
    |-- Validator (syntax + tests)
    |-- State Manager (persistent tracking)
    |
    v
Project Files (git branch per task)
    |
    v
Approval → Merge to Main
```

## Quick Start

### 1. Install Dependencies

```bash
cd agent_orchestrator
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and project settings
```

### 3. Prepare Your Project

```bash
# Create a git repository for your project
mkdir -p projects/my-project
cd projects/my-project
git init
git checkout -b main
cd ../..
```

### 4. Run

**CLI Mode (interactive):**
```bash
python main.py --mode cli
```

**Telegram Bot Mode:**
```bash
python main.py --mode telegram
```

## Usage

### CLI Commands

```bash
# Interactive CLI mode
python main.py --mode cli

# Inside the CLI:
orchestrator> team              # Show team overview
orchestrator> create-agent      # Create a new agent
orchestrator> submit            # Submit a new task
orchestrator> tasks             # List all tasks
orchestrator> approve TASK-XXX  # Approve a pending task
orchestrator> reject TASK-XXX   # Reject a task
orchestrator> skills            # List available skills
orchestrator> status            # System status
orchestrator> help              # Show all commands
```

### Telegram Commands

- `/start` - Welcome message and help
- `/team` - Show team overview
- `/agents` - List all agents
- `/roles` - List available roles
- `/createagent` - Create a new agent (interactive)
- `/submit` - Submit a task (interactive)
- `/tasks [status]` - List tasks
- `/task <id>` - Task details
- `/approve <task_id>` - Approve pending task
- `/reject <task_id>` - Reject task
- `/skills` - List available skills
- `/status` - System status
- `/help` - Show help

## Default Roles

| Role | Hierarchy | Can Delegate To | Approval Required |
|---|---|---|---|
| CEO | 1 (Highest) | CTO, Senior, DevOps Lead | No |
| CTO | 2 | Senior, DevOps Lead, Security | No |
| Senior Engineer | 3 | Junior Engineer | No |
| DevOps Lead | 3 | DevOps Engineer | No |
| Security Engineer | 3 | — | No |
| Junior Engineer | 4 | — | **Yes** |
| DevOps Engineer | 4 | — | **Yes** |
| QA Engineer | 4 | — | No |

## Built-in Skills

- **Languages**: Python, JavaScript, TypeScript
- **Frameworks**: Django, React
- **DevOps**: Docker, CI/CD
- **Database**: PostgreSQL
- **Concepts**: System Design, Application Security

Add custom skills by dropping JSON files into `skills/custom/`.

## Safety

- ✅ Each task creates an isolated git branch
- ✅ Automated validation before commits (syntax, tests, linting)
- ✅ Hierarchical approval workflow
- ✅ Manual approval required before merge
- ✅ Automatic rollback on validation failure
- ✅ Daily budget limit for API costs
- ✅ Audit trail for all actions

## Documentation

- **[SETUP.md](SETUP.md)** - Full setup guide, configuration, troubleshooting
- **[AGENTS.md](AGENTS.md)** - Developer guide, architecture, contributing

## Project Types Supported

| Type | Validation |
|---|---|
| `generic` | Basic file checks |
| `python` | `py_compile`, `pytest` |
| `node` | ESLint, `npm test` |
| `laravel` | PHP syntax, Blade, `php artisan test` |

## License

MIT
