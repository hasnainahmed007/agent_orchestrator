"""Project context scanner to give agents understanding of the codebase."""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class ProjectContext:
    """Structured project context."""
    project_name: str
    project_type: str
    laravel_version: str
    has_modules: bool
    services: List[str]
    models: List[str]
    controllers: List[str]
    modules: List[str]
    views: List[str]
    php_version: str
    key_packages: Dict[str, str]
    coding_patterns: Dict[str, Any]
    recent_commits: List[str]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_summary(self) -> str:
        """Generate human-readable summary."""
        summary = f"""# Project Context: {self.project_name}

## Framework
- Type: {self.project_type}
- Laravel Version: {self.laravel_version}
- PHP Version: {self.php_version}
- Nwidart Modules: {'Yes' if self.has_modules else 'No'}

## Code Structure
- Services: {len(self.services)} files
- Models: {len(self.models)} files
- Controllers: {len(self.controllers)} files
- Views: {len(self.views)} files
- Modules: {len(self.modules)} modules

## Existing Services
{chr(10).join([f"- {s}" for s in self.services[:10]])}
{f"... and {len(self.services) - 10} more" if len(self.services) > 10 else ""}

## Existing Models
{chr(10).join([f"- {m}" for m in self.models[:10]])}
{f"... and {len(self.models) - 10} more" if len(self.models) > 10 else ""}

## Modules
{chr(10).join([f"- {m}" for m in self.modules]) if self.modules else "None"}

## Key Dependencies
{chr(10).join([f"- {k}: {v}" for k, v in list(self.key_packages.items())[:10]])}
"""
        return summary


