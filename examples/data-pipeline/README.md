# Example: Build a Data Pipeline

This example shows Agent Orchestrator building an ETL data pipeline.

## Setup

```bash
cd ..
python main.py --mode cli

orchestrator> submit
Task title: Build ETL pipeline for CSV processing
Task description:
Build a Python ETL pipeline that:
1. Reads CSV files from a source directory
2. Cleans and validates the data
3. Transforms columns (rename, convert types)
4. Loads results into a SQLite database
5. Logs all operations with timestamps
Use pandas for data processing and sqlite3 for storage.
Priority: critical
Assign to: 0

orchestrator> process TASK-XXXXXXXX
```

## Expected Output

- `pipeline.py` - Main ETL orchestration
- `extract.py` - CSV readers
- `transform.py` - Data cleaning
- `load.py` - SQLite writer
- `requirements.txt` - pandas
- `test_pipeline.py` - Tests

## Run

```bash
pip install -r requirements.txt
python pipeline.py --source ./input --db ./output/data.db
```
