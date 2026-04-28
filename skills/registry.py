"""Pre-defined skill modules with best practices, coding standards, and tool definitions."""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class SkillModule:
    """A pre-defined skill module that agents can possess."""
    skill_id: str
    name: str
    category: str  # e.g., 'language', 'framework', 'devops', 'database', 'concept'
    description: str
    expertise_level: str  # 'beginner', 'intermediate', 'expert', 'master'
    
    # Knowledge base
    best_practices: List[str] = field(default_factory=list)
    coding_standards: List[str] = field(default_factory=list)
    common_patterns: List[str] = field(default_factory=list)
    anti_patterns: List[str] = field(default_factory=list)
    
    # Tools this skill enables
    tools: List[str] = field(default_factory=list)
    
    # File patterns this skill works with
    file_patterns: Dict[str, str] = field(default_factory=dict)
    
    # Prompt context that gets injected when agent has this skill
    system_context: str = ""
    
    # Validation rules specific to this skill
    validation_rules: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'skill_id': self.skill_id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'expertise_level': self.expertise_level,
            'best_practices': self.best_practices,
            'coding_standards': self.coding_standards,
            'common_patterns': self.common_patterns,
            'anti_patterns': self.anti_patterns,
            'tools': self.tools,
            'file_patterns': self.file_patterns,
            'system_context': self.system_context,
            'validation_rules': self.validation_rules
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SkillModule':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# =============================================================================
# PRE-DEFINED SKILL MODULES
# =============================================================================

