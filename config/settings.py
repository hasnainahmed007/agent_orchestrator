"""Configuration management for Agent Orchestrator."""
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class Config:
    """Application configuration."""

    # Paths
    BASE_DIR = Path(__file__).parent.parent

    # Project settings (generic - not tied to Laravel)
    PROJECT_PATH = Path(os.getenv('PROJECT_PATH', str(BASE_DIR / 'projects' / 'default')))
    PROJECT_NAME = os.getenv('PROJECT_NAME', 'default-project')
    PROJECT_TYPE = os.getenv('PROJECT_TYPE', 'generic')
    MAIN_BRANCH = os.getenv('MAIN_BRANCH', 'main')

    # OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')
    OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '4000'))
    OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.1'))

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_ALLOWED_USERS = [
        uid.strip()
        for uid in os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',')
        if uid.strip()
    ]

    # Agent settings
    AGENT_VERBOSE = os.getenv('AGENT_VERBOSE', 'true').lower() == 'true'
    AGENT_MAX_ITERATIONS = int(os.getenv('AGENT_MAX_ITERATIONS', '15'))
    AGENT_MEMORY = os.getenv('AGENT_MEMORY', 'true').lower() == 'true'

    # Multi-agent team settings
    DEFAULT_TEAM_CONFIG = os.getenv('DEFAULT_TEAM_CONFIG', 'default')
    ENABLE_AUTO_ASSIGN = os.getenv('ENABLE_AUTO_ASSIGN', 'true').lower() == 'true'
    ENABLE_HIERARCHICAL_DELEGATION = os.getenv('ENABLE_HIERARCHICAL_DELEGATION', 'true').lower() == 'true'

    # Safety
    REQUIRE_APPROVAL = os.getenv('REQUIRE_APPROVAL', 'true').lower() == 'true'
    AUTO_MERGE_ON_TESTS_PASS = os.getenv('AUTO_MERGE_ON_TESTS_PASS', 'false').lower() == 'true'
    MAX_FILES_PER_TASK = int(os.getenv('MAX_FILES_PER_TASK', '20'))
    ENABLE_ROLLBACK = os.getenv('ENABLE_ROLLBACK', 'true').lower() == 'true'

    # Cost Control
    DAILY_BUDGET_LIMIT = float(os.getenv('DAILY_BUDGET_LIMIT', '5.0'))
    MAX_TOKENS_PER_REQUEST = int(os.getenv('MAX_TOKENS_PER_REQUEST', '4000'))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = BASE_DIR / os.getenv('LOG_FILE', 'logs/orchestrator.log')

    # State
    STATE_FILE = BASE_DIR / os.getenv('STATE_FILE', 'state/orchestrator_state.json')
    TASKS_FILE = BASE_DIR / os.getenv('TASKS_FILE', 'state/tasks.json')

    # Skills
    CUSTOM_SKILLS_DIR = BASE_DIR / os.getenv('CUSTOM_SKILLS_DIR', 'skills/custom')

    @classmethod
    def validate(cls):
        """Validate required configuration. Returns (errors, warnings)."""
        errors = []
        warnings = []

        if not cls.OPENAI_API_KEY or cls.OPENAI_API_KEY == 'your_openai_api_key_here':
            errors.append("OPENAI_API_KEY is required. Set it in .env file.")

        if not cls.TELEGRAM_BOT_TOKEN or cls.TELEGRAM_BOT_TOKEN == 'your_telegram_bot_token_here':
            warnings.append("TELEGRAM_BOT_TOKEN not set. Telegram bot mode will be unavailable.")

        # Make project path if it doesn't exist
        cls.PROJECT_PATH.mkdir(parents=True, exist_ok=True)

        # Auto-initialize git repo if missing
        git_dir = cls.PROJECT_PATH / '.git'
        if not git_dir.exists():
            try:
                subprocess.run(
                    ['git', 'init', '--initial-branch=' + cls.MAIN_BRANCH],
                    cwd=str(cls.PROJECT_PATH),
                    capture_output=True,
                    timeout=10
                )
                # Create initial commit so branches work
                readme = cls.PROJECT_PATH / 'README.md'
                if not readme.exists():
                    readme.write_text(f'# {cls.PROJECT_NAME}\n')
                subprocess.run(
                    ['git', 'add', '-A'],
                    cwd=str(cls.PROJECT_PATH),
                    capture_output=True,
                    timeout=10
                )
                subprocess.run(
                    ['git', 'commit', '-m', 'Initial commit (auto-initialized by Agent Orchestrator)'],
                    cwd=str(cls.PROJECT_PATH),
                    capture_output=True,
                    timeout=10
                )
                warnings.append(f"Auto-initialized git repository at {cls.PROJECT_PATH}")
            except Exception as e:
                errors.append(f"Failed to initialize git repository at {cls.PROJECT_PATH}: {e}")

        return errors, warnings

    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist."""
        for dir_path in [
            cls.BASE_DIR / 'logs',
            cls.BASE_DIR / 'state',
            cls.BASE_DIR / 'skills' / 'custom',
            cls.PROJECT_PATH
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_project_validation_config(cls) -> dict:
        """Get validation configuration based on project type."""
        configs = {
            'laravel': {
                'php_enabled': True,
                'blade_enabled': True,
                'artisan_enabled': True,
                'test_command': 'php artisan test',
            },
            'python': {
                'php_enabled': False,
                'blade_enabled': False,
                'artisan_enabled': False,
                'test_command': 'pytest',
                'lint_command': 'python -m py_compile',
            },
            'node': {
                'php_enabled': False,
                'blade_enabled': False,
                'artisan_enabled': False,
                'test_command': 'npm test',
                'lint_command': 'npm run lint',
            },
            'generic': {
                'php_enabled': False,
                'blade_enabled': False,
                'artisan_enabled': False,
                'test_command': '',
                'lint_command': '',
            }
        }
        return configs.get(cls.PROJECT_TYPE, configs['generic'])