class ProjectContextScanner:
    """Scans Laravel project to build context."""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.context: Optional[ProjectContext] = None
    
    def scan(self) -> ProjectContext:
        """Full project scan."""
        print("🔍 Scanning project context...")
        
        self.context = ProjectContext(
            project_name=self._get_project_name(),
            project_type="laravel",
            laravel_version=self._get_laravel_version(),
            has_modules=self._has_modules(),
            services=self._scan_services(),
            models=self._scan_models(),
            controllers=self._scan_controllers(),
            modules=self._scan_modules(),
            views=self._scan_views(),
            php_version=self._get_php_version(),
            key_packages=self._get_key_packages(),
            coding_patterns=self._analyze_patterns(),
            recent_commits=[]
        )
        
        print(f"✅ Scan complete: {len(self.context.services)} services, {len(self.context.models)} models")
        return self.context
    
    def _get_project_name(self) -> str:
        """Get project name from composer.json."""
        composer_file = self.project_path / 'composer.json'
        if composer_file.exists():
            try:
                data = json.loads(composer_file.read_text())
                return data.get('name', 'unknown-project')
            except:
                pass
        return self.project_path.name
    
    def _get_laravel_version(self) -> str:
        """Get Laravel version from composer.lock."""
        composer_lock = self.project_path / 'composer.lock'
        if composer_lock.exists():
            try:
                data = json.loads(composer_lock.read_text())
                for package in data.get('packages', []):
                    if package.get('name') == 'laravel/framework':
                        return package.get('version', 'unknown')
            except:
                pass
        
        # Try composer.json
        composer_file = self.project_path / 'composer.json'
        if composer_file.exists():
            try:
                data = json.loads(composer_file.read_text())
                version = data.get('require', {}).get('laravel/framework', 'unknown')
                return version
            except:
                pass
        
        return 'unknown'
    
    def _has_modules(self) -> bool:
        """Check if project uses Nwidart Modules."""
        modules_dir = self.project_path / 'Modules'
        return modules_dir.exists() and modules_dir.is_dir()
    
    def _get_php_version(self) -> str:
        """Get PHP version from composer.json."""
        composer_file = self.project_path / 'composer.json'
        if composer_file.exists():
            try:
                data = json.loads(composer_file.read_text())
                version = data.get('require', {}).get('php', 'unknown')
                return version
            except:
                pass
        return 'unknown'
    
    def _get_key_packages(self) -> Dict[str, str]:
        """Get key packages from composer.json."""
        composer_file = self.project_path / 'composer.json'
        if composer_file.exists():
            try:
                data = json.loads(composer_file.read_text())
                packages = {}
                require = data.get('require', {})
                
                key_packages = [
                    'laravel/framework', 'livewire/livewire', 'spatie/laravel-permission',
                    'nwidart/laravel-modules', 'intervention/image', 'guzzlehttp/guzzle'
                ]
                
                for pkg in key_packages:
                    if pkg in require:
                        packages[pkg] = require[pkg]
                
                return packages
            except:
                pass
        return {}
    
    def _scan_services(self) -> List[str]:
        """Scan app/Services directory."""
        services_dir = self.project_path / 'app' / 'Services'
        return self._scan_php_files(services_dir)
    
    def _scan_models(self) -> List[str]:
        """Scan app/Models directory."""
        models_dir = self.project_path / 'app' / 'Models'
        return self._scan_php_files(models_dir)
    
    def _scan_controllers(self) -> List[str]:
        """Scan app/Http/Controllers directory."""
        controllers_dir = self.project_path / 'app' / 'Http' / 'Controllers'
        return self._scan_php_files(controllers_dir)
    
    def _scan_modules(self) -> List[str]:
        """Scan Modules directory."""
        modules_dir = self.project_path / 'Modules'
        if not modules_dir.exists():
            return []
        
        modules = []
        for item in modules_dir.iterdir():
            if item.is_dir():
                # Check if it's a valid module
                if (item / 'module.json').exists():
                    modules.append(item.name)
        
        return modules
    
    def _scan_views(self) -> List[str]:
        """Scan resources/views directory."""
        views_dir = self.project_path / 'resources' / 'views'
        return self._scan_blade_files(views_dir)
    
    def _scan_php_files(self, directory: Path) -> List[str]:
        """Recursively scan for PHP files."""
        files = []
        if not directory.exists():
            return files
        
        for item in directory.rglob('*.php'):
            if item.is_file():
                # Get class name from file
                relative = item.relative_to(self.project_path)
                files.append(str(relative).replace('\\', '/'))
        
        return sorted(files)
    
    def _scan_blade_files(self, directory: Path) -> List[str]:
        """Recursively scan for Blade files."""
        files = []
        if not directory.exists():
            return files
        
        for item in directory.rglob('*.blade.php'):
            if item.is_file():
                relative = item.relative_to(self.project_path)
                files.append(str(relative).replace('\\', '/'))
        
        return sorted(files)
    
    def _analyze_patterns(self) -> Dict[str, Any]:
        """Analyze coding patterns from existing code."""
        patterns = {
            'service_pattern': self._check_service_pattern(),
            'request_validation': self._check_request_pattern(),
            'resource_pattern': self._check_resource_pattern(),
            'test_framework': self._check_test_framework()
        }
        return patterns
    
    def _check_service_pattern(self) -> bool:
        """Check if project uses service pattern."""
        services_dir = self.project_path / 'app' / 'Services'
        return services_dir.exists() and any(services_dir.glob('*.php'))
    
    def _check_request_pattern(self) -> bool:
        """Check if project uses Form Request classes."""
        requests_dir = self.project_path / 'app' / 'Http' / 'Requests'
        return requests_dir.exists() and any(requests_dir.glob('*.php'))
    
    def _check_resource_pattern(self) -> bool:
        """Check if project uses API Resources."""
        resources_dir = self.project_path / 'app' / 'Http' / 'Resources'
        return resources_dir.exists() and any(resources_dir.glob('*.php'))
    
    def _check_test_framework(self) -> str:
        """Check which testing framework is used."""
        if (self.project_path / 'tests' / 'Pest.php').exists():
            return 'Pest'
        elif (self.project_path / 'phpunit.xml').exists():
            return 'PHPUnit'
        return 'Unknown'
    
    def get_service_content(self, service_name: str) -> Optional[str]:
        """Get content of a service class for reference."""
        service_path = self.project_path / 'app' / 'Services' / f'{service_name}.php'
        if service_path.exists():
            return service_path.read_text()
        return None
    
    def get_model_content(self, model_name: str) -> Optional[str]:
        """Get content of a model class for reference."""
        model_path = self.project_path / 'app' / 'Models' / f'{model_name}.php'
        if model_path.exists():
            return model_path.read_text()
        return None
    
    def get_similar_services(self, task_description: str) -> List[str]:
        """Find services similar to the task."""
        if not self.context:
            self.scan()
        
        # Simple keyword matching (could be improved with embeddings)
        keywords = task_description.lower().split()
        similar = []
        
        for service in self.context.services:
            service_lower = service.lower()
            score = sum(1 for kw in keywords if kw in service_lower)
            if score > 0:
                similar.append((service, score))
        
        similar.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in similar[:5]]