SKILL_LIBRARY: Dict[str, SkillModule] = {
    
    # Programming Languages
    # -------------------------------------------------------------------------
    
    'python': SkillModule(
        skill_id='python',
        name='Python Development',
        category='language',
        description='Expert-level Python programming with modern best practices',
        expertise_level='expert',
        best_practices=[
            'Follow PEP 8 style guide',
            'Use type hints (PEP 484) for function signatures',
            'Write docstrings for all public modules, classes, methods',
            'Use context managers (with statements) for resource management',
            'Prefer list/dict comprehensions over simple loops',
            'Use pathlib for file path operations',
            'Handle exceptions specifically, avoid bare except',
            'Use f-strings for string formatting (Python 3.6+)',
            'Write unit tests with pytest',
            'Use virtual environments for dependency isolation'
        ],
        coding_standards=[
            'Max line length: 88 characters (Black formatter default)',
            'Use snake_case for variables and functions',
            'Use PascalCase for class names',
            'Use UPPER_SNAKE_CASE for constants',
            'Single leading underscore for internal use',
            'Double leading underscore for name mangling (avoid)',
            'Always use explicit imports (no wildcard imports)',
            'Group imports: stdlib, third-party, local'
        ],
        common_patterns=[
            'Factory pattern for object creation',
            'Decorator pattern for cross-cutting concerns',
            'Context manager pattern for resource management',
            'Dataclasses for data containers (Python 3.7+)',
            'Enum classes for constants',
            'Protocol classes for structural subtyping',
            'Dependency injection for testability'
        ],
        anti_patterns=[
            'Using mutable default arguments',
            'Catching bare Exception without logging',
            'Using global state',
            'Circular imports',
            'Blocking I/O in async code',
            'Using eval/exec with untrusted input'
        ],
        tools=['read_file', 'write_file', 'edit_file', 'search_files', 'run_command'],
        file_patterns={
            'module': '{name}.py',
            'package': '{name}/__init__.py',
            'test': 'test_{name}.py',
            'config': '{name}.yaml',
            'requirements': 'requirements.txt'
        },
        system_context="""
You are a Python expert. You write clean, type-hinted, well-documented Python code.
You follow PEP 8, use modern Python features (3.10+), and prioritize readability.
You always consider edge cases, write tests, and handle errors gracefully.
        """,
        validation_rules=[
            'Run python -m py_compile to check syntax',
            'Run pytest for test validation',
            'Run mypy for type checking',
            'Check for import errors'
        ]
    ),
    
    'javascript': SkillModule(
        skill_id='javascript',
        name='JavaScript Development',
        category='language',
        description='Modern JavaScript (ES2023+) with Node.js and browser environments',
        expertise_level='expert',
        best_practices=[
            'Use const by default, let when reassignment needed, avoid var',
            'Use async/await over raw Promises',
            'Use destructuring for cleaner code',
            'Use template literals over string concatenation',
            'Write JSDoc comments for public APIs',
            'Use ES modules (import/export) over CommonJS',
            'Handle errors with try/catch in async functions',
            'Use strict equality (===) always',
            'Avoid callback hell with async patterns',
            'Write unit tests with Jest or Vitest'
        ],
        coding_standards=[
            'Max line length: 100 characters',
            'Use camelCase for variables and functions',
            'Use PascalCase for classes and React components',
            'Use SCREAMING_SNAKE_CASE for constants',
            'Semicolons required',
            '2-space indentation',
            'Single quotes for strings'
        ],
        common_patterns=[
            'Module pattern with IIFE or ES modules',
            'Observer pattern for event handling',
            'Promise-based async operations',
            'Destructuring assignments',
            'Spread operator for immutability',
            'Optional chaining (?.) and nullish coalescing (??)',
            'Functional programming patterns (map, filter, reduce)'
        ],
        anti_patterns=[
            'Using == instead of ===',
            'Mutating function arguments',
            'Using eval() or new Function()',
            'Callback hell without async/await',
            'Global variable pollution',
            'Memory leaks from uncleared event listeners'
        ],
        tools=['read_file', 'write_file', 'edit_file', 'search_files', 'run_command'],
        file_patterns={
            'module': '{name}.js',
            'es_module': '{name}.mjs',
            'test': '{name}.test.js',
            'config': '{name}.config.js'
        },
        system_context="""
You are a JavaScript expert. You write modern, clean ES2023+ code.
You prefer functional patterns, immutable data structures, and async/await.
You understand both Node.js and browser environments deeply.
        """,
        validation_rules=[
            'Run eslint for linting',
            'Run jest for testing',
            'Check for syntax errors with node --check'
        ]
    ),
    
    'typescript': SkillModule(
        skill_id='typescript',
        name='TypeScript Development',
        category='language',
        description='TypeScript with strict typing and advanced patterns',
        expertise_level='expert',
        best_practices=[
            'Enable strict mode in tsconfig.json',
            'Use explicit return types on public APIs',
            'Prefer interfaces for object shapes, types for unions',
            'Use enums for related constants',
            'Leverage generics for reusable code',
            'Use readonly for immutable properties',
            'Use discriminated unions for state machines',
            'Avoid any - use unknown instead',
            'Use optional chaining and nullish coalescing',
            'Write tests with Jest/Vitest + ts-jest'
        ],
        coding_standards=[
            'Max line length: 100 characters',
            'Use PascalCase for types, interfaces, enums, classes',
            'Use camelCase for variables, functions, methods',
            'Use SCREAMING_SNAKE_CASE for constants',
            'Prefix interfaces with I (optional, project-dependent)',
            'Suffix type guards with is (e.g., isUser)'
        ],
        common_patterns=[
            'Discriminated unions for reducers/state',
            'Builder pattern with method chaining',
            'Dependency injection with interfaces',
            'Mapped types for transformations',
            'Conditional types for generic constraints',
            'Template literal types for string patterns'
        ],
        anti_patterns=[
            'Using any type',
            'Over-engineering types (avoid deeply nested generics)',
            'Mixing namespaces and ES modules',
            'Using non-null assertion (!) without checks',
            'Circular type references'
        ],
        tools=['read_file', 'write_file', 'edit_file', 'search_files', 'run_command'],
        file_patterns={
            'module': '{name}.ts',
            'type': '{name}.types.ts',
            'test': '{name}.test.ts',
            'config': 'tsconfig.json'
        },
        system_context="""
You are a TypeScript expert. You leverage the full power of the type system.
You write strictly typed code with comprehensive interfaces and generics.
You know when to use types vs interfaces, and you never use 'any'.
        """,
        validation_rules=[
            'Run tsc --noEmit for type checking',
            'Run eslint with @typescript-eslint',
            'Run tests with ts-jest or vitest'
        ]
    ),
    
    # Frameworks
    # -------------------------------------------------------------------------
    
    'django': SkillModule(
        skill_id='django',
        name='Django Web Framework',
        category='framework',
        description='Django for building robust web applications and APIs',
        expertise_level='expert',
        best_practices=[
            'Use class-based views for complex logic',
            'Keep business logic in models or services, not views',
            'Use Django ORM effectively, avoid raw SQL when possible',
            'Write custom managers for reusable query logic',
            'Use Django signals sparingly (they create implicit behavior)',
            'Implement proper user authentication and authorization',
            'Use Django REST Framework for APIs',
            'Write comprehensive tests with TestCase',
            'Use migrations for all schema changes',
            'Follow MVT (Model-View-Template) separation'
        ],
        coding_standards=[
            'PEP 8 for Python code',
            'Organize apps by domain/feature',
            'Use Django shortcuts (get_object_or_404, redirect)',
            'Name views descriptively (e.g., UserCreateView)',
            'Use reverse() for URL resolution'
        ],
        common_patterns=[
            'Service layer pattern for business logic',
            'Repository pattern for data access',
            'Mixin classes for shared view behavior',
            'Custom middleware for cross-cutting concerns',
            'Celery for background tasks',
            'Redis for caching and sessions'
        ],
        anti_patterns=[
            'Fat views with business logic',
            'Using signals for core business logic',
            'N+1 query problems (use select_related, prefetch_related)',
            'Hardcoding URLs in templates or views',
            'Ignoring CSRF protection'
        ],
        tools=['read_file', 'write_file', 'edit_file', 'search_files', 'run_command'],
        file_patterns={
            'model': '{app}/models.py',
            'view': '{app}/views.py',
            'url': '{app}/urls.py',
            'serializer': '{app}/serializers.py',
            'test': '{app}/tests.py',
            'admin': '{app}/admin.py'
        },
        system_context="""
You are a Django expert. You build secure, scalable web applications following Django best practices.
You understand ORM optimization, middleware, and the full request/response lifecycle.
        """,
        validation_rules=[
            'Run python manage.py check',
            'Run python manage.py test',
            'Run migrations check',
            'Validate with django-stubs for type checking'
        ]
    ),
    
    'react': SkillModule(
        skill_id='react',
        name='React Frontend Development',
        category='framework',
        description='React with hooks, modern patterns, and performance optimization',
        expertise_level='expert',
        best_practices=[
            'Use functional components with hooks over class components',
            'Custom hooks for reusable logic',
            'Use React.memo for expensive renders',
            'Use useCallback for function props to child components',
            'Use useMemo for expensive computations',
            'Keep components small and focused (Single Responsibility)',
            'Prop drilling is a code smell - use Context or state management',
            'Use key prop correctly in lists',
            'Handle loading, error, and empty states',
            'Use TypeScript for type safety'
        ],
        coding_standards=[
            'Component names in PascalCase',
            'Hook names start with use',
            'Custom hook files: use{Feature}.ts',
            'Component files: {ComponentName}.tsx',
            'Co-locate tests: {ComponentName}.test.tsx',
            'One component per file (mostly)'
        ],
        common_patterns=[
            'Container/Presentational component split',
            'Compound components for flexible APIs',
            'Render props (less common now, prefer hooks)',
            'Higher-Order Components (HOCs) for cross-cutting concerns',
            'State management with Zustand, Redux Toolkit, or Context',
            'React Query for server state'
        ],
        anti_patterns=[
            'Mutating state directly',
            'Using useEffect when not needed',
            'Creating components inside render',
            'Missing dependency arrays in hooks',
            'Using index as key in lists',
            'Prop drilling through many levels'
        ],
        tools=['read_file', 'write_file', 'edit_file', 'search_files', 'run_command'],
        file_patterns={
            'component': '{ComponentName}.tsx',
            'hook': 'use{Feature}.ts',
            'test': '{ComponentName}.test.tsx',
            'style': '{ComponentName}.module.css'
        },
        system_context="""
You are a React expert. You build performant, accessible, and maintainable UI components.
You master hooks, patterns, and modern state management.
        """,
        validation_rules=[
            'Run eslint with react-hooks plugin',
            'Run jest/react-testing-library tests',
            'Type check with tsc'
        ]
    ),
    
    # DevOps / Infrastructure
    # -------------------------------------------------------------------------
    
    'docker': SkillModule(
        skill_id='docker',
        name='Docker & Containerization',
        category='devops',
        description='Docker, Docker Compose, and container best practices',
        expertise_level='expert',
        best_practices=[
            'Use multi-stage builds for smaller images',
            'Run containers as non-root user',
            'Use specific image tags, never latest',
            'Minimize layers (combine RUN commands)',
            'Use .dockerignore to reduce build context',
            'Health checks in Dockerfile',
            'Proper signal handling (PID 1)',
            'Separate build and runtime dependencies'
        ],
        coding_standards=[
            'Use official base images when possible',
            'Alpine or distroless for minimal attack surface',
            'Label images with metadata'
        ],
        common_patterns=[
            'Multi-stage builds',
            'Layer caching optimization',
            'Docker Compose for local development',
            'Sidecar containers',
            'Init containers pattern'
        ],
        anti_patterns=[
            'Running as root',
            'Using latest tag',
            'Storing secrets in images',
            'Large build contexts',
            'Ignoring layer caching'
        ],
        tools=['read_file', 'write_file', 'edit_file', 'search_files', 'run_command'],
        file_patterns={
            'dockerfile': 'Dockerfile',
            'compose': 'docker-compose.yml',
            'ignore': '.dockerignore'
        },
        system_context="""
You are a Docker expert. You build secure, efficient, and production-ready containers.
You understand image optimization, multi-stage builds, and container security.
        """,
        validation_rules=[
            'Run docker build to verify Dockerfile',
            'Run hadolint for Dockerfile linting',
            'Check for security issues with trivy'
        ]
    ),
    
    'devops': SkillModule(
        skill_id='devops',
        name='DevOps & CI/CD',
        category='devops',
        description='CI/CD pipelines, infrastructure as code, and deployment automation',
        expertise_level='expert',
        best_practices=[
            'Infrastructure as Code (Terraform, Pulumi, CloudFormation)',
            'GitOps for deployment workflows',
            'Immutable infrastructure',
            'Automated testing in CI pipeline',
            'Blue-green or canary deployments',
            'Comprehensive monitoring and alerting',
            'Secrets management (Vault, AWS Secrets Manager)',
            'Version control for all infrastructure code'
        ],
        coding_standards=[
            'Use semantic versioning for artifacts',
            'Tag all releases',
            'Document deployment procedures',
            'Use environment-specific configs'
        ],
        common_patterns=[
            'GitHub Actions / GitLab CI / Jenkins pipelines',
            'Terraform modules for reusable infrastructure',
            'Ansible for configuration management',
            'Kubernetes manifests with Helm',
            'ArgoCD for GitOps'
        ],
        anti_patterns=[
            'Manual production changes',
            'Secrets in version control',
            'Deploying without tests',
            'Single environment setup',
            'No rollback strategy'
        ],
        tools=['read_file', 'write_file', 'edit_file', 'search_files', 'run_command'],
        file_patterns={
            'workflow': '.github/workflows/{name}.yml',
            'terraform': 'terraform/{name}.tf',
            'ansible': 'ansible/{name}.yml',
            'k8s': 'k8s/{name}.yaml'
        },
        system_context="""
You are a DevOps expert. You design and implement robust CI/CD pipelines and infrastructure.
You follow GitOps, automate everything, and prioritize reliability and security.
        """,
        validation_rules=[
            'Validate YAML syntax',
            'Run terraform plan for infrastructure',
            'Lint CI/CD configurations'
        ]
    ),
    
    # Databases
    # -------------------------------------------------------------------------
    
    'postgresql': SkillModule(
        skill_id='postgresql',
        name='PostgreSQL Database',
        category='database',
        description='PostgreSQL design, optimization, and administration',
        expertise_level='expert',
        best_practices=[
            'Use appropriate data types (avoid text for everything)',
            'Create indexes for frequently queried columns',
            'Use EXPLAIN ANALYZE for query optimization',
            'Normalize to 3NF, denormalize only when needed',
            'Use transactions for atomic operations',
            'Implement proper constraints (NOT NULL, CHECK, FOREIGN KEY)',
            'Use connection pooling (PgBouncer)',
            'Regular VACUUM and ANALYZE'
        ],
        coding_standards=[
            'Use snake_case for table and column names',
            'Plural table names (users, not user)',
            'Primary key always named id',
            'Foreign key named {table}_id',
            'Timestamps: created_at, updated_at'
        ],
        common_patterns=[
            'JSONB for semi-structured data',
            'Partial indexes for filtered queries',
            'Materialized views for complex reports',
            'Partitioning for large tables',
            'Full-text search with tsvector'
        ],
        anti_patterns=[
            'N+1 queries',
            'Missing indexes on foreign keys',
            'Storing sensitive data unencrypted',
            'Using SELECT * in production',
            'Not handling connection limits'
        ],
        tools=['read_file', 'write_file', 'edit_file', 'search_files', 'run_command'],
        file_patterns={
            'migration': 'migrations/{timestamp}_{name}.sql',
            'schema': 'schema.sql',
            'seed': 'seeds/{name}.sql'
        },
        system_context="""
You are a PostgreSQL expert. You design efficient schemas, write optimized queries,
and understand indexing, partitioning, and administration deeply.
        """,
        validation_rules=[
            'Check SQL syntax',
            'Review query plans',
            'Validate migration files'
        ]
    ),
    
    # Architecture / Concepts
    # -------------------------------------------------------------------------
    
    'system_design': SkillModule(
        skill_id='system_design',
        name='System Design & Architecture',
        category='concept',
        description='Designing scalable, reliable, and maintainable systems',
        expertise_level='master',
        best_practices=[
            'Design for failure (circuit breakers, retries, fallbacks)',
            'Choose consistency model based on requirements',
            'Use async processing for non-critical paths',
            'Implement proper caching strategies',
            'Design APIs with versioning from the start',
            'Use event-driven architecture for decoupling',
            'Implement proper logging, metrics, and tracing',
            'Security by design (least privilege, encryption)'
        ],
        coding_standards=[
            'Document architectural decisions (ADRs)',
            'Use C4 model or similar for documentation',
            'Define clear service boundaries',
            'API-first design with OpenAPI/Swagger'
        ],
        common_patterns=[
            'Microservices with API Gateway',
            'Event Sourcing and CQRS',
            'Saga pattern for distributed transactions',
            'Strangler Fig pattern for migrations',
            'Bulkhead pattern for isolation',
            'Rate limiting and throttling'
        ],
        anti_patterns=[
            'Distributed monolith',
            'Synchronous calls between microservices',
            'Shared databases between services',
            'Ignoring network latency',
            'Over-engineering simple problems'
        ],
        tools=['read_file', 'write_file', 'edit_file', 'search_files', 'run_command'],
        file_patterns={
            'adr': 'docs/adr/{number:04d}-{name}.md',
            'diagram': 'docs/diagrams/{name}.puml',
            'api_spec': 'docs/api/{name}.yaml'
        },
        system_context="""
You are a System Architect. You design systems that scale, considering trade-offs
between consistency, availability, partition tolerance, cost, and complexity.
        """,
        validation_rules=[
            'Review against CAP theorem requirements',
            'Check for single points of failure',
            'Validate security considerations'
        ]
    ),
    
    'security': SkillModule(
        skill_id='security',
        name='Application Security',
        category='concept',
        description='Secure coding practices, threat modeling, and vulnerability assessment',
        expertise_level='expert',
        best_practices=[
            'Never trust user input - validate and sanitize everything',
            'Use parameterized queries to prevent SQL injection',
            'Implement proper authentication (OAuth 2.0, JWT)',
            'Use HTTPS everywhere',
            'Implement rate limiting',
            'Hash passwords with bcrypt/Argon2',
            'Use Content Security Policy headers',
            'Regular dependency scanning (Snyk, Dependabot)',
            'Principle of least privilege for all access'
        ],
        coding_standards=[
            'OWASP Top 10 compliance',
            'CWE awareness in code review',
            'Security-focused code review checklist'
        ],
        common_patterns=[
            'Defense in depth',
            'Zero trust architecture',
            'Secrets management',
            'Input validation layers',
            'Audit logging for sensitive operations'
        ],
        anti_patterns=[
            'Storing passwords in plain text',
            'Ignoring security headers',
            'Disabling CSRF protection',
            'Trusting client-side validation',
            'Hardcoding secrets in code'
        ],
        tools=['read_file', 'write_file', 'edit_file', 'search_files', 'run_command'],
        file_patterns={
            'policy': 'security/{name}.md',
            'threat_model': 'security/threat-models/{name}.md'
        },
        system_context="""
You are a Security Engineer. You write secure code, identify vulnerabilities,
and implement defense-in-depth strategies. You think like an attacker.
        """,
        validation_rules=[
            'Run static analysis (bandit, semgrep)',
            'Check for hardcoded secrets',
            'Review against OWASP checklist'
        ]
    )
}


