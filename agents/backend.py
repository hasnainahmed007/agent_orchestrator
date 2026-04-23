"""Backend Agent - Laravel Backend Specialist."""
from typing import Optional
from crewai import Agent
from langchain_openai import ChatOpenAI

from config.settings import Config
from config.prompts import BACKEND_PROMPT


class BackendAgent:
    """Specialized agent for Laravel backend development."""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(
            model=Config.OPENAI_MODEL,
            api_key=Config.OPENAI_API_KEY,
            temperature=Config.OPENAI_TEMPERATURE,
            max_tokens=Config.OPENAI_MAX_TOKENS
        )
        self.agent: Optional[Agent] = None
    
    def create(self) -> Agent:
        """Create and return the backend agent."""
        self.agent = Agent(
            role='Laravel Backend Developer',
            goal='Create high-quality, secure, and efficient Laravel backend code following PSR-12 standards and best practices',
            backstory=BACKEND_PROMPT,
            verbose=Config.AGENT_VERBOSE,
            allow_delegation=False,
            llm=self.llm,
            max_iter=Config.AGENT_MAX_ITERATIONS,
            memory=Config.AGENT_MEMORY,
            tools=[]
        )
        return self.agent
    
    def get_capabilities(self) -> list:
        """Return list of backend capabilities."""
        return [
            'Create/update controllers',
            'Implement service classes',
            'Write model methods and relationships',
            'Create database migrations',
            'Add validation rules',
            'Implement API endpoints',
            'Create middleware',
            'Write Form Request classes',
            'Create API Resources',
            'Implement authentication/authorization',
            'Handle file uploads',
            'Create job classes and queues',
            'Implement events and listeners',
            'Write console commands'
        ]
    
    def get_file_patterns(self) -> dict:
        """Return standard Laravel file patterns."""
        return {
            'controller': 'app/Http/Controllers/{Name}Controller.php',
            'service': 'app/Services/{Name}Service.php',
            'model': 'app/Models/{Name}.php',
            'migration': 'database/migrations/YYYY_MM_DD_HHMMSS_create_{name}_table.php',
            'request': 'app/Http/Requests/{Name}Request.php',
            'resource': 'app/Http/Resources/{Name}Resource.php',
            'middleware': 'app/Http/Middleware/{Name}Middleware.php',
            'job': 'app/Jobs/{Name}Job.php',
            'event': 'app/Events/{Name}Event.php',
            'listener': 'app/Listeners/{Name}Listener.php',
            'command': 'app/Console/Commands/{Name}Command.php'
        }
