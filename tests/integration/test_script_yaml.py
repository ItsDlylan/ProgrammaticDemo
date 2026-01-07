"""INT-005: Test parse and validate YAML script.

This test verifies that:
1. A test script YAML file can be created
2. Script.from_yaml() can load it
3. Script.validate() returns no errors
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from programmatic_demo.models import Script


VALID_SCRIPT_YAML = """
name: Test Demo Script
description: A test script for validation

metadata:
  author: test
  version: "1.0"

scenes:
  - name: intro
    goal: Introduce the demo
    steps:
      - action: wait
        params:
          seconds: 1
        narration: Welcome to the test demo

  - name: main
    goal: Perform main actions
    steps:
      - action: click
        target:
          type: screen
          description: Start button
        wait_for:
          type: text
          value: Started
        narration: Click the start button

      - action: type
        target:
          type: selector
          selector: "#search-input"
        params:
          text: hello world
        narration: Type search query

      - action: terminal
        params:
          command: echo "Hello World"
        wait_for:
          type: text
          value: Hello
        narration: Run a terminal command

  - name: outro
    goal: Conclude the demo
    steps:
      - action: wait
        params:
          seconds: 2
        narration: Thank you for watching
"""


class TestScriptYamlParsing:
    """Test YAML script parsing and validation."""

    def test_parse_valid_yaml_script(self):
        """Test that a valid YAML script can be parsed."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(VALID_SCRIPT_YAML)
            yaml_path = Path(f.name)

        try:
            script = Script.from_yaml(yaml_path)

            assert script is not None
            assert script.name == "Test Demo Script"
            assert script.description == "A test script for validation"
            assert script.scenes is not None
            assert len(script.scenes) == 3
        finally:
            yaml_path.unlink()

    def test_validate_parsed_script(self):
        """Test that a valid parsed script validates without errors."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(VALID_SCRIPT_YAML)
            yaml_path = Path(f.name)

        try:
            script = Script.from_yaml(yaml_path)
            errors = script.validate()

            assert errors == [], f"Validation errors: {errors}"
        finally:
            yaml_path.unlink()

    def test_script_scenes_parsed_correctly(self):
        """Test that scenes are parsed with correct structure."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(VALID_SCRIPT_YAML)
            yaml_path = Path(f.name)

        try:
            script = Script.from_yaml(yaml_path)

            # Check intro scene
            intro = script.scenes[0]
            assert intro.name == "intro"
            assert intro.goal == "Introduce the demo"
            assert len(intro.steps) == 1
            assert intro.steps[0].action.value == "wait"

            # Check main scene
            main = script.scenes[1]
            assert main.name == "main"
            assert len(main.steps) == 3

            # Check click step has correct target
            click_step = main.steps[0]
            assert click_step.action.value == "click"
            assert click_step.target is not None
            assert click_step.target.type.value == "screen"
            assert click_step.target.description == "Start button"
            assert click_step.wait_for is not None
            assert click_step.wait_for.type.value == "text"
            assert click_step.wait_for.value == "Started"

            # Check type step
            type_step = main.steps[1]
            assert type_step.action.value == "type"
            assert type_step.target.type.value == "selector"
            assert type_step.target.selector == "#search-input"
        finally:
            yaml_path.unlink()

    def test_script_to_dict_roundtrip(self):
        """Test that script can be converted to dict and back."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(VALID_SCRIPT_YAML)
            yaml_path = Path(f.name)

        try:
            script = Script.from_yaml(yaml_path)
            script_dict = script.to_dict()

            # Recreate from dict
            script2 = Script.from_dict(script_dict)

            assert script2.name == script.name
            assert script2.description == script.description
            assert len(script2.scenes) == len(script.scenes)
            assert script2.validate() == []
        finally:
            yaml_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
