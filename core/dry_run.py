"""Dry-run mode for previewing agent actions without modifying files.

When enabled, the AgentTools write_file and edit_file methods
log what they would do instead of actually writing.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)


class DryRunContext:
    """Context manager / flag for dry-run mode.

    Usage:
        from core.dry_run import dry_run_mode

        with dry_run_mode():
            agent.execute_task(...)  # No files modified
    """

    _active: bool = False
    _log: List[str] = []

    @classmethod
    def is_active(cls) -> bool:
        return cls._active

    @classmethod
    def enable(cls):
        cls._active = True
        cls._log = []

    @classmethod
    def disable(cls):
        cls._active = False

    @classmethod
    def log_action(cls, action: str, filepath: str, detail: str = ""):
        entry = f"[DRY-RUN] {action}: {filepath}"
        if detail:
            entry += f" ({detail})"
        cls._log.append(entry)
        logger.info(entry)

    @classmethod
    def get_log(cls) -> List[str]:
        return cls._log.copy()

    @classmethod
    def clear_log(cls):
        cls._log = []

    def __enter__(self):
        self.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disable()
        return False


dry_run_mode = DryRunContext


def dry_run_write_file(tools_instance, file_path: str, content: str) -> str:
    """Dry-run version of AgentTools.write_file."""
    if DryRunContext.is_active():
        DryRunContext.log_action(
            "WRITE", file_path,
            f"{len(content)} bytes"
        )
        return f"[DRY-RUN] Would create file: {file_path}"
    return tools_instance._real_write_file(file_path, content)


def dry_run_edit_file(tools_instance, file_path: str, old_string: str, new_string: str) -> str:
    """Dry-run version of AgentTools.edit_file."""
    if DryRunContext.is_active():
        DryRunContext.log_action(
            "EDIT", file_path,
            f"replace {len(old_string)} bytes with {len(new_string)} bytes"
        )
        return f"[DRY-RUN] Would edit file: {file_path}"
    return tools_instance._real_edit_file(file_path, old_string, new_string)


def dry_run_run_command(tools_instance, command: str) -> str:
    """Dry-run version of AgentTools.run_command."""
    if DryRunContext.is_active():
        DryRunContext.log_action("RUN", command)
        return f"[DRY-RUN] Would run: {command}"
    return tools_instance._real_run_command(command)
