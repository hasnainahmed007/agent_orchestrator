"""Pre-built task templates for common development patterns.

Templates provide structured task descriptions that agents
can execute reliably. Users pick a template and provide parameters.
"""
from typing import Dict, Optional


TASK_TEMPLATES: Dict[str, Dict] = {
    "rest_api": {
        "name": "Create REST API",
        "description": "Build a complete REST API with CRUD endpoints",
        "category": "backend",
        "default_priority": "high",
        "template": """Create a REST API for {entity_name} with these endpoints:
- GET /{endpoint} — list all {entity_name_plural}
- GET /{endpoint}/{{id}} — get {entity_name} by ID
- POST /{endpoint} — create new {entity_name}
- PUT /{endpoint}/{{id}} — update {entity_name}
- DELETE /{endpoint}/{{id}} — delete {entity_name}

Requirements:
- Use {framework} framework
- Validate input with proper error handling
- Return appropriate HTTP status codes
- Include a test suite
{folder}
""",
        "params": {
            "entity_name": "User",
            "entity_name_plural": "Users",
            "endpoint": "users",
            "framework": "FastAPI",
            "folder": ""
        }
    },
    "auth_system": {
        "name": "Add Authentication",
        "description": "Add JWT-based authentication to an existing API",
        "category": "security",
        "default_priority": "high",
        "template": """Add JWT authentication to the existing project:

1. Create user registration endpoint: POST /auth/register
2. Create login endpoint: POST /auth/login (returns JWT token)
3. Add middleware to protect routes with JWT validation
4. Add role-based access control (admin, user)
5. Hash passwords with bcrypt
6. Add token refresh endpoint: POST /auth/refresh

Requirements:
- Use {framework} framework
- Store users in {storage}
- Return proper error messages for invalid credentials
- Include comprehensive authentication tests
""",
        "params": {
            "framework": "FastAPI",
            "storage": "SQLite database"
        }
    },
    "cli_tool": {
        "name": "Build CLI Tool",
        "description": "Build a command-line interface tool",
        "category": "tooling",
        "template": """Build a CLI tool called `{tool_name}.py` that {purpose}.

Features:
- Use argparse for argument parsing
- Support --input and --output flags
- Add --verbose mode for detailed logging
- Add --dry-run mode to preview changes
- Include --help with examples
- Exit codes: 0 for success, 1 for errors

Requirements:
- Written in Python {python_version}+
- Use standard library where possible
- Include docstrings and type hints
- Include pytest tests
""",
        "params": {
            "tool_name": "organize",
            "purpose": "organizes files by type into folders",
            "python_version": "3.10"
        }
    },
    "database_migration": {
        "name": "Database Migration",
        "description": "Create database migration and model updates",
        "category": "backend",
        "template": """Create database migration for {changes}:

Changes needed:
{migration_details}

Requirements:
- Use {orm} for migrations
- Include rollback/downgrade support
- Add data validation for new fields
- Update existing models/tests
- Handle null constraints properly
""",
        "params": {
            "changes": "adding a new `status` field to the users table",
            "migration_details": "- Add `status` column (VARCHAR, default 'active')\n- Add index on status column\n- Update User model\n- Update existing tests",
            "orm": "SQLAlchemy"
        }
    },
    "etl_pipeline": {
        "name": "ETL Data Pipeline",
        "description": "Build an Extract-Transform-Load pipeline",
        "category": "data",
        "default_priority": "critical",
        "template": """Build an ETL pipeline that:

Extract:
- Read {source_format} files from {source_path}
- Validate file format and encoding
- Log row counts per file

Transform:
- Clean and normalize data
- {transformations}
- Handle missing/empty values

Load:
- Write results to {target_storage}
- Use batch inserts for performance
- Log final record counts

Requirements:
- Use pandas for data processing
- Log every step with timestamps
- Handle edge cases (empty files, malformed data)
- Include pytest tests with sample data
""",
        "params": {
            "source_format": "CSV",
            "source_path": "./input/",
            "transformations": "Convert date strings to datetime, rename columns to snake_case, filter out invalid rows",
            "target_storage": "SQLite database at ./output/data.db"
        }
    },
    "unit_tests": {
        "name": "Write Unit Tests",
        "description": "Write comprehensive test suite for existing code",
        "category": "testing",
        "template": """Write comprehensive tests for {target_module}:

Test Coverage:
- Test all public functions and methods
- Test edge cases and error handling
- Test with valid and invalid inputs
- Test async functions if present
- Target {coverage_target}% coverage

Requirements:
- Use pytest framework
- Use fixtures for shared setup
- Mock external dependencies
- Use parametrize for multiple test cases
- Follow existing test patterns in the codebase
""",
        "params": {
            "target_module": "the users service module",
            "coverage_target": "90"
        }
    },
    "docker_setup": {
        "name": "Docker Setup",
        "description": "Create Dockerfile and docker-compose for the project",
        "category": "devops",
        "template": """Create Docker configuration:

1. Dockerfile:
   - Multi-stage build ({base_image})
   - Install dependencies efficiently
   - Run as non-root user
   - Expose port {port}
   - Health check endpoint

2. docker-compose.yml:
   - App service with Dockerfile
   - {services} services
   - Volume mounts for development
   - Environment variables from .env

3. .dockerignore:
   - Exclude node_modules, __pycache__, .git
   - Exclude local state and logs

Requirements:
- Use official base images
- Minimize layer count
- Add LABEL with metadata
""",
        "params": {
            "base_image": "python:3.12-slim",
            "port": "8000",
            "services": "PostgreSQL database"
        }
    }
}


def get_template(template_id: str) -> Optional[Dict]:
    """Get a task template by ID."""
    return TASK_TEMPLATES.get(template_id)


def list_templates(category: Optional[str] = None) -> list:
    """List available task templates, optionally filtered by category."""
    result = []
    for tid, tmpl in TASK_TEMPLATES.items():
        if category and tmpl.get('category') != category:
            continue
        result.append({
            'id': tid,
            'name': tmpl['name'],
            'description': tmpl['description'],
            'category': tmpl.get('category', 'general'),
        })
    return result


def build_task_from_template(template_id: str, **params) -> Optional[Dict]:
    """Build a task title/description from a template with params."""
    tmpl = get_template(template_id)
    if not tmpl:
        return None

    merged = {**tmpl.get('params', {}), **params}
    description = tmpl['template'].format(**merged)
    title = tmpl['name']
    if 'entity_name' in merged:
        title = f"{tmpl['name']}: {merged['entity_name']}"

    return {
        'title': title,
        'description': description,
        'priority': tmpl.get('default_priority', 'normal'),
        'category': tmpl.get('category', 'general'),
    }
