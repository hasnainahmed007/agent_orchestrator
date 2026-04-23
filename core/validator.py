"""Validator for agent code changes."""
import subprocess
from pathlib import Path
from typing import Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of validation."""
    success: bool
    message: str
    errors: List[str]
    warnings: List[str]
    files_checked: List[str]
    
    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'message': self.message,
            'errors': self.errors,
            'warnings': self.warnings,
            'files_checked': self.files_checked
        }


class Validator:
    """Validates code changes before commit."""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.php_executable = self._find_php()
    
    def _find_php(self) -> Optional[str]:
        """Find PHP executable."""
        # Common paths on Windows
        possible_paths = [
            r'C:\xampp\php\php.exe',
            r'C:\php\php.exe',
            'php'
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, '-v'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return path
            except:
                continue
        
        return None
    
    def validate_all(self, files: List[str]) -> ValidationResult:
        """Run all validations on files.
        
        Args:
            files: List of relative file paths to validate
            
        Returns:
            ValidationResult with details
        """
        errors = []
        warnings = []
        
        # Separate files by type
        php_files = [f for f in files if f.endswith('.php')]
        blade_files = [f for f in files if f.endswith('.blade.php')]
        
        # Validate PHP syntax
        for php_file in php_files:
            success, error = self._validate_php_syntax(php_file)
            if not success:
                errors.append(f"Syntax error in {php_file}: {error}")
        
        # Validate Blade templates
        for blade_file in blade_files:
            success, error = self._validate_blade_syntax(blade_file)
            if not success:
                errors.append(f"Blade error in {blade_file}: {error}")
        
        # Run tests if any PHP files changed
        if php_files:
            test_result = self._run_tests()
            if not test_result.success:
                errors.extend(test_result.errors)
            warnings.extend(test_result.warnings)
        
        success = len(errors) == 0
        message = "All validations passed" if success else f"Found {len(errors)} errors"
        
        return ValidationResult(
            success=success,
            message=message,
            errors=errors,
            warnings=warnings,
            files_checked=files
        )
    
    def _validate_php_syntax(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Check PHP syntax for errors."""
        if not self.php_executable:
            return True, None  # Skip if PHP not found
        
        full_path = self.project_path / file_path
        if not full_path.exists():
            return True, None  # New file, can't validate syntax yet
        
        try:
            result = subprocess.run(
                [self.php_executable, '-l', str(full_path)],
                capture_output=True,
                text=True,
                timeout=10
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
        
        # Basic checks
        # Count opening and closing directives
        open_directives = content.count('@if') + content.count('@foreach') + content.count('@for')
        close_directives = content.count('@endif') + content.count('@endforeach') + content.count('@endfor')
        
        # Count opening and closing braces
        open_braces = content.count('{{')
        close_braces = content.count('}}')
        
        issues = []
        
        if open_directives != close_directives:
            issues.append(f"Mismatched directives: {open_directives} open, {close_directives} close")
        
        if open_braces != close_braces:
            issues.append(f"Mismatched braces: {open_braces} open, {close_braces} close")
        
        # Check for common mistakes
        if '{{!' in content and '!}}' not in content:
            issues.append("Unclosed raw echo directive")
        
        if issues:
            return False, '; '.join(issues)
        
        return True, None
    
    def _run_tests(self) -> ValidationResult:
        """Run Laravel test suite."""
        if not self.php_executable:
            return ValidationResult(
                success=True,
                message="PHP not found, skipping tests",
                errors=[],
                warnings=["PHP executable not found, tests skipped"],
                files_checked=[]
            )
        
        artisan_path = self.project_path / 'artisan'
        if not artisan_path.exists():
            return ValidationResult(
                success=True,
                message="Artisan not found, skipping tests",
                errors=[],
                warnings=["Artisan not found"],
                files_checked=[]
            )
        
        try:
            result = subprocess.run(
                [self.php_executable, str(artisan_path), 'test', '--no-interaction'],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.project_path)
            )
            
            if result.returncode == 0:
                return ValidationResult(
                    success=True,
                    message="All tests passed",
                    errors=[],
                    warnings=[],
                    files_checked=[]
                )
            else:
                # Parse test output for failures
                errors = []
                output = result.stdout + result.stderr
                
                # Simple parsing - could be improved
                for line in output.split('\n'):
                    if 'FAIL' in line or 'Error' in line or 'Failed' in line:
                        errors.append(line.strip())
                
                if not errors:
                    errors.append("Tests failed (see output)")
                
                return ValidationResult(
                    success=False,
                    message=f"Tests failed with {len(errors)} errors",
                    errors=errors[:10],  # Limit errors
                    warnings=[],
                    files_checked=[]
                )
        
        except subprocess.TimeoutExpired:
            return ValidationResult(
                success=False,
                message="Tests timed out",
                errors=["Test execution exceeded 120 seconds"],
                warnings=[],
                files_checked=[]
            )
        except Exception as e:
            return ValidationResult(
                success=False,
                message=f"Failed to run tests: {e}",
                errors=[str(e)],
                warnings=[],
                files_checked=[]
            )
    
    def run_artisan_command(self, command: str) -> Tuple[bool, str]:
        """Run an artisan command.
        
        Args:
            command: Artisan command (e.g., 'migrate:status')
            
        Returns:
            Tuple of (success, output)
        """
        if not self.php_executable:
            return False, "PHP executable not found"
        
        artisan_path = self.project_path / 'artisan'
        if not artisan_path.exists():
            return False, "Artisan not found"
        
        try:
            result = subprocess.run(
                [self.php_executable, str(artisan_path), command],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_path)
            )
            
            output = result.stdout + result.stderr
            return result.returncode == 0, output
        
        except Exception as e:
            return False, str(e)
    
    def check_composer_valid(self) -> bool:
        """Check if composer.json is valid."""
        composer_json = self.project_path / 'composer.json'
        if not composer_json.exists():
            return True
        
        try:
            import json
            json.loads(composer_json.read_text())
            return True
        except:
            return False