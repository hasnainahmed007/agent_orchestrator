# Contributing to Agent Orchestrator

Thanks for your interest in contributing!

## Code of Conduct

Be respectful. Be constructive. Focus on the code.

## How to Contribute

### Reporting Bugs

Use the [Bug Report template](https://github.com/agentorchestrator/agent-orchestrator/issues/new?template=bug_report.yml).

Include: version, mode (CLI/Telegram/API), steps to reproduce, logs.

### Feature Requests

Use the [Feature Request template](https://github.com/agentorchestrator/agent-orchestrator/issues/new?template=feature_request.yml).

### Pull Requests

1. **Fork** the repo
2. **Create a branch**: `feat/my-feature` or `fix/my-bug`
3. **Write tests** for your changes
4. **Run tests**: `pytest tests/ -v`
5. **Run linter**: `ruff check .`
6. **Submit PR** with clear description

## Development Setup

```bash
git clone <your-fork>
cd agent_orchestrator
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with test-only API key
```

## Code Style

- Python 3.10+ with type hints
- Black formatter (line length 88)
- Ruff linter
- Docstrings for public APIs
- F-strings for string formatting

## Project Structure

```
agents/          # Agent creation, roles, delegation
cli/             # Interactive CLI
config/          # Settings, prompts
core/            # Git, validation, state, cost tracking
remote/          # Telegram bot
skills/          # Pre-defined skill modules
api/             # FastAPI REST server
tests/           # Pytest test suite
```

## Adding Features

### New Skill

Create JSON file in `skills/custom/`:

```json
{
  "skill_id": "my_skill",
  "name": "My Skill",
  "category": "language",
  "description": "...",
  "expertise_level": "intermediate",
  "best_practices": ["..."],
  "tools": ["read_file", "write_file"]
}
```

### New Role

```python
from agents.roles import AgentRole

role = AgentRole(
    role_id='my_role',
    name='My Role',
    description='...',
    hierarchy_level=3,
    skills=['python'],
    can_delegate_to=['junior_engineer'],
    reviewed_by=['cto']
)
role_manager.create_role(role)
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_skills.py -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

## Architecture Decisions

### Why CrewAI?
CrewAI provides agent orchestration with tool integration and memory. It's the most mature Python agent framework.

### Why JSON state files?
For MVP portability. SQLite migration is planned.

### Why Git isolation per task?
Safety — each agent gets a branch. No merge without approval. Rollback is a branch delete.

## License

By contributing, you agree your code will be licensed under the MIT License.
