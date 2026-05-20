# Agent Orchestrator

A **multi-agent AI system** that manages software development teams with hierarchical roles, skill-based task delegation, and remote control.

[![Tests](https://github.com/agentorchestrator/agent-orchestrator/actions/workflows/tests.yml/badge.svg)](https://github.com/agentorchestrator/agent-orchestrator/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://hub.docker.com)

## Features

- **Multi-Agent Teams** — CEO, CTO, Senior Engineers, Juniors, DevOps, QA with hierarchy
- **Skill-Based Auto-Assignment** — Tasks auto-routed to best agent via keyword matching
- **Hierarchical Delegation** — Senior agents break complex tasks into subtasks for juniors
- **Approval Workflow** — Junior work requires senior review before merge
- **Telegram Bot** — Manage your entire team from mobile
- **Safe Git Workflow** — Isolated branch per task, validation gates, auto-rollback on failure
- **Dynamic Project Scanning** — Auto-detects Python, Node, Laravel, Generic project types
- **Task Validation** — Python syntax check + pytest, JS npm lint + test, PHP syntax + Blade
- **Multi-LLM Support** — OpenAI, Anthropic Claude, Google Gemini, Ollama, DeepSeek, Groq
- **PostgreSQL + SQLite** — Persistent state with full database backend option
- **Cost Tracking** — Per-task and daily budget limits for API usage
- **Performance Metrics** — Agent success rates, execution times, token usage
- **Custom Skills** — Drop JSON files into `skills/custom/`
- **Agent Marketplace** — Share and install community skills
- **Plugin System** — Extend with custom LLMs, validators, scanners, tools, notifiers
- **Docker** — One-command deployment with `docker-compose up`

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env: add OPENAI_API_KEY, set PROJECT_PATH

# 3. Run CLI
python main.py --mode cli

# 4. Create an agent
orchestrator> create-agent
Agent name: Alice
Role: 3  (Senior Software Engineer)

# 5. Submit a task
orchestrator> submit
Task title: Build User API
Task description: Create REST API endpoints for user CRUD
Priority: high
Assign to: 1

# 6. Process it
orchestrator> process TASK-XXXXXXXX
```

## LLM Providers

| Provider | Config |
|---|---|
| OpenAI | `OPENAI_API_KEY=sk-...` |
| Anthropic | `LLM_PROVIDER=anthropic`, `LLM_API_KEY=...` |
| Google Gemini | `LLM_PROVIDER=google`, `LLM_API_KEY=...` |
| Ollama (local) | `LLM_PROVIDER=ollama` (defaults to `localhost:11434`) |
| DeepSeek | `LLM_PROVIDER=deepseek`, `OPENAI_BASE_URL=https://api.deepseek.com/v1` |
| Groq | `LLM_PROVIDER=groq`, `OPENAI_BASE_URL=https://api.groq.com/openai/v1` |
| Custom endpoint | `OPENAI_BASE_URL=https://your-endpoint/v1` |

## Deployment

### Docker

```bash
docker-compose up
```

### PostgreSQL Backend

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/orchestrator
```

## Directory Structure

```
agent_orchestrator/
├── agents/          # Agent creation, roles, delegation, tools
├── cli/             # Interactive terminal
├── config/          # Settings, prompts
├── core/            # Git, validation, state, database, LLM providers, plugins
├── remote/          # Telegram bot
├── skills/          # Built-in + custom + marketplace skills
├── api/             # FastAPI REST server
├── examples/        # Sample projects (FastAPI CRUD, CLI tool, ETL pipeline)
├── tests/           # Test suite
├── .github/         # CI/CD, issue templates
├── Dockerfile
├── docker-compose.yml
├── CONTRIBUTING.md
└── SETUP.md
```

## Documentation

- **[SETUP.md](SETUP.md)** — Full setup guide, configuration, troubleshooting
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — How to contribute
- **[examples/](examples/)** — Sample projects and use cases

## License

MIT — see [LICENSE](LICENSE)
