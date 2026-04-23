"""Frontend Agent - Blade/Tailwind CSS Specialist."""
from typing import Optional
from crewai import Agent
from langchain_openai import ChatOpenAI

from config.settings import Config
from config.prompts import FRONTEND_PROMPT


class FrontendAgent:
    """Specialized agent for Laravel Blade templates and Tailwind CSS."""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(
            model=Config.OPENAI_MODEL,
            api_key=Config.OPENAI_API_KEY,
            temperature=Config.OPENAI_TEMPERATURE,
            max_tokens=Config.OPENAI_MAX_TOKENS
        )
        self.agent: Optional[Agent] = None
    
    def create(self) -> Agent:
        """Create and return the frontend agent."""
        self.agent = Agent(
            role='Laravel Frontend Developer',
            goal='Create beautiful, responsive, and accessible Laravel Blade views with Tailwind CSS following modern UI/UX best practices',
            backstory=FRONTEND_PROMPT,
            verbose=Config.AGENT_VERBOSE,
            allow_delegation=False,
            llm=self.llm,
            max_iter=Config.AGENT_MAX_ITERATIONS,
            memory=Config.AGENT_MEMORY,
            tools=[]
        )
        return self.agent
    
    def get_capabilities(self) -> list:
        """Return list of frontend capabilities."""
        return [
            'Create Blade view templates',
            'Add Tailwind CSS styling',
            'Write JavaScript for interactivity',
            'Create forms with validation error display',
            'Design responsive layouts',
            'Reuse existing UI components',
            'Create Blade components',
            'Implement Alpine.js interactivity',
            'Create layouts and master pages',
            'Add pagination UI',
            'Create data tables',
            'Implement modals and dropdowns',
            'Add notifications and alerts',
            'Create navigation menus'
        ]
    
    def get_file_patterns(self) -> dict:
        """Return standard frontend file patterns."""
        return {
            'view': 'resources/views/{path}/{name}.blade.php',
            'component': 'resources/views/components/{name}.blade.php',
            'layout': 'resources/views/layouts/{name}.blade.php',
            'partial': 'resources/views/partials/{name}.blade.php',
            'javascript': 'resources/js/{name}.js',
            'css': 'resources/css/{name}.css'
        }
    
    def get_tailwind_utilities(self) -> dict:
        """Return common Tailwind CSS utility patterns."""
        return {
            'layout': {
                'container': 'container mx-auto px-4',
                'flex_center': 'flex items-center justify-center',
                'grid': 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6',
                'flex_between': 'flex items-center justify-between'
            },
            'spacing': {
                'section': 'py-12',
                'card': 'p-6',
                'gap': 'gap-4'
            },
            'colors': {
                'primary': 'bg-blue-600 hover:bg-blue-700 text-white',
                'success': 'bg-green-600 hover:bg-green-700 text-white',
                'danger': 'bg-red-600 hover:bg-red-700 text-white',
                'warning': 'bg-yellow-600 hover:bg-yellow-700 text-white'
            },
            'forms': {
                'input': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'label': 'block text-sm font-medium text-gray-700 mb-1',
                'button': 'px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors',
                'error': 'text-red-500 text-sm mt-1'
            }
        }
