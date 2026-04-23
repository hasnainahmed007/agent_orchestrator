"""Orchestrator Agent - Manager/Coordinator for all agents."""
from typing import List, Dict, Any, Optional
from crewai import Agent
from langchain_openai import ChatOpenAI

from config.settings import Config
from config.prompts import ORCHESTRATOR_PROMPT


class OrchestratorAgent:
    """The main orchestrator agent that coordinates all other agents."""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(
            model=Config.OPENAI_MODEL,
            api_key=Config.OPENAI_API_KEY,
            temperature=Config.OPENAI_TEMPERATURE,
            max_tokens=Config.OPENAI_MAX_TOKENS
        )
        self.agent: Optional[Agent] = None
    
    def create(self) -> Agent:
        """Create and return the orchestrator agent."""
        self.agent = Agent(
            role='Orchestrator Agent',
            goal='Coordinate and manage specialized agents to complete Laravel development tasks efficiently and safely',
            backstory=ORCHESTRATOR_PROMPT,
            verbose=Config.AGENT_VERBOSE,
            allow_delegation=True,
            llm=self.llm,
            max_iter=Config.AGENT_MAX_ITERATIONS,
            memory=Config.AGENT_MEMORY,
            tools=[]
        )
        return self.agent
    
    def decompose_task(self, task_description: str, project_context: str = "") -> Dict[str, Any]:
        """Analyze task and break it down into subtasks.
        
        Args:
            task_description: High-level task description
            project_context: Project context summary
            
        Returns:
            Dictionary with task breakdown
        """
        description_lower = task_description.lower()
        
        needs_backend = any(kw in description_lower for kw in [
            'api', 'controller', 'model', 'migration', 'service', 
            'backend', 'php', 'validation', 'database', 'endpoint',
            'create', 'update', 'delete', 'crud', 'route'
        ])
        
        needs_frontend = any(kw in description_lower for kw in [
            'page', 'view', 'blade', 'form', 'ui', 'frontend',
            'html', 'css', 'javascript', 'component', 'design',
            'button', 'modal', 'table', 'list', 'dashboard'
        ])
        
        needs_testing = any(kw in description_lower for kw in [
            'test', 'testing', 'spec', 'phpunit', 'pest'
        ]) or needs_backend or needs_frontend
        
        agents_needed = []
        if needs_backend:
            agents_needed.append('backend')
        if needs_frontend:
            agents_needed.append('frontend')
        agents_needed.append('testing')
        
        return {
            'original_task': task_description,
            'needs_backend': needs_backend,
            'needs_frontend': needs_frontend,
            'needs_testing': needs_testing,
            'agents_needed': agents_needed,
            'execution_order': agents_needed,
            'estimated_complexity': self._estimate_complexity(
                needs_backend, needs_frontend, needs_testing
            )
        }
    
    def _estimate_complexity(self, backend: bool, frontend: bool, testing: bool) -> str:
        """Estimate task complexity."""
        score = sum([backend, frontend, testing])
        if score >= 3:
            return 'high'
        elif score >= 2:
            return 'medium'
        return 'low'
    
    def coordinate_agents(self, task_breakdown: Dict[str, Any]) -> List[Dict[str, str]]:
        """Create execution plan for agents.
        
        Args:
            task_breakdown: Output from decompose_task
            
        Returns:
            List of agent execution steps
        """
        steps = []
        agents = task_breakdown.get('agents_needed', [])
        
        for i, agent_name in enumerate(agents):
            step = {
                'order': i + 1,
                'agent': agent_name,
                'status': 'pending',
                'depends_on': agents[:i] if i > 0 else []
            }
            steps.append(step)
        
        return steps
