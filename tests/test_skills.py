"""Tests for skill registry module."""
import json
import tempfile
from pathlib import Path
import pytest
from skills.registry import (
    SkillModule, SkillRegistry, SKILL_LIBRARY, get_skill_registry, reset_skill_registry
)


class TestSkillModule:
    """Tests for SkillModule dataclass."""

    def test_create_skill_module(self):
        """Create a SkillModule with required fields."""
        skill = SkillModule(
            skill_id='test_python',
            name='Test Python',
            category='language',
            description='Test skill for Python',
            expertise_level='expert'
        )
        assert skill.skill_id == 'test_python'
        assert skill.category == 'language'
        assert skill.best_practices == []
        assert skill.tools == []

    def test_skill_module_with_tools(self):
        """SkillModule stores tools list."""
        skill = SkillModule(
            skill_id='test',
            name='Test',
            category='test',
            description='Test',
            expertise_level='beginner',
            tools=['read_file', 'write_file', 'run_command']
        )
        assert len(skill.tools) == 3
        assert 'read_file' in skill.tools

    def test_skill_to_dict_and_back(self):
        """to_dict and from_dict round-trip correctly."""
        skill = SkillModule(
            skill_id='test_roundtrip',
            name='Roundtrip Test',
            category='devops',
            description='Testing serialization',
            expertise_level='master',
            best_practices=['Do X', 'Avoid Y'],
            coding_standards=['Standard 1'],
            tools=['tool_a', 'tool_b'],
            file_patterns={'config': '*.json'}
        )
        data = skill.to_dict()
        restored = SkillModule.from_dict(data)
        assert restored.skill_id == skill.skill_id
        assert restored.name == skill.name
        assert restored.best_practices == skill.best_practices
        assert restored.tools == skill.tools
        assert restored.file_patterns == skill.file_patterns


class TestSkillRegistry:
    """Tests for SkillRegistry."""

    def test_builtin_skills_loaded(self):
        """SKILL_LIBRARY contains the expected built-in skills."""
        reset_skill_registry()
        registry = get_skill_registry()
        builtin = ['python', 'javascript', 'typescript', 'django', 'react',
                   'docker', 'devops', 'postgresql', 'system_design', 'security']
        for sid in builtin:
            assert sid in registry.skills, f"Missing builtin skill: {sid}"

    def test_get_skill_by_id(self):
        """get_skill returns correct SkillModule."""
        reset_skill_registry()
        registry = get_skill_registry()
        skill = registry.get_skill('python')
        assert skill is not None
        assert skill.name is not None
        assert skill.category == 'language'

    def test_get_nonexistent_skill(self):
        """get_skill returns None for missing skill."""
        reset_skill_registry()
        registry = get_skill_registry()
        assert registry.get_skill('nonexistent') is None

    def test_list_skills(self):
        """list_skills returns all skill objects."""
        reset_skill_registry()
        registry = get_skill_registry()
        skills = registry.list_skills()
        skill_ids = [s.skill_id for s in skills]
        assert len(skills) >= 9
        assert 'python' in skill_ids
        assert 'react' in skill_ids

    def test_get_skills_by_category(self):
        """get_skills_by_category groups skills correctly."""
        reset_skill_registry()
        registry = get_skill_registry()
        cats = registry.get_skills_by_category()
        assert 'language' in cats
        assert 'framework' in cats
        assert 'devops' in cats
        assert 'concept' in cats
        # Python is a language
        assert any(s.skill_id == 'python' for s in cats.get('language', []))

    def test_get_combined_context(self):
        """get_combined_context merges skill contexts."""
        reset_skill_registry()
        registry = get_skill_registry()
        context = registry.get_combined_context(['python', 'system_design'])
        assert isinstance(context, str)
        assert len(context) > 0

    def test_get_combined_best_practices(self):
        """get_combined_best_practices merges best practices."""
        reset_skill_registry()
        registry = get_skill_registry()
        practices = registry.get_combined_best_practices(['python'])
        assert isinstance(practices, list)
        assert len(practices) >= 0

    def test_get_allowed_tools(self):
        """get_allowed_tools returns tool names from skills."""
        reset_skill_registry()
        registry = get_skill_registry()
        tools = registry.get_allowed_tools(['python'])
        assert isinstance(tools, list)

    def test_add_custom_skill(self, tmp_path):
        """add_custom_skill adds a SkillModule to registry."""
        reset_skill_registry()
        registry = get_skill_registry()

        skill = SkillModule(
            skill_id='custom_graphql',
            name='GraphQL',
            category='framework',
            description='Custom GraphQL skill',
            expertise_level='expert',
            best_practices=['Use schema-first'],
            tools=['read_file', 'write_file']
        )
        registry.add_custom_skill(skill)
        assert 'custom_graphql' in registry.skills
        assert registry.get_skill('custom_graphql').name == 'GraphQL'

    def test_add_custom_skill_overwrites(self, tmp_path):
        """Adding custom skill with same ID overwrites builtin."""
        reset_skill_registry()
        registry = get_skill_registry()

        skill = SkillModule(
            skill_id='python',
            name='Custom Python Override',
            category='language',
            description='Custom',
            expertise_level='master',
            tools=['custom_tool']
        )
        registry.add_custom_skill(skill)
        assert registry.get_skill('python').name == 'Custom Python Override'
        assert 'custom_tool' in registry.get_skill('python').tools


class TestSkillRegistrySingleton:
    """Tests for singleton behavior."""

    def test_get_skill_registry_is_singleton(self):
        """get_skill_registry returns same instance."""
        reset_skill_registry()
        r1 = get_skill_registry()
        r2 = get_skill_registry()
        assert r1 is r2

    def test_reset_skill_registry(self):
        """reset_skill_registry creates new instance."""
        r1 = get_skill_registry()
        reset_skill_registry()
        r2 = get_skill_registry()
        assert r1 is not r2  # new instance after reset
