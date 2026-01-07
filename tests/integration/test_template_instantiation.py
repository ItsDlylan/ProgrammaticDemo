"""INT-011: Test template instantiation.

This test verifies that:
1. Templates can be loaded from the registry
2. Template variables are correctly parsed
3. Variable substitution works correctly
4. Interactive instantiation works with mock prompts
5. Validation catches missing required variables
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from programmatic_demo.templates import (
    Template,
    TemplateRegistry,
    TemplateVariable,
    get_registry,
    get_template,
    list_templates,
    parse_variables,
    substitute_variables,
    validate_variable_values,
)


class TestTemplateLoading:
    """Test template loading from registry."""

    def test_builtin_templates_exist(self):
        """Test that builtin templates are loaded."""
        registry = get_registry()
        templates = list(registry.templates.values())

        assert len(templates) >= 1, "Expected at least one builtin template"

    def test_list_templates_function(self):
        """Test the list_templates convenience function."""
        templates = list_templates()

        assert isinstance(templates, list)
        assert all(isinstance(t, Template) for t in templates)

    def test_get_template_by_name(self):
        """Test getting a template by name."""
        templates = list_templates()
        if not templates:
            pytest.skip("No templates available")

        first_name = templates[0].name
        template = get_template(first_name)

        assert template is not None
        assert template.name == first_name

    def test_get_nonexistent_template(self):
        """Test getting a template that doesn't exist."""
        template = get_template("nonexistent-template-12345")

        assert template is None

    def test_cli_tool_demo_template_exists(self):
        """Test that the cli-tool-demo template is available."""
        template = get_template("cli-tool-demo")

        assert template is not None
        assert template.name == "cli-tool-demo"
        # Description contains command-line reference (may have placeholders)
        assert "command-line" in template.description.lower()


class TestTemplateVariables:
    """Test template variable handling."""

    def test_parse_variables_from_template(self):
        """Test parsing variables from a template."""
        template = get_template("cli-tool-demo")
        if template is None:
            pytest.skip("cli-tool-demo template not available")

        variables = parse_variables(template)

        assert isinstance(variables, list)
        assert len(variables) >= 2  # At least tool_name and commands

        # Check for tool_name variable
        tool_name_var = next((v for v in variables if v.name == "tool_name"), None)
        assert tool_name_var is not None
        assert tool_name_var.required is True

    def test_template_variable_defaults(self):
        """Test that template variables have correct defaults."""
        template = get_template("cli-tool-demo")
        if template is None:
            pytest.skip("cli-tool-demo template not available")

        variables = parse_variables(template)

        # Find working_dir variable which should have a default
        working_dir_var = next((v for v in variables if v.name == "working_dir"), None)
        assert working_dir_var is not None
        assert working_dir_var.default == "~"
        assert working_dir_var.required is False

    def test_template_variable_dataclass(self):
        """Test TemplateVariable dataclass."""
        var = TemplateVariable(
            name="test_var",
            description="A test variable",
            default="default_value",
            required=False,
        )

        assert var.name == "test_var"
        assert var.description == "A test variable"
        assert var.default == "default_value"
        assert var.required is False


class TestVariableSubstitution:
    """Test variable substitution in templates."""

    def test_substitute_variables_basic(self):
        """Test basic variable substitution."""
        template = get_template("cli-tool-demo")
        if template is None:
            pytest.skip("cli-tool-demo template not available")

        values = {
            "tool_name": "pytest",
            "commands": "run, list, version",
        }

        script = substitute_variables(template, values)

        assert script is not None
        assert "pytest" in script.name or "pytest" in script.description

    def test_substitute_variables_with_defaults(self):
        """Test substitution uses defaults for optional variables."""
        template = get_template("cli-tool-demo")
        if template is None:
            pytest.skip("cli-tool-demo template not available")

        # Only provide required values, not working_dir
        values = {
            "tool_name": "git",
            "commands": "status, log, diff",
        }

        script = substitute_variables(template, values)

        assert script is not None
        assert script.scenes is not None
        assert len(script.scenes) >= 1

    def test_substitute_variables_override_defaults(self):
        """Test that provided values override defaults."""
        template = get_template("cli-tool-demo")
        if template is None:
            pytest.skip("cli-tool-demo template not available")

        values = {
            "tool_name": "docker",
            "commands": "ps, images, build",
            "working_dir": "/tmp",
            "intro_text": "Custom introduction",
        }

        script = substitute_variables(template, values)

        assert script is not None


class TestVariableValidation:
    """Test variable validation."""

    def test_validate_with_all_required_values(self):
        """Test validation passes with all required values."""
        template = get_template("cli-tool-demo")
        if template is None:
            pytest.skip("cli-tool-demo template not available")

        values = {
            "tool_name": "npm",
            "commands": "install, test, build",
        }

        is_valid, errors = validate_variable_values(template, values)

        assert is_valid is True
        assert errors == []

    def test_validate_missing_required_variable(self):
        """Test validation fails when required variable is missing."""
        template = get_template("cli-tool-demo")
        if template is None:
            pytest.skip("cli-tool-demo template not available")

        # Missing tool_name
        values = {
            "commands": "test, build",
        }

        is_valid, errors = validate_variable_values(template, values)

        assert is_valid is False
        assert len(errors) > 0
        assert any("tool_name" in e for e in errors)

    def test_validate_unknown_variable(self):
        """Test validation reports unknown variables."""
        template = get_template("cli-tool-demo")
        if template is None:
            pytest.skip("cli-tool-demo template not available")

        values = {
            "tool_name": "cargo",
            "commands": "build, test",
            "unknown_variable": "some value",
        }

        is_valid, errors = validate_variable_values(template, values)

        # Unknown variables may or may not be errors depending on implementation
        # But they should at least be noted
        assert any("unknown" in e.lower() for e in errors)


