"""Tests for configuration module."""
import os
import tempfile
import subprocess
from pathlib import Path
import pytest
from config.settings import Config


class TestConfigValidation:
    """Tests for Config.validate()."""

    def test_missing_api_key_returns_error(self, monkeypatch):
        """Validate returns error when OPENAI_API_KEY is placeholder."""
        monkeypatch.setattr(Config, 'OPENAI_API_KEY', 'your_openai_api_key_here')
        monkeypatch.setattr(Config, 'TELEGRAM_BOT_TOKEN', '')
        errors, _ = Config.validate()
        assert any('OPENAI_API_KEY' in e for e in errors)

    def test_valid_config_no_errors(self, monkeypatch, tmp_path):
        """Validate returns no errors with minimal valid config."""
        monkeypatch.setattr(Config, 'OPENAI_API_KEY', 'sk-test123')
        monkeypatch.setattr(Config, 'TELEGRAM_BOT_TOKEN', '')
        monkeypatch.setattr(Config, 'PROJECT_PATH', tmp_path / 'myproject')

        # Ensure project path exists
        Config.PROJECT_PATH.mkdir(parents=True, exist_ok=True)

        errors, warnings = Config.validate()
        assert len(errors) == 0

    def test_missing_telegram_token_is_warning(self, monkeypatch, tmp_path):
        """Missing TELEGRAM_BOT_TOKEN produces warning, not error."""
        monkeypatch.setattr(Config, 'OPENAI_API_KEY', 'sk-test123')
        monkeypatch.setattr(Config, 'TELEGRAM_BOT_TOKEN', 'your_telegram_bot_token_here')
        monkeypatch.setattr(Config, 'PROJECT_PATH', tmp_path / 'myproject')
        Config.PROJECT_PATH.mkdir(parents=True, exist_ok=True)

        errors, warnings = Config.validate()
        assert len(errors) == 0
        assert any('TELEGRAM_BOT_TOKEN' in w for w in warnings)

    def test_auto_init_git_repo(self, monkeypatch, tmp_path):
        """Validate auto-initializes git repo when missing."""
        project_dir = tmp_path / 'new-project'
        monkeypatch.setattr(Config, 'OPENAI_API_KEY', 'sk-test123')
        monkeypatch.setattr(Config, 'TELEGRAM_BOT_TOKEN', '')
        monkeypatch.setattr(Config, 'PROJECT_PATH', project_dir)

        errors, _ = Config.validate()
        assert len(errors) == 0
        assert (project_dir / '.git').exists()

    def test_ensure_directories_creates_all(self, monkeypatch, tmp_path):
        """ensure_directories creates all required directories."""
        base = tmp_path / 'orchestrator'
        monkeypatch.setattr(Config, 'BASE_DIR', base)
        Config.ensure_directories()
        assert (base / 'logs').exists()
        assert (base / 'state').exists()
        assert (base / 'skills' / 'custom').exists()

    def test_get_project_validation_config_python(self):
        """Returns python validation config."""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(Config, 'PROJECT_TYPE', 'python')
        cfg = Config.get_project_validation_config()
        assert cfg['php_enabled'] is False
        assert 'pytest' in cfg['test_command']

    def test_get_project_validation_config_node(self):
        """Returns node validation config."""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(Config, 'PROJECT_TYPE', 'node')
        cfg = Config.get_project_validation_config()
        assert cfg['blade_enabled'] is False
        assert 'npm' in cfg['test_command']

    def test_get_project_validation_config_generic(self):
        """Returns generic validation config."""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(Config, 'PROJECT_TYPE', 'generic')
        cfg = Config.get_project_validation_config()
        assert cfg['php_enabled'] is False
        assert cfg['test_command'] == ''


class TestConfigDefaults:
    """Tests for Config default values."""

    def test_default_project_type_is_generic(self):
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.delenv('PROJECT_TYPE', raising=False)
        from dotenv import load_dotenv
        # Config is imported at module level, but PROJECT_TYPE should have default
        assert Config.PROJECT_TYPE == 'generic'

    def test_default_main_branch_is_main(self):
        assert Config.MAIN_BRANCH == 'main'

    def test_default_agent_settings(self):
        assert Config.AGENT_VERBOSE is True
        assert Config.AGENT_MAX_ITERATIONS == 15
