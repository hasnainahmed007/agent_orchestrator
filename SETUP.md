# Agent Orchestrator - Setup Guide

A multi-agent AI system for software development with hierarchical team management, skill-based task delegation, and remote control via Telegram.

## Table of Contents

- [Overview](#overview)
- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Configuration](#configuration)
- [Creating Your Team](#creating-your-team)
- [Submitting Tasks](#submitting-tasks)
- [Approval Workflow](#approval-workflow)
- [Telegram Bot Setup](#telegram-bot-setup)
- [Adding Custom Skills](#adding-custom-skills)
- [Creating Custom Roles](#creating-custom-roles)
- [Troubleshooting](#troubleshooting)

---

## Overview

Agent Orchestrator allows you to:

- **Create dynamic AI agent teams** with roles like CEO, CTO, Senior Engineer, Junior Engineer, DevOps, Security Engineer, QA
- **Assign pre-defined skills** to agents (Python, React, Docker, PostgreSQL, System Design, Security, etc.)
- **Submit tasks** that get auto-assigned to the best-suited agent based on skill matching
- **Delegate hierarchically** - senior agents can break tasks into subtasks for juniors
- **Review and approve** work before it gets committed to your codebase
- **Control remotely** via Telegram bot from your phone
- **Track everything** - tasks, costs, performance metrics, audit trails

---

## System Requirements

- **Python**: 3.10 or higher
- **Git**: Required for the target project directory
- **Operating System**: Linux, macOS, or Windows
- **OpenAI API Key**: Required for AI agent execution
- **Telegram Bot Token**: Optional (only if using Telegram mode)

---

## Quick Start

### 1. Clone and Install

```bash
git clone <repository-url>
cd agent_orchestrator
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and project settings
```

### 3. Prepare Your Project Directory

```bash
# Create or use an existing project directory
mkdir -p projects/my-project
cd projects/my-project
git init
git checkout -b main
cd ../..
```

### 4. Run the CLI

```bash
python main.py --mode cli
```

### 5. Create Your First Agent

```
orchestrator> create-agent
Agent name: Alice
Select role: 3  (Senior Software Engineer)
Add extra skills: none
```

### 6. Submit a Task

```
orchestrator> submit
Task title: Build User API
Task description: Create REST API endpoints for user CRUD operations
Priority: high
Assign to: 0  (auto-assign)
```

---

## Detailed Setup

### Step 1: Install Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate it
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

#### Required Settings

| Variable | Description | Example |
|---|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-...` |
| `PROJECT_PATH` | Path to your project (must be a git repo) | `/home/user/projects/my-app` |
| `PROJECT_NAME` | Name of your project | `my-app` |
| `PROJECT_TYPE` | Type of project | `generic`, `python`, `node`, `laravel` |
| `MAIN_BRANCH` | Main git branch name | `main` |

#### Optional Settings

| Variable | Description | Default |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | From @BotFather | (empty) |
| `TELEGRAM_ALLOWED_USERS` | Comma-separated user IDs | (empty) |
| `OPENAI_MODEL` | Model to use | `gpt-4o` |
| `REQUIRE_APPROVAL` | Require approval before merge | `true` |
| `DAILY_BUDGET_LIMIT` | Max daily API cost ($) | `5.0` |
| `ENABLE_AUTO_ASSIGN` | Auto-assign tasks to agents | `true` |
| `ENABLE_HIERARCHICAL_DELEGATION` | Allow senior agents to delegate | `true` |

### Step 3: Prepare Your Project

The target project **must be a git repository**:

```bash
# If starting fresh
mkdir my-project
cd my-project
git init
echo "# My Project" > README.md
git add README.md
git commit -m "Initial commit"
git branch -m main  # or master, depending on your preference
```

Update `PROJECT_PATH` in `.env` to point to this directory.

### Step 4: Run the System

**CLI Mode** (interactive terminal):
```bash
python main.py --mode cli
```

**Telegram Bot Mode**:
```bash
python main.py --mode telegram
```

**Show Status**:
```bash
python main.py --status
```

---

## Configuration

### Project Types

The `PROJECT_TYPE` setting affects validation:

| Type | Validation Behavior |
|---|---|
| `generic` | Basic file checks only |
| `python` | Python syntax check (`py_compile`), pytest |
| `node` | ESLint, `npm test` |
| `laravel` | PHP syntax, Blade checks, `php artisan test` |

### Agent Settings

| Setting | Description |
|---|---|
| `AGENT_VERBOSE` | Show detailed agent output |
| `AGENT_MAX_ITERATIONS` | Max agent thinking steps |
| `AGENT_MEMORY` | Enable agent memory |
| `MAX_FILES_PER_TASK` | Limit files an agent can touch |

### Safety Settings

| Setting | Description |
|---|---|
| `REQUIRE_APPROVAL` | Human approval before merging |
| `ENABLE_ROLLBACK` | Auto-rollback on validation failure |
| `AUTO_MERGE_ON_TESTS_PASS` | Auto-merge if tests pass |

---

## Creating Your Team

### Using the CLI

```
orchestrator> create-agent
Agent name: Alice
Select role:
  1. Chief Executive Officer (ceo)
  2. Chief Technology Officer (cto)
  3. Senior Software Engineer (senior_engineer)
  4. DevOps Lead (devops_lead)
  5. Security Engineer (security_engineer)
  6. Junior Software Engineer (junior_engineer)
  7. DevOps Engineer (devops_engineer)
  8. QA Engineer (qa_engineer)
Select role (number or role_id): 3
Add extra skills? (comma-separated, or empty): python,django
```

### Using Telegram

```
/createagent
Bot: What's the agent's name?
You: Alice
Bot: Choose a role:
     1. Chief Executive Officer (ceo)
     ...
You: 3
Bot: Selected role: Senior Software Engineer
     Add extra skills? (comma-separated skill IDs, or 'none'):
You: python,django
Bot: Agent created successfully!
     Name: Alice
     ID: agent-xxxxx
     Role: senior_engineer
```

### Available Skills

Built-in skills include:

- **Languages**: `python`, `javascript`, `typescript`
- **Frameworks**: `django`, `react`
- **DevOps**: `docker`, `devops`
- **Database**: `postgresql`
- **Concepts**: `system_design`, `security`

View all skills with:
```
orchestrator> skills
```

---

## Submitting Tasks

### CLI

```
orchestrator> submit
Task title: Build User API
Task description:
Create REST API endpoints for user CRUD operations with:
- GET /api/users (list)
- GET /api/users/{id} (show)
- POST /api/users (create)
- PUT /api/users/{id} (update)
- DELETE /api/users/{id} (delete)
Use proper validation and error handling.

Priority? (low/normal/high/critical): high

Available agents:
  1. Alice (Senior Software Engineer)
  2. Bob (Junior Software Engineer)
Assign to (number, agent ID, or 0 for auto): 0

Task submitted!
  ID: TASK-XXXXXX
  Status: pending
```

### Telegram

```
/submit
Bot: What's the task title?
You: Build User API
Bot: Task description:
You: Create REST API endpoints for user CRUD operations
Bot: Priority? (low/normal/high/critical)
You: high
Bot: Task submitted!
     ID: TASK-XXXXXX
     Title: Build User API
     Status: pending
```

---

## Approval Workflow

When a task is completed by an agent whose role requires approval (e.g., Junior Engineer):

1. Task status becomes `under_review`
2. Notification is sent (CLI or Telegram)
3. Reviewer approves or rejects:

```
# CLI
orchestrator> approve TASK-XXXXXX
Approval notes: Looks good, well tested
Task TASK-XXXXXX approved.

# Or reject
orchestrator> reject TASK-XXXXXX
Rejection reason: Missing input validation on email field
Task TASK-XXXXXX rejected.
```

```
# Telegram
/approve TASK-XXXXXX
# Or use inline button
```

---

## Telegram Bot Setup

### 1. Create a Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow instructions to name your bot
4. Copy the **API token** provided

### 2. Get Your User ID

1. Search for **@userinfobot** in Telegram
2. Start the bot
3. Note your **User ID**

### 3. Configure

Add to `.env`:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALLOWED_USERS=your_user_id
```

### 4. Run

```bash
python main.py --mode telegram
```

### 5. Use the Bot

Send `/start` to your bot on Telegram.

---

## Adding Custom Skills

You can add custom skills by creating JSON files in `skills/custom/`.

### Example Custom Skill

Create `skills/custom/graphql.json`:

```json
{
  "skill_id": "graphql",
  "name": "GraphQL API Development",
  "category": "framework",
  "description": "Building GraphQL APIs with Apollo and Node.js",
  "expertise_level": "expert",
  "best_practices": [
    "Design schema-first APIs",
    "Use DataLoader for N+1 problem",
    "Implement proper error handling",
    "Use fragments for reusable queries"
  ],
  "coding_standards": [
    "Use PascalCase for type names",
    "Use camelCase for field names",
    "Always define resolvers explicitly"
  ],
  "common_patterns": [
    "Schema stitching for microservices",
    "Subscription for real-time updates",
    "Federation for distributed graphs"
  ],
  "anti_patterns": [
    "Exposing database directly",
    "Deep nesting beyond 5 levels",
    "Missing pagination on lists"
  ],
  "tools": ["read_file", "write_file", "edit_file", "search_files", "run_command"],
  "file_patterns": {
    "schema": "schema.graphql",
    "resolver": "resolvers/{name}.js",
    "type": "types/{name}.js"
  },
  "system_context": "You are a GraphQL expert...",
  "validation_rules": ["Run graphql-schema-linter"]
}
```

The skill will be automatically loaded on next startup.

---

## Creating Custom Roles

You can create custom roles programmatically or by editing `state/agent_roles.json`.

### Example: Creating a Tech Lead Role

```python
from agents.roles import AgentRole, AgentRoleManager

role = AgentRole(
    role_id='tech_lead',
    name='Technical Lead',
    description='Lead developer who architects features and mentors the team',
    hierarchy_level=3,
    skills=['python', 'typescript', 'system_design'],
    responsibilities=[
        'Architect complex features',
        'Review all team code',
        'Mentor senior and junior engineers',
        'Set coding standards'
    ],
    can_delegate_to=['senior_engineer', 'junior_engineer'],
    reviewed_by=['cto'],
    approval_required=False,
    can_create_subtasks=True,
    can_modify_files=True
)

# Save it
role_manager = AgentRoleManager('./state')
role_manager.create_role(role)
```

---

## Troubleshooting

### "PROJECT_PATH is not a git repository"

Your project directory must be a git repository:
```bash
cd /your/project/path
git init
git checkout -b main
git add .
git commit -m "Initial commit"
```

### "OPENAI_API_KEY is required"

Add your OpenAI API key to `.env`:
```env
OPENAI_API_KEY=sk-your-key-here
```

### "Telegram bot token not configured"

Add your bot token to `.env` or use CLI mode instead:
```bash
python main.py --mode cli
```

### Agents not auto-assigning

Make sure:
1. You have created at least one agent
2. The agent's status is `idle`
3. `ENABLE_AUTO_ASSIGN=true` in `.env`

### Tasks failing immediately

Check logs:
```bash
tail -f logs/orchestrator.log
```

Common causes:
- OpenAI API key invalid or quota exceeded
- Project path doesn't exist
- Git repository not initialized

---

## Directory Structure

```
agent_orchestrator/
├── agents/              # Agent definitions and management
│   ├── __init__.py
│   ├── roles.py         # Role & instance management
│   ├── delegation.py    # Task delegation engine
│   ├── tools.py         # Agent file operation tools
│   ├── backend.py       # Legacy backend agent
│   ├── frontend.py      # Legacy frontend agent
│   ├── testing.py       # Legacy testing agent
│   └── orchestrator.py  # Legacy orchestrator agent
├── cli/                 # Command-line interface
│   ├── __init__.py
│   └── interface.py
├── config/              # Configuration
│   ├── settings.py
│   └── prompts.py
├── core/                # Core functionality
│   ├── git_manager.py
│   ├── state_manager.py
│   ├── validator.py
│   ├── project_context.py
│   ├── cost_tracker.py
│   ├── rate_limiter.py
│   ├── performance_tracker.py
│   ├── audit_logger.py
│   └── project_manager.py
├── remote/              # Telegram bot
│   └── telegram_bot.py
├── skills/              # Skill modules
│   ├── __init__.py
│   └── registry.py
├── api/                 # REST API server
│   └── server.py
├── tasks/               # Legacy task definitions
│   └── definitions.py
├── projects/            # Target projects (created by user)
│   └── default/
├── logs/                # Log files
├── state/               # Persistent state
│   ├── agent_roles.json
│   ├── agent_instances.json
│   ├── delegated_tasks.json
│   └── ...
├── main.py              # Entry point
├── orchestrator.py      # Main orchestrator class
├── requirements.txt     # Dependencies
├── .env                 # Configuration (user-created)
├── .env.example         # Configuration template
├── SETUP.md             # This file
└── README.md            # Project overview
```

---

## Next Steps

1. **Explore CLI commands**: Type `help` in the CLI
2. **Set up Telegram**: For mobile remote control
3. **Add custom skills**: For technologies not built-in
4. **Create custom roles**: For your specific team structure
5. **Build a web dashboard**: When you're ready for a UI (the API layer is ready)

For developer conventions and contribution guidelines, see `AGENTS.md`.
