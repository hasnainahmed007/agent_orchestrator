"""Hot-reload watcher for skills and custom config files.

Watches skills/custom/ directory for changes and auto-reloads
skills into the registry without restarting the orchestrator.
"""
import time
import threading
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SkillWatcher:
    """Watches a directory for skill file changes and auto-reloads."""

    def __init__(self, watch_dir: Path, registry, poll_interval: float = 2.0):
        self.watch_dir = Path(watch_dir)
        self.registry = registry
        self.poll_interval = poll_interval
        self._file_mtimes: dict[str, float] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start watching for file changes in background thread."""
        if self._running:
            return
        self._running = True
        self._snapshot()
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info(f"Skill watcher started on {self.watch_dir}")

    def stop(self):
        """Stop the watcher thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Skill watcher stopped")

    def _snapshot(self):
        """Take a snapshot of current file modification times."""
        self._file_mtimes = {}
        if not self.watch_dir.exists():
            return
        for f in self.watch_dir.glob("*.json"):
            self._file_mtimes[str(f)] = f.stat().st_mtime

    def _watch_loop(self):
        """Background loop checking for file changes."""
        while self._running:
            try:
                self._check_changes()
            except Exception as e:
                logger.debug(f"Skill watcher error: {e}")
            time.sleep(self.poll_interval)

    def _check_changes(self):
        """Check for added, modified, or removed files."""
        if not self.watch_dir.exists():
            return

        current_files = set()
        for f in self.watch_dir.glob("*.json"):
            path_str = str(f)
            current_files.add(path_str)
            current_mtime = f.stat().st_mtime

            if path_str not in self._file_mtimes:
                # New file added
                self._on_file_added(f)
            elif current_mtime > self._file_mtimes[path_str]:
                # File modified
                self._on_file_modified(f)

        # Check for removed files
        for path_str in list(self._file_mtimes.keys()):
            if path_str not in current_files:
                self._on_file_removed(Path(path_str))

        self._snapshot()

    def _on_file_added(self, filepath: Path):
        """Handle a new skill file."""
        logger.info(f"New skill file detected: {filepath.name}")
        try:
            import json
            data = json.loads(filepath.read_text())
            from skills.registry import SkillModule
            skill = SkillModule.from_dict(data)
            self.registry.add_custom_skill(skill)
            logger.info(f"Auto-loaded skill: {skill.skill_id}")
        except Exception as e:
            logger.warning(f"Failed to load skill {filepath.name}: {e}")

    def _on_file_modified(self, filepath: Path):
        """Handle a modified skill file (reload it)."""
        logger.info(f"Skill file modified: {filepath.name}")
        self._on_file_added(filepath)  # Same logic: overwrite

    def _on_file_removed(self, filepath: Path):
        """Handle a removed skill file."""
        import json
        skill_id = filepath.stem
        logger.info(f"Skill file removed: {skill_id}")
        if skill_id in self.registry.skills:
            # Don't remove built-in skills
            builtin_ids = {
                'python', 'javascript', 'typescript', 'django', 'react',
                'docker', 'devops', 'postgresql', 'system_design', 'security'
            }
            if skill_id not in builtin_ids:
                del self.registry.skills[skill_id]
                logger.info(f"Unloaded skill: {skill_id}")
