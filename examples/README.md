# Examples

Real-world use cases for Agent Orchestrator.

| Example | Description | Project Type |
|---|---|---|
| [FastAPI CRUD](fastapi-crud/) | Build a complete FastAPI REST API with CRUD endpoints, Pydantic models, and tests | `python` |
| [CLI Tool](cli-tool/) | Build a command-line file organizer with argparse, dry-run mode | `python` |
| [Data Pipeline](data-pipeline/) | Build an ETL pipeline from CSV to SQLite with pandas | `python` |

## How to Use

1. Set `PROJECT_PATH` in `.env` to the example directory
2. Set `PROJECT_TYPE` to `python`
3. Run `python main.py --mode cli`
4. Create agents and submit tasks as described in each example's README

## Adding Your Own Examples

Contribute examples via PR! Create a new directory under `examples/` with:
- `README.md` explaining the use case
- Task descriptions that produce meaningful output
- Any starter files the agent should work with
