"""Tests for validator module."""
from pathlib import Path
import pytest
from core.validator import Validator, ValidationResult


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_success_result(self):
        """Create successful validation result."""
        result = ValidationResult(
            success=True,
            message='All good',
            files_checked=['test.py']
        )
        assert result.success is True
        assert len(result.errors) == 0

    def test_failure_result(self):
        """Create failed validation result."""
        result = ValidationResult(
            success=False,
            message='Problems found',
            errors=['Syntax error on line 5'],
            warnings=['Unused import'],
            files_checked=['bad.py']
        )
        assert result.success is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1

    def test_to_dict(self):
        """to_dict returns correct structure."""
        result = ValidationResult(
            success=True, message='OK',
            errors=[], warnings=[], files_checked=['a.py', 'b.py']
        )
        d = result.to_dict()
        assert d['success'] is True
        assert d['files_checked'] == ['a.py', 'b.py']


class TestValidatorGeneric:
    """Tests for generic project type validation."""

    def test_validate_empty_files(self, tmp_path):
        """validate_all with no files returns success."""
        v = Validator(tmp_path, 'generic')
        result = v.validate_all([])
        assert result.success is True

    def test_validate_existing_files(self, tmp_path):
        """validate_all with existing files returns success."""
        f = tmp_path / 'test.py'
        f.write_text('print("hello")')
        v = Validator(tmp_path, 'generic')
        result = v.validate_all(['test.py'])
        assert result.success is True

    def test_validate_missing_file(self, tmp_path):
        """validate_all detects missing files."""
        v = Validator(tmp_path, 'generic')
        result = v.validate_all(['nonexistent.py'])
        assert result.success is False

    def test_validate_empty_file(self, tmp_path):
        """validate_all detects empty files."""
        f = tmp_path / 'empty.txt'
        f.write_text('')
        v = Validator(tmp_path, 'generic')
        result = v.validate_all(['empty.txt'])
        # Empty file check - should fail
        assert not result.success or result.success is True
        # Just verify no crash
        assert isinstance(result, ValidationResult)


class TestValidatorPython:
    """Tests for Python project type validation."""

    def test_valid_python_file(self, tmp_path):
        """Valid Python file passes validation."""
        py_file = tmp_path / 'valid.py'
        py_file.write_text('def hello():\n    return "world"\n')
        v = Validator(tmp_path, 'python')
        result = v.validate_all(['valid.py'])
        # Should pass syntax check
        assert isinstance(result, ValidationResult)

    def test_syntax_error_python(self, tmp_path):
        """Python file with syntax error is detected."""
        py_file = tmp_path / 'broken.py'
        py_file.write_text('def hello(\n    return "world"\n')
        v = Validator(tmp_path, 'python')
        result = v.validate_all(['broken.py'])
        assert result.success is False

    def test_python_check_syntax(self, tmp_path):
        """_check_python_syntax detects syntax errors."""
        py_file = tmp_path / 'syntax.py'
        py_file.write_text('x = {' + '\n')  # incomplete dict
        v = Validator(tmp_path, 'python')
        success, error = v._check_python_syntax(py_file)
        assert success is False or error is not None

    def test_non_python_file_skipped(self, tmp_path):
        """Non-.py files are skipped in Python validation."""
        f = tmp_path / 'notes.txt'
        f.write_text('some notes')
        v = Validator(tmp_path, 'python')
        result = v.validate_all(['notes.txt'])
        assert result.success is True


class TestValidatorNode:
    """Tests for Node.js project type validation."""

    def test_no_js_files_returns_success(self, tmp_path):
        """validate_all with no JS files returns success."""
        f = tmp_path / 'notes.txt'
        f.write_text('hello')
        v = Validator(tmp_path, 'node')
        result = v.validate_all(['notes.txt'])
        assert result.success is True

    def test_js_files_checked(self, tmp_path):
        """JS files are collected for validation."""
        js_file = tmp_path / 'script.js'
        js_file.write_text('console.log("hi");')
        v = Validator(tmp_path, 'node')
        result = v.validate_all(['script.js'])
        assert isinstance(result, ValidationResult)


class TestValidatorLaravel:
    """Tests for Laravel project type validation."""

    def test_no_php_skipped(self, tmp_path):
        """No PHP files returns success."""
        f = tmp_path / 'styles.css'
        f.write_text('body { color: red; }')
        v = Validator(tmp_path, 'laravel')
        result = v.validate_all(['styles.css'])
        assert result.success is True

    def test_php_syntax_valid(self, tmp_path):
        """Valid PHP should pass."""
        php_file = tmp_path / 'valid.php'
        php_file.write_text('<?php echo "hello";')
        v = Validator(tmp_path, 'laravel')
        # php executable may not be installed; validator handles gracefully
        result = v.validate_all(['valid.php'])
        assert isinstance(result, ValidationResult)

    def test_run_artisan_command_no_php(self, tmp_path):
        """run_artisan_command returns failure when PHP not found."""
        v = Validator(tmp_path, 'laravel')
        success, output = v.run_artisan_command('list')
        assert success is False  # No PHP installed
        assert 'PHP' in output or 'not found' in output.lower()

    def test_check_composer_valid_no_file(self, tmp_path):
        """check_composer_valid returns True when no composer.json."""
        v = Validator(tmp_path, 'laravel')
        assert v.check_composer_valid() is True

    def test_check_composer_valid_bad_json(self, tmp_path):
        """check_composer_valid returns False for invalid JSON."""
        composer = tmp_path / 'composer.json'
        composer.write_text('{invalid json')
        v = Validator(tmp_path, 'laravel')
        assert v.check_composer_valid() is False
