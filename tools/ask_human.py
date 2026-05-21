"""Ask Human tool for CrewAI agents.

When an agent encounters a problem they cannot solve, they call this tool.
The tool pauses execution, notifies the human via Telegram, and waits for a
response before returning it to the agent so work can continue.
"""
import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class AskHumanTool:
    """A CrewAI-compatible tool that lets agents ask humans for help.

    Usage:
        orchestrator = ...
        tool = AskHumanTool(
            on_help_requested=orchestrator.request_help,
            get_help_response=orchestrator.get_help_response,
            task_id="TASK-123",
        )
        crewai_tool = tool.as_crewai_tool()
    """

    def __init__(
        self,
        on_help_requested: Callable,
        get_help_response: Callable,
        task_id: str,
        timeout: int = 3600,
    ):
        """Initialize the tool.

        Args:
            on_help_requested: Async/sync callable(task_id, question) -> None
                Called when the agent requests help. Should notify human.
            get_help_response: Callable(task_id) -> Optional[str]
                Blocking call that returns human response when available.
            task_id: The task this tool is attached to.
            timeout: Max seconds to wait for human response (default 1 hour).
        """
        self._on_help_requested = on_help_requested
        self._get_help_response = get_help_response
        self._task_id = task_id
        self._timeout = timeout

    def ask_human(self, question: str) -> str:
        """Ask the human for help and wait for a response.

        This function blocks until the human responds or timeout is reached.

        Args:
            question: The question or problem description for the human.

        Returns:
            The human's response, or a timeout message.
        """
        logger.info(f"Agent requesting human help: {question[:200]}")

        # Notify the human
        try:
            self._on_help_requested(self._task_id, question)
        except Exception as e:
            logger.error(f"Failed to notify human: {e}")
            return f"[ERROR] Could not notify human: {e}"

        # Wait for human response
        start_time = time.time()
        while (time.time() - start_time) < self._timeout:
            try:
                response = self._get_help_response(self._task_id)
                if response is not None:
                    logger.info(f"Human responded: {response[:200]}")
                    return response
            except Exception as e:
                logger.error(f"Error checking for human response: {e}")

            time.sleep(2)  # Poll every 2 seconds

        return (
            "[TIMEOUT] No human response received within "
            f"{self._timeout} seconds. The task will be marked as failed."
        )

    def as_crewai_tool(self):
        """Return a CrewAI-compatible tool instance."""
        from crewai.tools import tool

        ask_human_fn = self.ask_human

        @tool("ask_human")
        def _ask_human(question: str) -> str:
            """Ask the human supervisor for help with a problem.

            Use this when you encounter an issue you cannot resolve on your own,
            such as:
            - Configuration problems (missing dependencies, port conflicts)
            - Unclear requirements
            - Permission issues
            - Unexpected errors you don't understand

            Args:
                question: Describe the problem clearly. What did you try?
                         What is blocking you? What help do you need?

            Returns:
                The human's response with instructions on how to proceed.
            """
            return ask_human_fn(question)

        return _ask_human


def create_ask_human_tool(
    on_help_requested: Callable,
    get_help_response: Callable,
    task_id: str,
    timeout: int = 3600,
) -> Callable:
    """Factory function to create an ask_human CrewAI tool.

    Args:
        on_help_requested: Called when agent requests help.
        get_help_response: Blocking call for human response.
        task_id: Task ID.
        timeout: Max wait seconds.

    Returns:
        A CrewAI-compatible tool function.
    """
    instance = AskHumanTool(
        on_help_requested=on_help_requested,
        get_help_response=get_help_response,
        task_id=task_id,
        timeout=timeout,
    )
    return instance.as_crewai_tool()
