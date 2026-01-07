"""Prompt templates for director agent interactions.

This package contains prompt templates used by the Director agent
for planning scenes, analyzing observations, and deciding on actions.
"""

import re
from pathlib import Path
from typing import Any

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str, **variables: Any) -> str:
    """Load a prompt template by name with optional variable substitution.

    Args:
        name: Name of the prompt template (without .txt extension).
        **variables: Variables to substitute in the template.
            Use {variable_name} placeholders in templates.

    Returns:
        The prompt template text with variables substituted.

    Raises:
        FileNotFoundError: If the prompt template doesn't exist.

    Example:
        >>> load_prompt("scene_planner", demo_name="My Demo", scene_description="Login flow")
    """
    prompt_path = PROMPTS_DIR / f"{name}.txt"
    template = prompt_path.read_text()

    if variables:
        # Substitute variables using {variable_name} format
        # We use a custom substitution to handle missing variables gracefully
        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            if var_name in variables:
                return str(variables[var_name])
            # Keep original placeholder if variable not provided
            return match.group(0)

        template = re.sub(r"\{(\w+)\}", replace_var, template)

    return template


def format_prompt(template: str, **variables: Any) -> str:
    """Format a prompt template string with variable substitution.

    Args:
        template: The template string with {variable_name} placeholders.
        **variables: Variables to substitute.

    Returns:
        The formatted string with variables substituted.

    Example:
        >>> format_prompt("Hello {name}!", name="World")
        "Hello World!"
    """
    def replace_var(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name in variables:
            return str(variables[var_name])
        return match.group(0)

    return re.sub(r"\{(\w+)\}", replace_var, template)


def get_available_prompts() -> list[str]:
    """Get a list of available prompt template names.

    Returns:
        List of prompt names (without .txt extension).
    """
    return [p.stem for p in PROMPTS_DIR.glob("*.txt")]


def get_prompt_variables(name: str) -> list[str]:
    """Get the list of variables used in a prompt template.

    Args:
        name: Name of the prompt template (without .txt extension).

    Returns:
        List of variable names found in the template.
    """
    prompt_path = PROMPTS_DIR / f"{name}.txt"
    template = prompt_path.read_text()
    # Find all {variable_name} patterns
    matches = re.findall(r"\{(\w+)\}", template)
    # Return unique variable names
    return list(dict.fromkeys(matches))


__all__ = [
    "load_prompt",
    "format_prompt",
    "get_available_prompts",
    "get_prompt_variables",
    "PROMPTS_DIR",
]
