"""Agent definitions using CrewAI."""
from typing import List, Dict, Any, Optional
from crewai import Agent, Task, Crew
from pathlib import Path

from config.settings import Config
from core.project_context import ProjectContextScanner
from agents.tools import AgentTools


class AgentManager:
    """Manages creation and execution of dynamic specialized agents."""

    def __init__(self, project_path: Path, llm_provider: str = "auto",
                 llm_model: str = "gpt-4o", llm_api_key: str = ""):
        self.project_path = project_path
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.tools = AgentTools(project_path)
        self.crewai_tools = self.tools.get_crewai_tools()
        self.tool_map = {t.name: t for t in self.crewai_tools}

        self.context_scanner = ProjectContextScanner(project_path)
        self.project_context = None

    def _get_llm(self):
        """Get LLM instance using provider abstraction."""
        from core.llm_providers import create_llm

        provider = self.llm_provider if self.llm_provider != "auto" else "openai"
        return create_llm(
            provider=provider,
            model=self.llm_model,
            api_key=self.llm_api_key,
            base_url=Config.OPENAI_BASE_URL,
            temperature=Config.OPENAI_TEMPERATURE,
            max_tokens=Config.OPENAI_MAX_TOKENS,
        )

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
            llm=self._get_llm(),
            max_iter=Config.AGENT_MAX_ITERATIONS,
            memory=Config.AGENT_MEMORY,
            tools=crewai_tool_objects if crewai_tool_objects else None,
        )

    def get_project_context_summary(self) -> str:
        """Get project context as a string for prompts."""
        if not self.project_context:
            self.scan_project()
        if self.project_context:
            return self.project_context.to_summary()
        return ""

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


__all__ = ['AgentManager', 'AgentTools']
