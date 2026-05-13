"""Validator for agent code changes - dynamic per project type."""
import subprocess
from pathlib import Path
from typing import Tuple, List, Optional
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of validation."""
    success: bool
    message: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    files_checked: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'message': self.message,
            'errors': self.errors,
            'warnings': self.warnings,
            'files_checked': self.files_checked
        }


class Validator:
    """Validates code changes before commit, dispatching by project type."""

    def __init__(self, project_path: Path, project_type: str = 'generic'):
        self.project_path = Path(project_path)
        self.project_type = project_type

    def validate_all(self, files: List[str]) -> ValidationResult:
        """Run all validations on changed files."""
        if self.project_type == 'python':
            return self._validate_python(files)
        elif self.project_type == 'node':
            return self._validate_node(files)
        elif self.project_type == 'laravel':
            return self._validate_laravel(files)
        else:
            return self._validate_generic(files)

    # ── Generic validation ──────────────────────────────────────────

    def _validate_generic(self, files: List[str]) -> ValidationResult:
        """Generic validation - file existence and size checks."""
        errors = []
        for f in files:
            full_path = self.project_path / f
            if full_path.exists():
                size = full_path.stat().st_size
                if size == 0:
                    errors.append(f"Warning: {f} is empty")
            else:
                errors.append(f"File not found: {f}")

        success = len(errors) == 0
        return ValidationResult(
            success=success,
            message="All files exist and are non-empty" if success else f"Found {len(errors)} issues",
            errors=errors,
            files_checked=files
        )

    # ── Python validation ────────────────────────────────────────────

    def _validate_python(self, files: List[str]) -> ValidationResult:
        """Validate Python code changes."""
        errors = []
        warnings = []

        py_files = [f for f in files if f.endswith('.py')]

        for py_file in py_files:
            full_path = self.project_path / py_file
            if not full_path.exists():
                errors.append(f"File not found: {py_file}")
                continue

            success, error = self._check_python_syntax(full_path)
            if not success:
                errors.append(f"Syntax error in {py_file}: {error}")

        # Check imports if files changed
        if py_files:
            try:
                result = subprocess.run(
                    ['python', '-m', 'py_compile'] + [str(self.project_path / f) for f in py_files],
                    capture_output=True, text=True, timeout=30,
                    cwd=str(self.project_path)
                )
                if result.returncode != 0:
                    errors.append(f"Compile check failed: {result.stderr.strip()}")
            except FileNotFoundError:
                warnings.append("Python interpreter not found, skipped compile check")
            except Exception as e:
                errors.append(f"Compile check error: {e}")

        # Run tests if test files changed
        test_files = [f for f in py_files if 'test' in f.lower()]
        if test_files:
            try:
                result = subprocess.run(
                    ['pytest', '--tb=short', '-q'] + [str(self.project_path / f) for f in test_files],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(self.project_path)
                )
                if result.returncode != 0:
                    errors.append(f"Pytest failed:\n{result.stderr[:1000]}")
            except FileNotFoundError:
                warnings.append("pytest not found, skipped test run")
            except subprocess.TimeoutExpired:
                errors.append("Test execution timed out")
            except Exception as e:
                errors.append(f"Test execution error: {e}")

        success = len(errors) == 0
        return ValidationResult(
            success=success,
            message="Python validation passed" if success else f"Found {len(errors)} errors",
            errors=errors,
            warnings=warnings,
            files_checked=files
        )

    def _check_python_syntax(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Check Python file can be compiled."""
        try:
            code = file_path.read_text()
            compile(code, str(file_path), 'exec')
            return True, None
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, str(e)

    # ── Node.js validation ──────────────────────────────────────────

    def _validate_node(self, files: List[str]) -> ValidationResult:
        """Validate Node.js/TypeScript code changes."""
        errors = []
        warnings = []

        js_ts_files = [f for f in files if f.endswith(('.js', '.jsx', '.ts', '.tsx'))]

        if not js_ts_files:
            return ValidationResult(
                success=True, message="No JavaScript/TypeScript files to validate",
                files_checked=files
            )

        # Check file existence
        for f in js_ts_files:
            if not (self.project_path / f).exists():
                errors.append(f"File not found: {f}")

        # Run linter if available
        package_json = self.project_path / 'package.json'
        if package_json.exists():
            try:
                result = subprocess.run(
                    ['npm', 'run', 'lint', '--', '--no-error-on-unmatched-pattern', '--quiet']
                    + [str(self.project_path / f) for f in js_ts_files],
                    capture_output=True, text=True, timeout=60,
                    cwd=str(self.project_path)
                )
                if result.returncode != 0:
                    errors.append(f"Lint failed:\n{result.stderr.strip()[:1000]}")
            except FileNotFoundError:
                warnings.append("npm not found, skipped lint check")
            except subprocess.TimeoutExpired:
                warnings.append("Lint check timed out")
            except Exception as e:
                errors.append(f"Lint error: {e}")

        # Run tests if test files changed
        test_files = [f for f in js_ts_files if 'test' in f.lower() or 'spec' in f.lower()]
        if test_files and package_json.exists():
            try:
                result = subprocess.run(
                    ['npm', 'test', '--', '--silent'],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(self.project_path)
                )
                if result.returncode != 0:
                    errors.append(f"Tests failed:\n{result.stderr.strip()[:1000]}")
            except FileNotFoundError:
                warnings.append("npm not found, skipped test run")
            except subprocess.TimeoutExpired:
                errors.append("Test execution timed out")
            except Exception as e:
                errors.append(f"Test execution error: {e}")

        success = len(errors) == 0
        return ValidationResult(
            success=success,
            message="Node.js validation passed" if success else f"Found {len(errors)} errors",
            errors=errors,
            warnings=warnings,
            files_checked=files
        )

    # ── Laravel validation ──────────────────────────────────────────

    def _validate_laravel(self, files: List[str]) -> ValidationResult:
        """Validate Laravel/PHP code changes."""
        errors = []
        warnings = []

        php_files = [f for f in files if f.endswith('.php') and '.blade.php' not in f]
        blade_files = [f for f in files if f.endswith('.blade.php')]

        php_executable = self._find_php()

        # PHP syntax check
        for php_file in php_files:
            success, error = self._validate_php_syntax(php_file, php_executable)
            if not success:
                errors.append(f"Syntax error in {php_file}: {error}")

        # Blade syntax check
        for blade_file in blade_files:
            success, error = self._validate_blade_syntax(blade_file)
            if not success:
                errors.append(f"Blade error in {blade_file}: {error}")

        # Run tests if PHP files changed
        if php_files and php_executable:
            artisan_path = self.project_path / 'artisan'
            if artisan_path.exists():
                test_result = self._run_artisan_tests(php_executable, artisan_path)
                if not test_result.success:
                    errors.extend(test_result.errors)
                warnings.extend(test_result.warnings)
            else:
                warnings.append("Artisan not found, skipped tests")
        elif php_files and not php_executable:
            warnings.append("PHP executable not found, skipped tests")

        success = len(errors) == 0
        return ValidationResult(
            success=success,
            message="All validations passed" if success else f"Found {len(errors)} errors",
            errors=errors,
            warnings=warnings,
            files_checked=files
        )

    def _find_php(self) -> Optional[str]:
        """Find PHP executable."""
        possible_paths = [
            r'C:\xampp\php\php.exe',
            r'C:\php\php.exe',
            'php'
        ]
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, '-v'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return path
            except Exception:
                continue
        return None

    def _validate_php_syntax(self, file_path: str, php_executable: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Check PHP syntax for errors."""
        if not php_executable:
            return True, None

        full_path = self.project_path / file_path
        if not full_path.exists():
            return True, None

        try:
            result = subprocess.run(
                [php_executable, '-l', str(full_path)],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return False, result.stderr
            return True, None
        except subprocess.TimeoutExpired:
            return False, "Validation timeout"
        except Exception as e:
            return False, str(e)

    def _validate_blade_syntax(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Check Blade template syntax."""
        full_path = self.project_path / file_path
        if not full_path.exists():
            return True, None

        content = full_path.read_text()
        issues = []

        open_directives = content.count('@if') + content.count('@foreach') + content.count('@for')
        close_directives = content.count('@endif') + content.count('@endforeach') + content.count('@endfor')

        open_braces = content.count('{{')
        close_braces = content.count('}}')

        if open_directives != close_directives:
            issues.append(f"Mismatched directives: {open_directives} open, {close_directives} close")

        if open_braces != close_braces:
            issues.append(f"Mismatched braces: {open_braces} open, {close_braces} close")

        if '{{!' in content and '!}}' not in content:
            issues.append("Unclosed raw echo directive")

        if issues:
            return False, '; '.join(issues)
        return True, None

    def _run_artisan_tests(self, php_executable: str, artisan_path: Path) -> ValidationResult:
        """Run Laravel test suite."""
        try:
            result = subprocess.run(
                [php_executable, str(artisan_path), 'test', '--no-interaction'],
                capture_output=True, text=True, timeout=120,
                cwd=str(self.project_path)
            )

            if result.returncode == 0:
                return ValidationResult(
                    success=True, message="All tests passed",
                    errors=[], warnings=[], files_checked=[]
                )
            else:
                errors = []
                output = result.stdout + result.stderr
                for line in output.split('\n'):
                    if 'FAIL' in line or 'Error' in line or 'Failed' in line:
                        errors.append(line.strip())
                if not errors:
                    errors.append("Tests failed (see output)")

                return ValidationResult(
                    success=False,
                    message=f"Tests failed with {len(errors)} errors",
                    errors=errors[:10],
                    warnings=[], files_checked=[]
                )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                success=False, message="Tests timed out",
                errors=["Test execution exceeded 120 seconds"],
                warnings=[], files_checked=[]
            )
        except Exception as e:
            return ValidationResult(
                success=False, message=f"Failed to run tests: {e}",
                errors=[str(e)], warnings=[], files_checked=[]
            )

    def run_artisan_command(self, command: str) -> Tuple[bool, str]:
        """Run an artisan command (Laravel only)."""
        php_executable = self._find_php()
        if not php_executable:
            return False, "PHP executable not found"

        artisan_path = self.project_path / 'artisan'
        if not artisan_path.exists():
            return False, "Artisan not found"

        try:
            result = subprocess.run(
                [php_executable, str(artisan_path), command],
                capture_output=True, text=True, timeout=30,
                cwd=str(self.project_path)
            )
            output = result.stdout + result.stderr
            return result.returncode == 0, output
        except Exception as e:
            return False, str(e)

    def check_composer_valid(self) -> bool:
        """Check if composer.json is valid (Laravel only)."""
        composer_json = self.project_path / 'composer.json'
        if not composer_json.exists():
            return True
        try:
            import json
            json.loads(composer_json.read_text())
            return True
        except Exception:
            return False
