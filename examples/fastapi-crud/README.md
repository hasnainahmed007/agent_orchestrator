# Example: Build a FastAPI CRUD API

This example shows how Agent Orchestrator builds a complete FastAPI CRUD application.

## Setup

```bash
# 1. Set project type to python
echo "PROJECT_TYPE=python" >> ../../.env

# 2. Start CLI
cd ../..
python main.py --mode cli

# 3. Create agents
orchestrator> create-agent
Agent name: Alice
Role: 3 (Senior Software Engineer)
Skills: python,fastapi

orchestrator> create-agent
Agent name: Bob
Role: 6 (Junior Software Engineer)
Skills: python

# 4. Submit task
orchestrator> submit
Task title: Build FastAPI User CRUD
Task description:
Build a complete User CRUD API using FastAPI with:
- GET /users (list all users)
- GET /users/{id} (get user by id)
- POST /users (create user with name, email fields)
- PUT /users/{id} (update user)
- DELETE /users/{id} (delete user)
Use Pydantic models for validation, include proper error handling.
Priority: high
Assign to: 1 (Alice)

# 5. Process the task
orchestrator> process TASK-XXXXXXXX
```

## Expected Output

The agent will create:
- `main.py` - FastAPI application with CRUD endpoints
- `models.py` - Pydantic models
- `requirements.txt` - FastAPI + uvicorn dependencies
- `test_main.py` - Pytest test suite

## Run the result

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
