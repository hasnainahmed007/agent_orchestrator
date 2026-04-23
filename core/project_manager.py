"""Multi-project support for managing multiple Laravel projects."""
import json
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
    project_type: str = "laravel"
    main_branch: str = "main"
    openai_model: str = "gpt-4o"
    require_approval: bool = True
    auto_merge: bool = False
    daily_budget: float = 5.0
    max_files_per_task: int = 20
    enabled: bool = True
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
        elif not Path(self.path).exists():
            errors.append(f"Project path does not exist: {self.path}")
        
        if self.daily_budget <= 0:
            errors.append("Daily budget must be positive")
        
        return errors


class ProjectManager:
    """Manages multiple Laravel projects."""
    
    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.projects_file = self.state_dir / 'projects.json'
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
