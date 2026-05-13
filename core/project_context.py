"""Project context scanner to give agents understanding of the codebase."""
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ProjectContext:
    """Structured project context - dynamic per project type."""
    project_name: str
    project_type: str
    language: str
    framework: str
    framework_version: str
    dependencies: Dict[str, str]
    structure: Dict[str, List[str]]
    config_files: List[str]
    test_framework: str
    coding_patterns: Dict[str, Any]
    recent_commits: List[str]

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [f"# Project Context: {self.project_name}"]
        lines.append(f"")
        lines.append(f"## Overview")
        lines.append(f"- Type: {self.project_type}")
        lines.append(f"- Language: {self.language}")
        lines.append(f"- Framework: {self.framework} {self.framework_version}")
        lines.append(f"- Test framework: {self.test_framework}")
        lines.append(f"")

        lines.append(f"## Structure")
        for category, files in self.structure.items():
            if files:
                lines.append(f"- {category}: {len(files)} files")
                for f in files[:5]:
                    lines.append(f"  - {f}")
                if len(files) > 5:
                    lines.append(f"  ... and {len(files) - 5} more")
        lines.append(f"")

        if self.dependencies:
            lines.append(f"## Key Dependencies")
            for k, v in list(self.dependencies.items())[:15]:
                lines.append(f"- {k}: {v}")

        if self.config_files:
            lines.append(f"")
            lines.append(f"## Config Files")
            for cf in self.config_files:
                lines.append(f"- {cf}")

        return "\n".join(lines)