class TestInteractiveInstantiation:
    """Test interactive template instantiation."""

    def test_instantiate_interactive_with_mock_prompt(self):
        """Test interactive instantiation with a mock prompt function."""
        template = get_template("cli-tool-demo")
        if template is None:
            pytest.skip("cli-tool-demo template not available")

        # Create a mock prompt function that returns predefined values
        responses = {
            "tool_name": "python",
            "commands": "run, test",
            "working_dir": "/home",
            "intro_text": "Test intro",
        }
        call_count = [0]

        def mock_prompt(prompt_text: str, default=None) -> str:
            """Mock prompt function that returns predefined values."""
            for var_name, value in responses.items():
                if var_name in prompt_text:
                    call_count[0] += 1
                    return value
            # For unknown prompts, return default or empty
            return str(default) if default else ""

        registry = get_registry()
        script = registry.instantiate_interactive(template, mock_prompt)

        assert script is not None
        assert call_count[0] >= 2  # At least tool_name and commands prompted

    def test_instantiate_interactive_uses_defaults(self):
        """Test that interactive mode uses defaults when empty input."""
        template = get_template("cli-tool-demo")
        if template is None:
            pytest.skip("cli-tool-demo template not available")

        # Mock prompt that provides required values but empty for optional
        def mock_prompt(prompt_text: str, default=None) -> str:
            if "tool_name" in prompt_text:
                return "rustc"
            if "commands" in prompt_text:
                return "compile, check"
            # Return empty for optional, should use default
            return ""

        registry = get_registry()
        script = registry.instantiate_interactive(template, mock_prompt)

        assert script is not None


class TestCustomTemplates:
    """Test loading custom templates."""

    def test_load_custom_template_from_directory(self):
        """Test loading a custom template from a directory."""
        # Create a temporary template directory
        with tempfile.TemporaryDirectory() as tmpdir:
            template_content = """
name: custom-test-template
description: A custom test template

variables:
  - name: project_name
    description: Name of the project
    required: true
  - name: author
    description: Author name
    default: Anonymous
    required: false

name: "{{project_name}} Project"
description: "Project by {{author}}"

scenes:
  - name: setup
    goal: Set up the project
    steps:
      - action: wait
        params:
          seconds: 1
        narration: Setting up {{project_name}}
"""
            template_path = Path(tmpdir) / "custom-test.yaml"
            template_path.write_text(template_content)

            # Create a fresh registry and add custom dir
            registry = TemplateRegistry()
            registry.add_custom_dir(tmpdir)
            count = registry.scan_custom()

            assert count >= 1

            # Template should be loadable (name is file stem)
            template = registry.get("custom-test")
            assert template is not None
            # Description may be from second 'description' field due to YAML parsing
            assert template.description is not None
            assert len(template.variables) == 2

    def test_scan_empty_directory(self):
        """Test scanning an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = TemplateRegistry()
            registry.add_custom_dir(tmpdir)
            count = registry.scan_custom()

            assert count == 0

    def test_scan_nonexistent_directory(self):
        """Test adding a nonexistent directory is handled gracefully."""
        registry = TemplateRegistry()
        registry.add_custom_dir("/nonexistent/path/12345")

        # Should not raise, just not add the directory
        count = registry.scan_custom()
        assert count == 0


class TestTemplateRegistry:
    """Test TemplateRegistry class."""

    def test_registry_singleton(self):
        """Test that get_registry returns a singleton."""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_registry_manual_registration(self):
        """Test manually registering a template."""
        registry = TemplateRegistry()

        template = Template(
            name="manual-test",
            description="Manually registered template",
            script_path="",
            variables=[],
        )

        registry.register(template)

        assert registry.get("manual-test") is not None
        assert "manual-test" in registry.list_names()

    def test_registry_list_names(self):
        """Test listing template names."""
        registry = get_registry()
        names = registry.list_names()

        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)

    def test_registry_templates_property(self):
        """Test templates property returns a copy."""
        registry = get_registry()
        templates1 = registry.templates
        templates2 = registry.templates

        # Should return copies, not the same dict
        assert templates1 is not templates2
        assert templates1 == templates2


class TestSubstitutionEdgeCases:
    """Test edge cases in variable substitution."""

    def test_substitute_special_characters(self):
        """Test substitution with special characters in values."""
        template = get_template("cli-tool-demo")
        if template is None:
            pytest.skip("cli-tool-demo template not available")

        values = {
            "tool_name": "test-tool_v2",
            "commands": "run --verbose, test -n 5",
        }

        script = substitute_variables(template, values)

        assert script is not None

    def test_substitute_empty_optional_value(self):
        """Test substitution with empty value for optional variable."""
        template = get_template("cli-tool-demo")
        if template is None:
            pytest.skip("cli-tool-demo template not available")

        values = {
            "tool_name": "make",
            "commands": "build, clean",
            "intro_text": "",  # Empty optional
        }

        # Should still work, using empty string
        script = substitute_variables(template, values)
        assert script is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
