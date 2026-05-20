"""Plugin system for extending Agent Orchestrator.

Plugins can add:
- Custom LLM providers
- Custom validators
- Custom project scanners
- Custom tools for agents
- Custom notification channels

Plugins are discovered via Python entry_points under the
'agent_orchestrator.plugins' group.

To create a plugin, define a class with a 'register' method and
add it to your package's setup.cfg or pyproject.toml:

    [project.entry-points."agent_orchestrator.plugins"]
    my_plugin = my_package.plugin:MyPlugin
"""
import logging
import pkg_resources
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PluginManifest:
    """Metadata for a plugin."""
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    category: str = "general"  # provider, validator, scanner, tool, notification
    entry_point: str = ""


class PluginManager:
    """Discovers and manages plugins."""

    PLUGIN_GROUP = "agent_orchestrator.plugins"

    def __init__(self):
        self._plugins: Dict[str, Any] = {}
        self._validators: List[Callable] = []
        self._scanners: List[Callable] = []
        self._llm_providers: Dict[str, Callable] = []
        self._tools: List[Callable] = []
        self._notifiers: List[Callable] = []

    def discover(self):
        """Discover all installed plugins via entry_points."""
        try:
            for entry_point in pkg_resources.iter_entry_points(self.PLUGIN_GROUP):
                try:
                    plugin_class = entry_point.load()
                    plugin = plugin_class()
                    if hasattr(plugin, 'register'):
                        plugin.register(self)
                        self._plugins[entry_point.name] = plugin
                        logger.info(f"Loaded plugin: {entry_point.name}")
                except Exception as e:
                    logger.warning(f"Failed to load plugin {entry_point.name}: {e}")
        except Exception as e:
            logger.debug(f"Plugin discovery skipped: {e}")

        return self

    def register_validator(self, name: str, validator_fn: Callable):
        """Register a custom validator function.

        Args:
            name: Unique validator name
            validator_fn: Function(files: List[str], project_path: Path) -> ValidationResult
        """
        self._validators.append(validator_fn)
        logger.info(f"Registered validator plugin: {name}")

    def register_scanner(self, name: str, scanner_fn: Callable):
        """Register a custom project scanner.

        Args:
            name: Unique scanner name
            scanner_fn: Function(project_path: Path) -> dict
        """
        self._scanners.append(scanner_fn)
        logger.info(f"Registered scanner plugin: {name}")

    def register_llm_provider(self, name: str, provider_fn: Callable):
        """Register a custom LLM provider.

        Args:
            name: Provider name (e.g., 'my_provider')
            provider_fn: Function(model, api_key, base_url, ...) -> LLM instance
        """
        from core.llm_providers import LLM_PROVIDERS
        LLM_PROVIDERS[name] = provider_fn
        logger.info(f"Registered LLM provider: {name}")

    def register_tool(self, name: str, tool_instance):
        """Register a custom agent tool.

        Args:
            name: Tool name
            tool_instance: CrewAI BaseTool instance
        """
        self._tools.append((name, tool_instance))
        logger.info(f"Registered tool plugin: {name}")

    def register_notifier(self, name: str, notifier_fn: Callable):
        """Register a custom notification channel.

        Args:
            name: Channel name (e.g., 'discord', 'slack')
            notifier_fn: Async function(message: str, **kwargs)
        """
        self._notifiers.append((name, notifier_fn))
        logger.info(f"Registered notifier plugin: {name}")

    def get_custom_validators(self) -> List[Callable]:
        return self._validators

    def get_custom_scanners(self) -> List[Callable]:
        return self._scanners

    def get_custom_tools(self) -> List[tuple]:
        return self._tools

    def get_notifiers(self) -> List[tuple]:
        return self._notifiers

    def list_plugins(self) -> List[Dict]:
        """List all loaded plugins."""
        result = []
        for name, plugin in self._plugins.items():
            manifest = getattr(plugin, 'manifest', None)
            if manifest:
                result.append({
                    'name': name,
                    'version': manifest.version,
                    'description': manifest.description,
                    'category': manifest.category,
                })
            else:
                result.append({'name': name, 'version': 'unknown'})
        return result


_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get or create the singleton PluginManager."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager().discover()
    return _plugin_manager


def reset_plugin_manager():
    """Reset plugin manager (for testing)."""
    global _plugin_manager
    _plugin_manager = None