class ProjectContextScanner:
    """Scans project to build context dynamically based on project type."""

    SCANNERS = {
        'python': ['_scan_python'],
        'node': ['_scan_node'],
        'laravel': ['_scan_laravel'],
        'generic': ['_scan_generic'],
    }

    def __init__(self, project_path: Path, project_type: str = None):
        self.project_path = Path(project_path)
        self.project_type = project_type or 'generic'
        self.context: Optional[ProjectContext] = None

    def scan(self) -> ProjectContext:
        """Full project scan, dispatching to type-specific scanner."""
        print(f"Scanning project context (type={self.project_type})...")

        scan_methods = self.SCANNERS.get(self.project_type, ['_scan_generic'])
        result = {
            'project_name': self._get_project_name(),
            'project_type': self.project_type,
            'language': '',
            'framework': '',
            'framework_version': '',
            'dependencies': {},
            'structure': {},
            'config_files': [],
            'test_framework': 'unknown',
            'coding_patterns': {},
            'recent_commits': self._get_recent_commits(),
        }

        for method_name in scan_methods:
            method = getattr(self, method_name, None)
            if method:
                result.update(method())

        self.context = ProjectContext(**result)

        total_files = sum(len(v) for v in self.context.structure.values())
        print(f"Scan complete: {len(self.context.dependencies)} deps, {total_files} files")
        return self.context

    def _get_project_name(self) -> str:
        """Get project name from common config files."""
        for cfg in ['pyproject.toml', 'package.json', 'composer.json']:
            cfg_path = self.project_path / cfg
            if cfg_path.exists():
                try:
                    if cfg == 'pyproject.toml':
                        return self._parse_toml_name(cfg_path)
                    elif cfg == 'package.json':
                        data = json.loads(cfg_path.read_text())
                        return data.get('name', self.project_path.name)
                    elif cfg == 'composer.json':
                        data = json.loads(cfg_path.read_text())
                        return data.get('name', self.project_path.name)
                except Exception:
                    pass
        return self.project_path.name

    def _parse_toml_name(self, toml_path: Path) -> str:
        """Simple TOML parser for project name."""
        content = toml_path.read_text()
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('name'):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
        return self.project_path.name

    def _get_recent_commits(self) -> List[str]:
        """Get recent git commits."""
        try:
            result = subprocess.run(
                ['git', 'log', '--oneline', '-10'],
                cwd=str(self.project_path),
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
        except Exception:
            pass
        return []

    def _scan_files(self, extensions: List[str], exclude_dirs: List[str] = None) -> List[str]:
        """Generic file scanner by extension."""
        exclude_dirs = exclude_dirs or ['__pycache__', 'node_modules', '.git', 'vendor']
        files = []
        for ext in extensions:
            for item in self.project_path.rglob(f'*{ext}'):
                # Skip excluded directories
                parts = item.relative_to(self.project_path).parts
                if any(ex in parts for ex in exclude_dirs):
                    continue
                if item.is_file():
                    files.append(str(item.relative_to(self.project_path)))
        return sorted(files)

    # ── Python scanner ────────────────────────────────────────────────

    def _scan_python(self) -> dict:
        """Scan Python project context."""
        info = {
            'language': 'python',
            'framework': 'none',
            'framework_version': '',
            'dependencies': {},
            'structure': {},
            'config_files': [],
            'test_framework': 'pytest',
            'coding_patterns': {},
        }

        # Detect framework
        if (self.project_path / 'manage.py').exists():
            info['framework'] = 'Django'
            info['framework_version'] = self._get_python_pkg_version('Django')
        elif self._has_py_dep('fastapi'):
            info['framework'] = 'FastAPI'
            info['framework_version'] = self._get_python_pkg_version('fastapi')
        elif self._has_py_dep('flask'):
            info['framework'] = 'Flask'
            info['framework_version'] = self._get_python_pkg_version('flask')

        # Config files
        for cf in ['pyproject.toml', 'setup.py', 'setup.cfg', 'requirements.txt',
                    'requirements-dev.txt', 'Pipfile', 'Makefile', '.env.example']:
            if (self.project_path / cf).exists():
                info['config_files'].append(cf)

        # Dependencies
        info['dependencies'] = self._get_python_deps()

        # Structure
        info['structure'] = {
            'packages': self._scan_files(['.py'], exclude_dirs=['__pycache__', '.git', 'node_modules']),
            'tests': self._scan_files(['.py'], exclude_dirs=['__pycache__', 'node_modules'])
        }
        # Separate tests
        info['structure']['tests'] = [f for f in info['structure']['packages'] if 'test' in f.lower()]
        info['structure']['source'] = [f for f in info['structure']['packages'] if 'test' not in f.lower()]
        del info['structure']['packages']

        # Test framework
        if (self.project_path / 'pytest.ini').exists() or \
           (self.project_path / 'pyproject.toml').exists():
            info['test_framework'] = 'pytest'
        elif (self.project_path / 'setup.cfg').exists():
            info['test_framework'] = 'pytest/unittest'

        # Coding patterns
        info['coding_patterns'] = {
            'type_hints': self._check_py_pattern('def ', ' -> '),
            'async_usage': self._check_py_pattern('async def', ''),
            'uses_pydantic': self._has_py_dep('pydantic'),
            'uses_sqlalchemy': self._has_py_dep('sqlalchemy'),
        }

        return info

    def _get_python_deps(self) -> Dict[str, str]:
        """Extract Python dependencies from pyproject.toml or requirements.txt."""
        deps = {}

        # Try pyproject.toml
        pyproject = self.project_path / 'pyproject.toml'
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                in_deps = False
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('[tool.poetry.dependencies]') or \
                       line.startswith('[project]'):
                        in_deps = True
                        continue
                    if in_deps and line.startswith('['):
                        in_deps = False
                        continue
                    if in_deps and '=' in line and not line.startswith('#'):
                        name, version = line.split('=', 1)
                        deps[name.strip().strip('"').strip("'")] = version.strip().strip('"').strip("'")
            except Exception:
                pass

        # Try requirements.txt
        reqs = self.project_path / 'requirements.txt'
        if reqs.exists() and not deps:
            try:
                for line in reqs.read_text().split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and '==' in line:
                        name, version = line.split('==', 1)
                        deps[name.strip()] = version.strip()
            except Exception:
                pass

        return deps

    def _get_python_pkg_version(self, pkg_name: str) -> str:
        """Get version of a Python package."""
        try:
            result = subprocess.run(
                ['pip', 'show', pkg_name],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        return line.split(':', 1)[1].strip()
        except Exception:
            pass
        return 'unknown'

    def _has_py_dep(self, pkg_name: str) -> bool:
        """Check if Python dependency exists."""
        deps = self._get_python_deps()
        return pkg_name.lower() in [d.lower() for d in deps]

    def _check_py_pattern(self, keyword: str, secondary: str) -> bool:
        """Check if Python files use a pattern."""
        py_files = list(self.project_path.rglob('*.py'))
        checked = 0
        for f in py_files:
            if checked >= 5:
                break
            try:
                content = f.read_text()
                if keyword in content:
                    if not secondary or secondary in content:
                        return True
                checked += 1
            except Exception:
                pass
        return False

    # ── Node.js scanner ──────────────────────────────────────────────

    def _scan_node(self) -> dict:
        """Scan Node.js project context."""
        info = {
            'language': 'javascript/typescript',
            'framework': 'none',
            'framework_version': '',
            'dependencies': {},
            'structure': {},
            'config_files': [],
            'test_framework': 'jest',
            'coding_patterns': {},
        }

        # Detect framework
        package_deps = self._get_node_deps()
        if 'next' in package_deps:
            info['framework'] = 'Next.js'
            info['framework_version'] = package_deps.get('next', '')
        elif 'react' in package_deps and 'react-dom' in package_deps:
            info['framework'] = 'React'
            info['framework_version'] = package_deps.get('react', '')
        elif 'vue' in package_deps:
            info['framework'] = 'Vue'
            info['framework_version'] = package_deps.get('vue', '')
        elif 'express' in package_deps:
            info['framework'] = 'Express'
            info['framework_version'] = package_deps.get('express', '')

        # Config files
        for cf in ['package.json', 'tsconfig.json', 'jsconfig.json', '.eslintrc.*',
                    '.prettierrc', 'next.config.*', 'vite.config.*', 'webpack.config.*']:
            matches = list(self.project_path.glob(cf))
            for m in matches:
                info['config_files'].append(str(m.relative_to(self.project_path)))

        info['dependencies'] = package_deps

        # Structure
        all_files = self._scan_files(
            ['.js', '.jsx', '.ts', '.tsx', '.css', '.html'],
            exclude_dirs=['node_modules', '.git', '.next', 'dist', 'build']
        )
        info['structure'] = {
            'source': [f for f in all_files if 'test' not in f.lower() and '__tests__' not in f.lower()],
            'tests': [f for f in all_files if 'test' in f.lower() or '__tests__' in f.lower()],
        }

        # TypeScript?
        ts_files = [f for f in all_files if f.endswith(('.ts', '.tsx'))]
        if ts_files:
            info['language'] = 'typescript'

        # Test framework
        if 'jest' in package_deps:
            info['test_framework'] = 'jest'
        elif 'vitest' in package_deps:
            info['test_framework'] = 'vitest'
        elif 'mocha' in package_deps:
            info['test_framework'] = 'mocha'

        return info

    def _get_node_deps(self) -> Dict[str, str]:
        """Extract Node.js dependencies from package.json."""
        package_json = self.project_path / 'package.json'
        if not package_json.exists():
            return {}
        try:
            data = json.loads(package_json.read_text())
            deps = {}
            deps.update(data.get('dependencies', {}))
            deps.update(data.get('devDependencies', {}))
            return deps
        except Exception:
            return {}

    # ── Laravel scanner ──────────────────────────────────────────────

    def _scan_laravel(self) -> dict:
        """Scan Laravel project context."""
        info = {
            'language': 'php',
            'framework': 'Laravel',
            'framework_version': self._get_laravel_version(),
            'dependencies': self._get_composer_deps(),
            'structure': {
                'services': self._scan_php_dir('app', 'Services'),
                'models': self._scan_php_dir('app', 'Models'),
                'controllers': self._scan_php_dir('app', 'Http', 'Controllers'),
                'views': self._scan_blade_files(),
                'modules': self._scan_modules(),
            },
            'config_files': [cf for cf in ['composer.json', 'composer.lock', '.env.example', 'phpunit.xml']
                           if (self.project_path / cf).exists()],
            'test_framework': self._check_test_framework(),
            'coding_patterns': {
                'service_pattern': self._check_dir('app', 'Services'),
                'request_validation': self._check_dir('app', 'Http', 'Requests'),
                'resource_pattern': self._check_dir('app', 'Http', 'Resources'),
            },
        }

        # PHP version
        php_ver = info['dependencies'].get('php', 'unknown')
        info['coding_patterns']['php_version'] = php_ver

        return info

    def _get_laravel_version(self) -> str:
        """Get Laravel version."""
        composer_lock = self.project_path / 'composer.lock'
        if composer_lock.exists():
            try:
                data = json.loads(composer_lock.read_text())
                for package in data.get('packages', []):
                    if package.get('name') == 'laravel/framework':
                        return package.get('version', 'unknown')
            except Exception:
                pass

        composer_file = self.project_path / 'composer.json'
        if composer_file.exists():
            try:
                data = json.loads(composer_file.read_text())
                return data.get('require', {}).get('laravel/framework', 'unknown')
            except Exception:
                pass
        return 'unknown'

    def _get_composer_deps(self) -> Dict[str, str]:
        """Get dependencies from composer.json."""
        composer_file = self.project_path / 'composer.json'
        if not composer_file.exists():
            return {}
        try:
            data = json.loads(composer_file.read_text())
            deps = {}
            deps.update(data.get('require', {}))
            deps.update(data.get('require-dev', {}))
            return deps
        except Exception:
            return {}

    def _scan_php_dir(self, *parts: str) -> List[str]:
        """Scan PHP files in a specific directory."""
        target = self.project_path.joinpath(*parts)
        if not target.exists():
            return []
        files = []
        for item in target.rglob('*.php'):
            if item.is_file():
                files.append(str(item.relative_to(self.project_path)))
        return sorted(files)

    def _scan_blade_files(self) -> List[str]:
        """Scan Blade template files."""
        views_dir = self.project_path / 'resources' / 'views'
        if not views_dir.exists():
            return []
        files = []
        for item in views_dir.rglob('*.blade.php'):
            if item.is_file():
                files.append(str(item.relative_to(self.project_path)))
        return sorted(files)

    def _scan_modules(self) -> List[str]:
        """Scan Nwidart modules."""
        modules_dir = self.project_path / 'Modules'
        if not modules_dir.exists():
            return []
        modules = []
        for item in modules_dir.iterdir():
            if item.is_dir() and (item / 'module.json').exists():
                modules.append(item.name)
        return modules

    def _check_dir(self, *parts: str) -> bool:
        """Check if a directory exists with files."""
        target = self.project_path.joinpath(*parts)
        return target.exists() and any(target.glob('*.php'))

    def _check_test_framework(self) -> str:
        """Detect PHP test framework."""
        if (self.project_path / 'tests' / 'Pest.php').exists():
            return 'Pest'
        elif (self.project_path / 'phpunit.xml').exists():
            return 'PHPUnit'
        return 'Unknown'

    # ── Generic scanner ──────────────────────────────────────────────

    def _scan_generic(self) -> dict:
        """Scan generic project - detect what we can."""
        info = {
            'language': '',
            'framework': '',
            'framework_version': '',
            'dependencies': {},
            'structure': {},
            'config_files': [],
            'test_framework': 'unknown',
            'coding_patterns': {},
        }

        # Detect language by file extension prevalence
        ext_counts = {}
        for item in self.project_path.rglob('*'):
            if item.is_file():
                ext = item.suffix.lower()
                if ext:
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
                    if len(ext_counts) > 10:
                        break

        if ext_counts:
            dominant = max(ext_counts, key=ext_counts.get)
            lang_map = {
                '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                '.jsx': 'javascript/react', '.tsx': 'typescript/react',
                '.php': 'php', '.rb': 'ruby', '.go': 'go',
                '.rs': 'rust', '.java': 'java', '.cs': 'csharp',
                '.css': 'css', '.html': 'html',
            }
            info['language'] = lang_map.get(dominant, f'unknown ({dominant})')

        # List all files (limited)
        all_files = self._scan_files(
            [k for k in ext_counts],
            exclude_dirs=['.git', '__pycache__', 'node_modules', 'vendor']
        )
        info['structure'] = {
            'source': all_files[:50],
            'tests': [f for f in all_files if 'test' in f.lower() or 'spec' in f.lower()],
        }

        # Detect config files by name
        config_names = [
            'pyproject.toml', 'package.json', 'composer.json', 'Cargo.toml',
            'go.mod', 'Gemfile', 'Makefile', 'Dockerfile', 'docker-compose.yml',
            '.env.example', '.env', '.gitignore', 'README.md',
        ]
        for cf in config_names:
            if (self.project_path / cf).exists():
                info['config_files'].append(cf)

        return info

    # ── Helpers ──────────────────────────────────────────────────────

    def get_service_content(self, service_name: str) -> Optional[str]:
        """Get content of a service class for reference (Laravel)."""
        service_path = self.project_path / 'app' / 'Services' / f'{service_name}.php'
        if service_path.exists():
            return service_path.read_text()
        return None

    def get_model_content(self, model_name: str) -> Optional[str]:
        """Get content of a model class for reference (Laravel)."""
        model_path = self.project_path / 'app' / 'Models' / f'{model_name}.php'
        if model_path.exists():
            return model_path.read_text()
        return None

    def get_similar_services(self, task_description: str) -> List[str]:
        """Find services similar to the task (Laravel)."""
        if not self.context:
            self.scan()

        keywords = task_description.lower().split()
        similar = []

        services = self.context.structure.get('services', [])
        for service in services:
            service_lower = service.lower()
            score = sum(1 for kw in keywords if kw in service_lower)
            if score > 0:
                similar.append((service, score))

        similar.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in similar[:5]]
