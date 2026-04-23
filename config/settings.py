"""Configuration management for Agent Orchestrator."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

class Config:
    """Application configuration."""
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    PROJECT_PATH = Path(os.getenv('PROJECT_PATH', r'C:\xampp\htdocs\Office\glamdemy_admin_panel'))
    
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
    
    # Project
    PROJECT_NAME = os.getenv('PROJECT_NAME', 'glamdemy_admin_panel')
    PROJECT_TYPE = os.getenv('PROJECT_TYPE', 'laravel')
    MAIN_BRANCH = os.getenv('MAIN_BRANCH', 'main')
    
    # Agent
    AGENT_VERBOSE = os.getenv('AGENT_VERBOSE', 'true').lower() == 'true'
    AGENT_MAX_ITERATIONS = int(os.getenv('AGENT_MAX_ITERATIONS', '15'))
    AGENT_MEMORY = os.getenv('AGENT_MEMORY', 'true').lower() == 'true'
    
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
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        errors = []
        
        if not cls.OPENAI_API_KEY or cls.OPENAI_API_KEY == 'your_openai_api_key_here':
            errors.append("OPENAI_API_KEY is required. Set it in .env file.")
        
        if not cls.TELEGRAM_BOT_TOKEN or cls.TELEGRAM_BOT_TOKEN == 'your_telegram_bot_token_here':
            errors.append("TELEGRAM_BOT_TOKEN is required. Set it in .env file.")
        
        if not cls.TELEGRAM_ALLOWED_USERS:
            errors.append("TELEGRAM_ALLOWED_USERS is required for security.")
        
        if not cls.PROJECT_PATH.exists():
            errors.append(f"PROJECT_PATH does not exist: {cls.PROJECT_PATH}")
        
        return errors
    
    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist."""
        for dir_path in [cls.BASE_DIR / 'logs', cls.BASE_DIR / 'state']:
            dir_path.mkdir(exist_ok=True)