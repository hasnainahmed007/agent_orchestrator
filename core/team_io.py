"""Import/export team configuration as YAML files.

Allows sharing team setups (roles + agents) across installations.
"""
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def export_team(role_manager, filepath: Path) -> bool:
    """Export all roles and agent instances to a YAML file.

    Args:
        role_manager: AgentRoleManager instance
        filepath: Output YAML file path

    Returns:
        True on success
    """
    try:
        data = {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'roles': [],
            'instances': [],
        }

        for role in role_manager.list_roles():
            data['roles'].append(role.to_dict())

        for instance in role_manager.list_instances():
            data['instances'].append(instance.to_dict())

        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(yaml.dump(data, default_flow_style=False, indent=2))
        logger.info(f"Team exported to {filepath}: {len(data['roles'])} roles, {len(data['instances'])} agents")
        return True
    except Exception as e:
        logger.error(f"Failed to export team: {e}")
        return False


def import_team(role_manager, filepath: Path, overwrite: bool = False) -> Dict[str, Any]:
    """Import roles and agent instances from a YAML file.

    Args:
        role_manager: AgentRoleManager instance
        filepath: Input YAML file path
        overwrite: If True, overwrite existing roles/instances with same ID

    Returns:
        Dict with 'created_roles', 'created_instances', 'skipped_roles', 'skipped_instances', 'errors'
    """
    result = {
        'created_roles': [],
        'created_instances': [],
        'skipped_roles': [],
        'skipped_instances': [],
        'errors': [],
    }

    if not filepath.exists():
        result['errors'].append(f"File not found: {filepath}")
        return result

    try:
        data = yaml.safe_load(filepath.read_text())
    except yaml.YAMLError as e:
        result['errors'].append(f"Invalid YAML: {e}")
        return result
    except Exception as e:
        result['errors'].append(f"Failed to read file: {e}")
        return result

    from agents.roles import AgentRole, AgentInstance

    for role_data in data.get('roles', []):
        role_id = role_data.get('role_id', '')
        existing = role_manager.get_role(role_id) if role_id else None
        if existing and not overwrite:
            result['skipped_roles'].append(role_id)
            continue

        try:
            role = AgentRole.from_dict(role_data)
            role_manager.create_role(role)
            result['created_roles'].append(role_id)
        except Exception as e:
            result['errors'].append(f"Failed to create role {role_id}: {e}")

    for inst_data in data.get('instances', []):
        instance_id = inst_data.get('instance_id', '')
        existing = role_manager.get_instance(instance_id) if instance_id else None
        if existing and not overwrite:
            result['skipped_instances'].append(instance_id)
            continue

        try:
            inst = AgentInstance.from_dict(inst_data)
            role_manager._instances[inst.instance_id] = inst
            role_manager._save()
            result['created_instances'].append(instance_id)
        except Exception as e:
            result['errors'].append(f"Failed to create instance {instance_id}: {e}")

    logger.info(
        f"Team imported from {filepath}: "
        f"{len(result['created_roles'])} roles, {len(result['created_instances'])} agents"
    )
    return result
