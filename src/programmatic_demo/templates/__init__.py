"""Templates module for demo script templates.

This package provides template management:
- Built-in demo templates for common scenarios
- Custom template loading and validation
- Template variables and parameter substitution
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TemplateVariable:
    """A variable in a template.

    Attributes:
        name: Variable name
        description: Description of the variable
        default: Default value (if any)
        required: Whether the variable is required
    """

    name: str
    description: str = ""
    default: Any = None
    required: bool = True


@dataclass
class Template:
    """A demo script template.

    Attributes:
        name: Template name/identifier
        description: Human-readable description
        script_path: Path to the template script file
        variables: List of template variables
    """

    name: str
    description: str = ""
    script_path: str = ""
    variables: list[TemplateVariable] = field(default_factory=list)


# Import registry after Template is defined to avoid circular imports
from programmatic_demo.templates.registry import TemplateRegistry, get_registry


def list_templates() -> list[Template]:
    """List all available templates.

    Returns:
        List of all registered Template objects.
    """
    registry = get_registry()
    return list(registry.templates.values())


def get_template(name: str) -> Template | None:
    """Get a template by name.

    Args:
        name: Template name to retrieve.

    Returns:
        Template if found, None otherwise.
    """
    registry = get_registry()
    return registry.get(name)


def parse_variables(template: Template) -> list[TemplateVariable]:
    """Parse and return the variables from a template.

    Args:
        template: Template to parse variables from.

    Returns:
        List of TemplateVariable objects defined in the template.
    """
    return template.variables.copy() if template.variables else []


__all__ = [
    "Template",
    "TemplateRegistry",
    "TemplateVariable",
    "get_registry",
    "get_template",
    "list_templates",
    "parse_variables",
]
