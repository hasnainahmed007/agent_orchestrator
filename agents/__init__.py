"""Agent definitions using CrewAI."""
from typing import List, Dict, Any, Optional
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from pathlib import Path

from config.settings import Config
from config.prompts import PromptComposer
from core.project_context import ProjectContextScanner
from agents.tools import AgentTools
from agents.orchestrator import OrchestratorAgent
from agents.backend import BackendAgent
from agents.frontend import FrontendAgent
from agents.testing import TestingAgent
from skills.registry import SkillRegistry


class AgentManager:
    """Manages creation and execution of dynamic specialized agents."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.tools = AgentTools(project_path)
        self.crewai_tools = self.tools.get_crewai_tools()
        self.tool_map = {t.name: t for t in self.crewai_tools}

        self.llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            api_key=Config.OPENAI_API_KEY,
            temperature=Config.OPENAI_TEMPERATURE,
            max_tokens=Config.OPENAI_MAX_TOKENS
        )
        self.context_scanner = ProjectContextScanner(project_path)
        self.project_context = None

        # Legacy specialized agent classes (kept for compatibility)
        self.orchestrator_agent = OrchestratorAgent(self.llm)
        self.backend_agent_class = BackendAgent(self.llm)
        self.frontend_agent_class = FrontendAgent(self.llm)
        self.testing_agent_class = TestingAgent(self.llm)

    def scan_project(self):
        """Scan project for context."""
        self.project_context = self.context_scanner.scan()

    def create_dynamic_agent(self, name: str, role: str, goal: str,
                            backstory: str, tools: List[str] = None) -> Agent:
        """Create a dynamic CrewAI agent from role definition.

        Args:
            name: Agent name
            role: Role title
            goal: Agent goal
            backstory: System prompt/backstory
            tools: List of allowed tool names

        Returns:
            CrewAI Agent instance
        """
        crewai_tool_objects = []
        if tools:
            for tool_name in tools:
                if tool_name in self.tool_map:
                    crewai_tool_objects.append(self.tool_map[tool_name])

        return Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            verbose=Config.AGENT_VERBOSE,
            allow_delegation=False,
            llm=Config.OPENAI_MODEL,
            max_iter=Config.AGENT_MAX_ITERATIONS,
            memory=Config.AGENT_MEMORY,
            tools=crewai_tool_objects if crewai_tool_objects else None,
        )

    def create_orchestrator(self) -> Agent:
        """Create the orchestrator agent (legacy)."""
        return self.orchestrator_agent.create()

    def create_backend_agent(self) -> Agent:
        """Create the backend agent (legacy)."""
        return self.backend_agent_class.create()

    def create_frontend_agent(self) -> Agent:
        """Create the frontend agent (legacy)."""
        return self.frontend_agent_class.create()

    def create_testing_agent(self) -> Agent:
        """Create the testing agent (legacy)."""
        return self.testing_agent_class.create()

    def analyze_task(self, task_description: str) -> Dict[str, Any]:
        """Analyze task and determine required agents (legacy).

        Returns:
            Dict with task breakdown
        """
        if not self.project_context:
            self.scan_project()

        task_breakdown = self.orchestrator_agent.decompose_task(
            task_description,
            self.project_context.to_summary() if self.project_context else ""
        )

        return {
            **task_breakdown,
            'context': self.project_context.to_summary() if self.project_context else ""
        }

    def execute_agent_task(self, agent: Agent, task_description: str, context: str = "") -> str:
        """Execute a task with a specific agent.

        Args:
            agent: The agent to use
            task_description: Task to execute
            context: Additional context

        Returns:
            Agent output
        """
        task = Task(
            description=f"""
{task_description}

PROJECT CONTEXT:
{context}

AVAILABLE TOOLS:
- read_file(file_path): Read file contents
- write_file(file_path, content): Create new file
- edit_file(file_path, old_string, new_string): Modify existing file
- search_files(pattern, directory): Search for files
- list_directory(directory): List directory contents
- run_command(command): Run shell command
- get_project_structure(): Get project structure

IMPORTANT:
1. Use tools to interact with the project
2. Track files you create or modify
3. Follow existing code patterns
4. Provide clean, working code
""",
            expected_output="Complete the task successfully and report what was done",
            agent=agent
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=Config.AGENT_VERBOSE
        )

        result = crew.kickoff()
        return str(result)


__all__ = [
    'AgentManager',
    'AgentTools',
    'OrchestratorAgent',
    'BackendAgent',
    'FrontendAgent',
    'TestingAgent'
]
