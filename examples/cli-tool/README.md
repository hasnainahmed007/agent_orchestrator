# Example: Build a CLI Tool

This example shows Agent Orchestrator building a command-line tool.

## Setup

```bash
cd ..
python main.py --mode cli

orchestrator> submit
Task title: Build file organizer CLI
Task description:
Create a Python CLI tool `organize.py` that:
1. Scans a directory and organizes files by extension
2. Supports --source and --target flags
3. Has --dry-run mode to preview changes
4. Uses argparse for argument parsing
5. Includes a --help command
Priority: high
Assign to: 0 (auto-assign)

orchestrator> process TASK-XXXXXXXX
```

## Expected Output

- `organize.py` - CLI tool with argparse
- `requirements.txt` - (minimal, stdlib only)
- `test_organize.py` - Tests

## Run

```bash
python organize.py --source ~/Downloads --target ~/Organized --dry-run
python organize.py --source ~/Downloads --target ~/Organized
```