class SkillRegistry:
    """Registry for managing skill modules."""
    
    def __init__(self, custom_skills_dir: Optional[Path] = None):
        self.skills: Dict[str, SkillModule] = {**SKILL_LIBRARY}
        self.custom_skills_dir = custom_skills_dir
        
        if custom_skills_dir:
            self._load_custom_skills()
    
    def _load_custom_skills(self):
        """Load custom skill definitions from directory."""
        if not self.custom_skills_dir.exists():
            return
        
        for skill_file in self.custom_skills_dir.glob('*.json'):
            try:
                data = json.loads(skill_file.read_text())
                skill = SkillModule.from_dict(data)
                self.skills[skill.skill_id] = skill
            except Exception as e:
                print(f"Warning: Could not load skill from {skill_file}: {e}")
    
    def get_skill(self, skill_id: str) -> Optional[SkillModule]:
        """Get a skill by ID."""
        return self.skills.get(skill_id)
    
    def list_skills(self, category: Optional[str] = None) -> List[SkillModule]:
        """List all skills, optionally filtered by category."""
        skills = list(self.skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return skills
    
    def get_skills_by_category(self) -> Dict[str, List[SkillModule]]:
        """Group skills by category."""
        result: Dict[str, List[SkillModule]] = {}
        for skill in self.skills.values():
            result.setdefault(skill.category, []).append(skill)
        return result
    
    def add_custom_skill(self, skill: SkillModule):
        """Add a custom skill."""
        self.skills[skill.skill_id] = skill
        
        if self.custom_skills_dir:
            self.custom_skills_dir.mkdir(parents=True, exist_ok=True)
            skill_file = self.custom_skills_dir / f"{skill.skill_id}.json"
            skill_file.write_text(json.dumps(skill.to_dict(), indent=2))
    
    def get_combined_context(self, skill_ids: List[str]) -> str:
        """Get combined system context for multiple skills."""
        contexts = []
        for skill_id in skill_ids:
            skill = self.skills.get(skill_id)
            if skill and skill.system_context:
                contexts.append(f"## {skill.name}\n{skill.system_context}")
        
        return "\n\n".join(contexts)
    
    def get_combined_best_practices(self, skill_ids: List[str]) -> List[str]:
        """Get combined best practices for multiple skills."""
        practices = []
        for skill_id in skill_ids:
            skill = self.skills.get(skill_id)
            if skill:
                practices.extend([f"[{skill.name}] {p}" for p in skill.best_practices])
        return practices
    
    def get_allowed_tools(self, skill_ids: List[str]) -> List[str]:
        """Get union of allowed tools for multiple skills."""
        tools = set()
        for skill_id in skill_ids:
            skill = self.skills.get(skill_id)
            if skill:
                tools.update(skill.tools)
        return list(tools)


# Global registry instance
_skill_registry: Optional[SkillRegistry] = None


def get_skill_registry(custom_dir: Optional[Path] = None) -> SkillRegistry:
    """Get or create the global skill registry."""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry(custom_dir)
    return _skill_registry


def reset_skill_registry():
    """Reset the global skill registry."""
    global _skill_registry
    _skill_registry = None
