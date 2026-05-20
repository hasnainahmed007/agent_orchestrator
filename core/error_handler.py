"""Better error messages with user-friendly categorization.

Wraps common errors in readable messages with suggested fixes.
"""
import logging
from enum import Enum
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories for user-facing errors."""
    CONFIG = "configuration"
    API = "api_key_or_network"
    GIT = "git_repository"
    VALIDATION = "code_validation"
    AGENT = "agent_execution"
    DATABASE = "database"
    PLUGIN = "plugin"
    UNKNOWN = "unknown"


ERROR_CATALOG: Dict[str, Dict[str, str]] = {
    # CrewAI / OpenAI errors
    "Incorrect API key": {
        "category": ErrorCategory.API.value,
        "message": "API key rejected.",
        "fix": "Check OPENAI_API_KEY in .env. Verify the key is valid at your provider's dashboard.",
    },
    "401": {
        "category": ErrorCategory.API.value,
        "message": "Authentication failed (401).",
        "fix": "Verify your API key or token. If using a custom endpoint, check OPENAI_BASE_URL.",
    },
    "429": {
        "category": ErrorCategory.API.value,
        "message": "Rate limit exceeded.",
        "fix": "Wait a moment, reduce concurrent tasks, or check your provider quota.",
    },
    "timeout": {
        "category": ErrorCategory.API.value,
        "message": "API request timed out.",
        "fix": "Check your network connection or increase timeout in Config.",
    },
    "not a git repository": {
        "category": ErrorCategory.GIT.value,
        "message": "Project directory is not a git repository.",
        "fix": "Run `git init` in PROJECT_PATH or let the orchestrator auto-init it.",
    },
    "InvalidGitRepositoryError": {
        "category": ErrorCategory.GIT.value,
        "message": "Project directory is not a valid git repository.",
        "fix": "Ensure PROJECT_PATH has a .git directory. The orchestrator will auto-init if missing.",
    },
    "GitCommandError": {
        "category": ErrorCategory.GIT.value,
        "message": "Git operation failed.",
        "fix": "Check if the branch exists, no merge conflicts, and you have write permissions.",
    },
    "Validation failed": {
        "category": ErrorCategory.VALIDATION.value,
        "message": "Code validation failed.",
        "fix": "Check the validation errors. Fix syntax issues or test failures, then re-process.",
    },
    "SyntaxError": {
        "category": ErrorCategory.VALIDATION.value,
        "message": "Syntax error in generated code.",
        "fix": "Review the generated file for syntax errors. Submit a more detailed task description.",
    },
    "ImportError": {
        "category": ErrorCategory.AGENT.value,
        "message": "Missing Python dependency.",
        "fix": "Install the missing package: `pip install <package-name>`.",
    },
    "ModuleNotFoundError": {
        "category": ErrorCategory.AGENT.value,
        "message": "Missing Python module.",
        "fix": "Install required dependencies or check the import path.",
    },
    "memory": {
        "category": ErrorCategory.AGENT.value,
        "message": "Agent memory error.",
        "fix": "Disable memory: set AGENT_MEMORY=false in .env if your provider lacks embeddings.",
    },
    "psycopg2": {
        "category": ErrorCategory.DATABASE.value,
        "message": "PostgreSQL driver not installed.",
        "fix": "Install psycopg2: `pip install psycopg2-binary`.",
    },
    "Configuration validation failed": {
        "category": ErrorCategory.CONFIG.value,
        "message": "Configuration is incomplete or invalid.",
        "fix": "Check .env file. Required: OPENAI_API_KEY. See SETUP.md for full config guide.",
    },
}


def categorize_error(error: Exception) -> Dict[str, str]:
    """Categorize an error and return a user-friendly message.

    Args:
        error: The exception object

    Returns:
        Dict with 'category', 'message', 'fix', 'original' keys
    """
    error_str = str(error)
    error_type = type(error).__name__

    # Search through error catalog for matching patterns
    for pattern, info in ERROR_CATALOG.items():
        if pattern.lower() in error_str.lower() or pattern.lower() in error_type.lower():
            return {
                'category': info['category'],
                'message': info['message'],
                'fix': info['fix'],
                'original': error_str[:500],
            }

    return {
        'category': ErrorCategory.UNKNOWN.value,
        'message': f"Unexpected error: {error_type}",
        'fix': "Check logs for details. Report this issue if it persists.",
        'original': error_str[:500],
    }


def format_error_for_display(error: Exception) -> str:
    """Format an error for CLI/Telegram display.

    Args:
        error: The exception

    Returns:
        Formatted error string
    """
    info = categorize_error(error)
    lines = [
        f"Error: {info['message']}",
        f"Category: {info['category']}",
    ]
    if info['fix']:
        lines.append(f"Fix: {info['fix']}")
    return "\n".join(lines)


def format_error_for_telegram(error: Exception) -> str:
    """Format an error for Telegram message (Markdown)."""
    info = categorize_error(error)
    lines = [
        f"*Error:* {info['message']}",
        f"_Category: {info['category']}_",
    ]
    if info['fix']:
        lines.append(f"*Fix:* {info['fix']}")
    return "\n".join(lines)
