"""Multi-project support for managing multiple isolated projects."""
import json
import subprocess
import uuid
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict, field


@dataclass
class ProjectConfig:
    """Configuration for a single project."""
    project_id: str
    name: str
    path: str
    project_type: str = "generic"
    main_branch: str = "main"
    openai_model: str = "gpt-4o"
    require_approval: bool = True
    auto_merge: bool = False
    daily_budget: float = 5.0
    max_files_per_task: int = 20
    enabled: bool = True
    active_agents: List[str] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def validate(self) -> List[str]:
        """Validate project configuration."""
        errors = []
        
        if not self.project_id:
            errors.append("Project ID is required")
        
        if not self.name:
            errors.append("Project name is required")
        
        if not self.path:
            errors.append("Project path is required")
        
        if self.daily_budget <= 0:
            errors.append("Daily budget must be positive")
        
        return errors


class ProjectManager:
    """Manages multiple isolated projects with git repos."""
    
    def __init__(self, state_dir: Path, projects_dir: Path = None):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.projects_file = self.state_dir / 'projects.json'
        self.projects_dir = Path(projects_dir) if projects_dir else self.state_dir.parent / 'projects'
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.projects: Dict[str, ProjectConfig] = {}
        self.active_project_id: Optional[str] = None
        self._load()
    
    def _load(self):
        """Load projects from file."""
        if self.projects_file.exists():
            try:
                data = json.loads(self.projects_file.read_text())
                self.active_project_id = data.get('active_project_id')
                
                for proj_id, proj_data in data.get('projects', {}).items():
                    self.projects[proj_id] = ProjectConfig(**proj_data)
            except:
                self.projects = {}
    
    def _save(self):
        """Save projects to file."""
        data = {
            'active_project_id': self.active_project_id,
            'projects': {
                proj_id: proj.to_dict()
                for proj_id, proj in self.projects.items()
            },
            'updated_at': datetime.now().isoformat()
        }
        self.projects_file.write_text(json.dumps(data, indent=2))
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use as directory name."""
        name = name.lower().strip()
        name = re.sub(r'[^a-z0-9_-]', '-', name)
        name = re.sub(r'-+', '-', name)
        return name.strip('-') or 'project'
    
    def _init_git_repo(self, project_path: Path, main_branch: str = "main") -> bool:
        """Initialize a git repository in the project directory."""
        git_dir = project_path / '.git'
        if git_dir.exists():
            return True
        
        try:
            subprocess.run(
                ['git', 'init', '--initial-branch=' + main_branch],
                cwd=str(project_path),
                capture_output=True,
                timeout=10
            )
            # Create initial commit
            readme = project_path / 'README.md'
            if not readme.exists():
                readme.write_text(f'# {project_path.name}\n')
            subprocess.run(
                ['git', 'add', '-A'],
                cwd=str(project_path),
                capture_output=True,
                timeout=10
            )
            subprocess.run(
                ['git', 'commit', '-m', 'Initial commit (auto-initialized)'],
                cwd=str(project_path),
                capture_output=True,
                timeout=10
            )
            return True
        except Exception:
            return False
    
    def _extract_project_name(self, description: str) -> str:
        """Extract a project name from a task description.
        
        Examples:
            "Create laravel project called blog" -> "blog"
            "Build REST API for ecommerce backend" -> "ecommerce-backend"
            "Add feature to my-app" -> "my-app"
        """
        # Try "called/Named X" pattern
        called_match = re.search(r'(?:called|named|name[d]?\s+)?["\']?([a-zA-Z][a-zA-Z0-9._-]+)["\']?', description)
        if called_match:
            name = called_match.group(1)
            if name.lower() not in ('project', 'app', 'application', 'the'):
                return self._sanitize_name(name)
        
        # Try "for X" pattern
        for_match = re.search(r'for\s+["\']?([a-zA-Z][a-zA-Z0-9._-]+)["\']?', description)
        if for_match:
            name = for_match.group(1)
            if name.lower() not in ('a', 'an', 'the', 'this'):
                return self._sanitize_name(name)
        
        # Use first significant word
        words = description.lower().split()
        skip_words = {'i', 'we', 'you', 'the', 'a', 'an', 'create', 'build', 'add', 'make',
                      'fix', 'update', 'modify', 'change', 'implement', 'develop', 'write'}
        for w in words:
            clean = re.sub(r'[^a-z0-9_-]', '', w)
            if clean and clean not in skip_words and len(clean) > 2:
                return self._sanitize_name(clean)
        
        return None
    
    def auto_create(self, task_description: str, project_type: str = "generic", 
                    requested_path: str = None) -> ProjectConfig:
        """Auto-create a project from a task description.
        
        If requested_path is given, use it directly.
        Otherwise extract project name from description and create at projects/{name}/.
        If name extraction fails, use projects/task-{uuid}/.
        
        Args:
            task_description: Task description to extract name from
            project_type: Type of project (generic, laravel, python, node)
            requested_path: Optional explicit path to use
            
        Returns:
            Created ProjectConfig
        """
        if requested_path and requested_path.lower() != 'auto':
            # User specified path
            proj_path = Path(requested_path).resolve()
            proj_name = proj_path.name
        else:
            # Auto-extract name
            proj_name = self._extract_project_name(task_description)
            if not proj_name:
                proj_name = f"task-{uuid.uuid4().hex[:8]}"
            proj_path = self.projects_dir / proj_name
        
        # Check if path already registered
        existing = self._find_by_path(str(proj_path))
        if existing:
            existing.updated_at = datetime.now().isoformat()
            self._save()
            return existing
        
        proj_path.mkdir(parents=True, exist_ok=True)
        self._init_git_repo(proj_path)
        
        project_id = proj_name
        # Ensure unique ID
        counter = 1
        while project_id in self.projects:
            project_id = f"{proj_name}-{counter}"
            counter += 1
        
        config = ProjectConfig(
            project_id=project_id,
            name=proj_name,
            path=str(proj_path),
            project_type=project_type,
        )
        
        self.projects[project_id] = config
        self._save()
        
        if not self.active_project_id:
            self.active_project_id = project_id
        
        return config
    
    def get_or_create_project(self, task_description: str = None,
                              project_type: str = "generic",
                              requested_path: str = None) -> ProjectConfig:
        """Get existing project or auto-create a new one.
        
        If requested_path is given and exists, return that project.
        Otherwise auto-create.
        """
        if requested_path and requested_path.lower() != 'auto':
            proj_path = Path(requested_path).resolve()
            existing = self._find_by_path(str(proj_path))
            if existing:
                return existing
            return self.auto_create(task_description or "New Project", project_type, requested_path)
        
        # Use active project if exists and no path specified
        if not requested_path:
            active = self.get_active_project()
            if active:
                return active
        
        return self.auto_create(task_description or "New Project", project_type)
    
    def _find_by_path(self, path: str) -> Optional[ProjectConfig]:
        """Find project by path."""
        for proj in self.projects.values():
            if str(proj.path) == str(path):
                return proj
        return None
    
    def add_agent_to_project(self, project_id: str, agent_instance_id: str) -> bool:
        """Track an agent working on a project."""
        project = self.projects.get(project_id)
        if not project:
            return False
        if agent_instance_id not in project.active_agents:
            project.active_agents.append(agent_instance_id)
            project.updated_at = datetime.now().isoformat()
            self._save()
        return True
    
    def add_task_to_project(self, project_id: str, task_id: str) -> bool:
        """Track a task for a project."""
        project = self.projects.get(project_id)
        if not project:
            return False
        if task_id not in project.tasks:
            project.tasks.append(task_id)
            project.updated_at = datetime.now().isoformat()
            self._save()
        return True
    
    def add_project(self, config: ProjectConfig) -> bool:
        """Add a new project.
        
        Args:
            config: Project configuration
            
        Returns:
            True if added successfully
        """
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid project config: {', '.join(errors)}")
        
        if config.project_id in self.projects:
            raise ValueError(f"Project already exists: {config.project_id}")
        
        # Auto-create project dir and init git if path doesn't exist
        proj_path = Path(config.path)
        if not proj_path.exists():
            proj_path.mkdir(parents=True, exist_ok=True)
        self._init_git_repo(proj_path, config.main_branch)
        
        config.updated_at = datetime.now().isoformat()
        self.projects[config.project_id] = config
        self._save()
        
        if not self.active_project_id:
            self.active_project_id = config.project_id
        
        return True
    
    def remove_project(self, project_id: str) -> bool:
        """Remove a project.
        
        Args:
            project_id: Project to remove
            
        Returns:
            True if removed
        """
        if project_id not in self.projects:
            return False
        
        del self.projects[project_id]
        
        if self.active_project_id == project_id:
            self.active_project_id = next(iter(self.projects), None)
        
        self._save()
        return True
    
    def get_project(self, project_id: str) -> Optional[ProjectConfig]:
        """Get project by ID."""
        return self.projects.get(project_id)
    
    def get_active_project(self) -> Optional[ProjectConfig]:
        """Get currently active project."""
        if not self.active_project_id:
            return None
        return self.projects.get(self.active_project_id)
    
    def set_active_project(self, project_id: str) -> bool:
        """Set active project.
        
        Args:
            project_id: Project to activate
            
        Returns:
            True if set successfully
        """
        if project_id not in self.projects:
            return False
        
        self.active_project_id = project_id
        self._save()
        return True
    
    def list_projects(self, enabled_only: bool = False) -> List[ProjectConfig]:
        """List all projects.
        
        Args:
            enabled_only: Only return enabled projects
            
        Returns:
            List of project configurations
        """
        projects = list(self.projects.values())
        
        if enabled_only:
            projects = [p for p in projects if p.enabled]
        
        return sorted(projects, key=lambda p: p.name)
    
    def update_project(self, project_id: str, **kwargs) -> bool:
        """Update project configuration.
        
        Args:
            project_id: Project to update
            **kwargs: Fields to update
            
        Returns:
            True if updated
        """
        if project_id not in self.projects:
            return False
        
        project = self.projects[project_id]
        
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)
        
        project.updated_at = datetime.now().isoformat()
        self._save()
        return True
    
    def toggle_project(self, project_id: str) -> bool:
        """Enable or disable a project."""
        if project_id not in self.projects:
            return False
        
        project = self.projects[project_id]
        project.enabled = not project.enabled
        project.updated_at = datetime.now().isoformat()
        self._save()
        return True
    
    def get_project_stats(self) -> Dict:
        """Get statistics for all projects."""
        total = len(self.projects)
        enabled = sum(1 for p in self.projects.values() if p.enabled)
        disabled = total - enabled
        
        by_type = {}
        for project in self.projects.values():
            project_type = project.project_type
            by_type[project_type] = by_type.get(project_type, 0) + 1
        
        return {
            'total_projects': total,
            'enabled': enabled,
            'disabled': disabled,
            'by_type': by_type,
            'active_project': self.active_project_id
        }
    
    def export_config(self) -> str:
        """Export all project configurations as JSON."""
        data = {
            'projects': {
                proj_id: proj.to_dict()
                for proj_id, proj in self.projects.items()
            },
            'active_project_id': self.active_project_id
        }
        return json.dumps(data, indent=2)
    
    def import_config(self, config_json: str) -> int:
        """Import project configurations from JSON.
        
        Args:
            config_json: JSON string with project configs
            
        Returns:
            Number of projects imported
        """
        data = json.loads(config_json)
        count = 0
        
        for proj_id, proj_data in data.get('projects', {}).items():
            try:
                config = ProjectConfig(**proj_data)
                errors = config.validate()
                if not errors:
                    self.projects[proj_id] = config
                    count += 1
            except:
                continue
        
        if data.get('active_project_id') in self.projects:
            self.active_project_id = data['active_project_id']
        
        self._save()
        return count
