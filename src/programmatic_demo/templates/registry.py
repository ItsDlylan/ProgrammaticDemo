"""Template registry for managing demo templates.

Provides template discovery, registration, and lookup.
"""

import re
from pathlib import Path
from typing import Any

import yaml

from programmatic_demo.templates import Template, TemplateVariable


class TemplateRegistry:
    """Registry for managing demo templates.

    Discovers templates from builtin directory and custom paths,
    and provides lookup by name.
    """

    def __init__(self) -> None:
        """Initialize the TemplateRegistry."""
        self._templates: dict[str, Template] = {}
        self._custom_dirs: list[Path] = []
        self._builtin_dir = Path(__file__).parent / "builtin"

    @property
    def templates(self) -> dict[str, Template]:
        """Get all registered templates."""
        return self._templates.copy()

    def scan_builtin(self) -> int:
        """Scan the builtin directory for templates.

        Returns:
            Number of templates found.
        """
        if not self._builtin_dir.exists():
            return 0

        count = 0
        for path in self._builtin_dir.glob("*.yaml"):
            template = self._load_template_file(path)
            if template:
                self._templates[template.name] = template
                count += 1

        for path in self._builtin_dir.glob("*.yml"):
            template = self._load_template_file(path)
            if template:
                self._templates[template.name] = template
                count += 1

        return count

    def add_custom_dir(self, path: str | Path) -> None:
        """Add a custom template directory.

        Args:
            path: Path to directory containing templates.
        """
        dir_path = Path(path)
        if dir_path.exists() and dir_path.is_dir():
            self._custom_dirs.append(dir_path)

    def scan_custom(self) -> int:
        """Scan custom directories for templates.

        Returns:
            Number of templates found.
        """
        count = 0
        for dir_path in self._custom_dirs:
            for path in dir_path.glob("*.yaml"):
                template = self._load_template_file(path)
                if template:
                    self._templates[template.name] = template
                    count += 1

            for path in dir_path.glob("*.yml"):
                template = self._load_template_file(path)
                if template:
                    self._templates[template.name] = template
                    count += 1

        return count

    def scan(self) -> int:
        """Scan all directories for templates.

        Returns:
            Total number of templates found.
        """
        count = self.scan_builtin()
        count += self.scan_custom()
        return count

    def register(self, template: Template) -> None:
        """Register a template manually.

        Args:
            template: Template to register.
        """
        self._templates[template.name] = template

    def get(self, name: str) -> Template | None:
        """Get a template by name.

        Args:
            name: Template name.

        Returns:
            Template if found, None otherwise.
        """
        return self._templates.get(name)

    def list_names(self) -> list[str]:
        """List all registered template names.

        Returns:
            List of template names.
        """
        return list(self._templates.keys())

    def _load_template_file(self, path: Path) -> Template | None:
        """Load a template from a YAML file.

        Args:
            path: Path to YAML file.

        Returns:
            Template if valid, None otherwise.
        """
        try:
            with open(path) as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                return None

            name = data.get("name", path.stem)
            description = data.get("description", "")

            variables: list[TemplateVariable] = []
            for var_data in data.get("variables", []):
                if isinstance(var_data, dict):
                    variables.append(
                        TemplateVariable(
                            name=var_data.get("name", ""),
                            description=var_data.get("description", ""),
                            default=var_data.get("default"),
                            required=var_data.get("required", True),
                        )
                    )

            return Template(
                name=name,
                description=description,
                script_path=str(path),
                variables=variables,
            )
        except Exception:
            return None

    def substitute_variables(
        self,
        template: Template,
        values: dict[str, Any],
    ) -> Any:
        """Substitute variables in a template and return a Script.

        Replaces {{variable}} patterns with provided values,
        parses the resulting YAML, and returns a Script object.

        Args:
            template: Template to substitute variables in.
            values: Dictionary mapping variable names to values.

        Returns:
            Script object with variables substituted.

        Raises:
            FileNotFoundError: If template script file doesn't exist.
            ValueError: If template parsing fails after substitution.
        """
        # Import Script here to avoid circular imports
        from programmatic_demo.models.script import Script

        # Load template file content
        script_path = Path(template.script_path)
        if not script_path.exists():
            raise FileNotFoundError(f"Template file not found: {script_path}")

        with open(script_path) as f:
            content = f.read()

        # Apply default values for missing variables
        effective_values = {}
        for var in template.variables:
            if var.name in values:
                effective_values[var.name] = values[var.name]
            elif var.default is not None:
                effective_values[var.name] = var.default

        # Substitute {{variable}} patterns
        def replace_var(match: re.Match) -> str:
            var_name = match.group(1).strip()
            if var_name in effective_values:
                value = effective_values[var_name]
                # Handle string escaping for YAML
                if isinstance(value, str):
                    return value
                return str(value)
            # Leave unmatched variables as-is
            return match.group(0)

        substituted = re.sub(r"\{\{\s*(\w+)\s*\}\}", replace_var, content)

        # Parse the substituted YAML
        try:
            data = yaml.safe_load(substituted)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse substituted template: {e}")

        if not isinstance(data, dict):
            raise ValueError("Template must contain a YAML dictionary")

        # Create and return Script object
        return Script.from_dict(data)

    def validate_variable_values(
        self,
        template: Template,
        values: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate that provided values match template requirements.

        Checks that all required variables are provided and have valid values.

        Args:
            template: Template to validate against.
            values: Dictionary mapping variable names to values.

        Returns:
            Tuple of (is_valid, list of error messages).
        """
        errors: list[str] = []

        # Check required variables are provided
        for var in template.variables:
            if var.required:
                if var.name not in values:
                    if var.default is None:
                        errors.append(f"Missing required variable: {var.name}")
                elif values[var.name] is None:
                    errors.append(f"Variable '{var.name}' cannot be None")

        # Check for unknown variables (optional, just a warning)
        known_vars = {var.name for var in template.variables}
        for name in values:
            if name not in known_vars:
                errors.append(f"Unknown variable: {name}")

        return (len(errors) == 0, errors)

    def instantiate_interactive(
        self,
        template: "Template",
        prompt_fn: callable | None = None,
    ) -> Any:
        """Interactively instantiate a template by prompting for variables.

        Walks through each variable defined in the template, showing
        descriptions and defaults, and prompting the user for input.
        After collecting all values, validates them and generates a Script.

        Args:
            template: Template to instantiate.
            prompt_fn: Custom prompt function that takes (prompt_text, default)
                      and returns user input. If None, uses built-in input().

        Returns:
            Script object with all variables substituted.

        Raises:
            ValueError: If validation fails after collecting input.
            KeyboardInterrupt: If user cancels during input.
        """
        # Import Script here to avoid circular imports
        from programmatic_demo.models.script import Script

        if prompt_fn is None:
            def prompt_fn(text: str, default: Any = None) -> str:
                if default is not None:
                    prompt = f"{text} [{default}]: "
                else:
                    prompt = f"{text}: "
                response = input(prompt).strip()
                return response if response else (str(default) if default is not None else "")

        print(f"\n{'='*60}")
        print(f"Template: {template.name}")
        print(f"Description: {template.description}")
        print(f"{'='*60}\n")

        values: dict[str, Any] = {}

        for var in template.variables:
            # Display variable info
            print(f"\n--- {var.name} ---")
            if var.description:
                print(f"  Description: {var.description}")
            if var.default is not None:
                print(f"  Default: {var.default}")
            print(f"  Required: {'Yes' if var.required else 'No'}")

            # Prompt for value
            while True:
                try:
                    value = prompt_fn(f"  Enter {var.name}", var.default)

                    # Handle empty input
                    if not value and var.required and var.default is None:
                        print("  Error: This variable is required")
                        continue

                    # Use default if empty
                    if not value and var.default is not None:
                        value = var.default

                    values[var.name] = value
                    break

                except EOFError:
                    # Handle end of input (e.g., piped input)
                    if var.default is not None:
                        values[var.name] = var.default
                        break
                    elif not var.required:
                        values[var.name] = ""
                        break
                    else:
                        raise ValueError(f"No input provided for required variable: {var.name}")

        print(f"\n{'='*60}")
        print("Collected values:")
        for name, value in values.items():
            display_value = value if len(str(value)) < 50 else str(value)[:47] + "..."
            print(f"  {name}: {display_value}")
        print(f"{'='*60}\n")

        # Validate collected values
        is_valid, errors = self.validate_variable_values(template, values)
        if not is_valid:
            error_msg = "\n".join(f"  - {e}" for e in errors)
            raise ValueError(f"Validation errors:\n{error_msg}")

        # Generate script
        return self.substitute_variables(template, values)


def instantiate_interactive(
    template_name: str,
    prompt_fn: callable | None = None,
) -> Any:
    """Convenience function to interactively instantiate a template by name.

    Args:
        template_name: Name of the template to instantiate.
        prompt_fn: Custom prompt function (see TemplateRegistry.instantiate_interactive).

    Returns:
        Script object with all variables substituted.

    Raises:
        ValueError: If template not found or validation fails.
    """
    registry = get_registry()
    template = registry.get(template_name)
    if template is None:
        available = registry.list_names()
        raise ValueError(f"Template not found: {template_name}. Available: {available}")
    return registry.instantiate_interactive(template, prompt_fn)


# Singleton instance
_registry: TemplateRegistry | None = None


def get_registry() -> TemplateRegistry:
    """Get or create the singleton TemplateRegistry instance."""
    global _registry
    if _registry is None:
        _registry = TemplateRegistry()
        _registry.scan()
    return _registry
