"""Agent Marketplace - share and install community skills."""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Marketplace catalog URL (can be local dir or remote repo)
DEFAULT_MARKETPLACE_REPO = "https://raw.githubusercontent.com/agentorchestrator/marketplace/main"


class MarketplaceManager:
    """Manages the agent skills marketplace.

    Skills can be:
    - Built-in: Bundled with the orchestrator
    - Custom: User-created in skills/custom/
    - Marketplace: Downloaded from the community repository
    """

    def __init__(self, marketplace_dir: Path, skills_dir: Path):
        self.marketplace_dir = Path(marketplace_dir)
        self.skills_dir = Path(skills_dir)
        self.marketplace_dir.mkdir(parents=True, exist_ok=True)

    def list_marketplace_skills(self) -> List[Dict]:
        """List all skills available in the marketplace directory."""
        skills = []
        for skill_file in self.marketplace_dir.glob("*.json"):
            try:
                data = json.loads(skill_file.read_text())
                skills.append({
                    'skill_id': data.get('skill_id', skill_file.stem),
                    'name': data.get('name', skill_file.stem),
                    'category': data.get('category', 'unknown'),
                    'description': data.get('description', ''),
                    'expertise_level': data.get('expertise_level', 'intermediate'),
                    'file': skill_file.name,
                    'source': 'marketplace'
                })
            except Exception as e:
                logger.warning(f"Failed to read marketplace skill {skill_file}: {e}")
        return skills

    def install_skill(self, skill_id: str) -> bool:
        """Install a skill from marketplace to custom skills."""
        source = self.marketplace_dir / f"{skill_id}.json"
        if not source.exists():
            logger.error(f"Marketplace skill not found: {skill_id}")
            return False

        dest = self.skills_dir / f"{skill_id}.json"
        dest.write_text(source.read_text())
        logger.info(f"Installed skill: {skill_id} from marketplace")
        return True

    def uninstall_skill(self, skill_id: str) -> bool:
        """Remove a marketplace-installed skill from custom skills."""
        dest = self.skills_dir / f"{skill_id}.json"
        if dest.exists():
            dest.unlink()
            logger.info(f"Uninstalled skill: {skill_id}")
            return True
        return False

    def publish_skill(self, skill_file: Path) -> bool:
        """Publish a custom skill to the marketplace directory."""
        if not skill_file.exists():
            logger.error(f"Skill file not found: {skill_file}")
            return False

        data = json.loads(skill_file.read_text())
        skill_id = data.get('skill_id', skill_file.stem)

        dest = self.marketplace_dir / f"{skill_id}.json"
        dest.write_text(json.dumps(data, indent=2))
        logger.info(f"Published skill: {skill_id} to marketplace")
        return True

    def search_skills(self, query: str) -> List[Dict]:
        """Search marketplace skills by name, category, or description."""
        query_lower = query.lower()
        results = []
        for skill in self.list_marketplace_skills():
            searchable = f"{skill['name']} {skill['category']} {skill['description']}".lower()
            if query_lower in searchable:
                results.append(skill)
        return results

    def get_marketplace_stats(self) -> Dict:
        """Get marketplace statistics."""
        skills = self.list_marketplace_skills()
        categories = {}
        for skill in skills:
            cat = skill.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1

        return {
            'total_skills': len(skills),
            'categories': categories,
            'skills': skills
        }


# Bundled marketplace skills
BUNDLED_MARKETPLACE_SKILLS = {
    "fastapi": {
        "skill_id": "fastapi",
        "name": "FastAPI Development",
        "category": "framework",
        "description": "Building high-performance REST APIs with FastAPI",
        "expertise_level": "expert",
        "best_practices": [
            "Use Pydantic v2 models for request/response validation",
            "Implement dependency injection for shared logic",
            "Use async endpoints for I/O-bound operations",
            "Add proper OpenAPI documentation tags",
            "Use HTTP status codes semantically"
        ],
        "coding_standards": [
            "Route handlers in separate router files",
            "Use dependency injection for DB sessions",
            "Type hint all function signatures",
            "Use middleware for cross-cutting concerns"
        ],
        "common_patterns": [
            "Repository pattern for database access",
            "Service layer between routes and DB",
            "Background tasks for async operations",
            "OAuth2 + JWT for authentication"
        ],
        "anti_patterns": [
            "Mixing business logic in route handlers",
            "Synchronous heavy operations in async endpoints",
            "Missing input validation",
            "Hardcoding secrets"
        ],
        "tools": ["read_file", "write_file", "edit_file", "search_files", "run_command"],
        "file_patterns": {"api": "api/*.py", "models": "models.py", "schemas": "schemas.py"},
        "system_context": "You are a FastAPI expert. Build production-ready APIs.",
        "validation_rules": ["Run pytest", "Check all endpoints return proper status codes"]
    },
    "cli_tools": {
        "skill_id": "cli_tools",
        "name": "CLI Tool Development",
        "category": "concept",
        "description": "Building command-line interfaces with argparse/click",
        "expertise_level": "intermediate",
        "best_practices": [
            "Use argparse or click for argument parsing",
            "Provide --help for every command",
            "Support --dry-run for safe previews",
            "Use colored output for readability",
            "Exit codes for success/failure"
        ],
        "tools": ["read_file", "write_file", "edit_file", "run_command"],
        "system_context": "Build robust CLI tools following Unix philosophy."
    },
    "data_engineering": {
        "skill_id": "data_engineering",
        "name": "Data Engineering & ETL",
        "category": "concept",
        "description": "Building data pipelines with Python (pandas, sqlite)",
        "expertise_level": "expert",
        "best_practices": [
            "Use pandas for data manipulation",
            "Implement incremental loads where possible",
            "Log every step of the pipeline",
            "Validate data quality at each stage",
            "Handle edge cases: empty files, malformed data"
        ],
        "tools": ["read_file", "write_file", "edit_file", "search_files", "run_command"],
        "system_context": "Build reliable ETL pipelines with proper error handling and logging."
    }
}


def bootstrap_marketplace(marketplace_dir: Path):
    """Initialize marketplace with bundled skills."""
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    for skill_id, skill_data in BUNDLED_MARKETPLACE_SKILLS.items():
        skill_file = marketplace_dir / f"{skill_id}.json"
        if not skill_file.exists():
            skill_file.write_text(json.dumps(skill_data, indent=2))
            logger.info(f"Bootstrapped marketplace skill: {skill_id}")
