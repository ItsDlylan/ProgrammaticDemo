"""Template registry for managing demo templates.

Provides template discovery, registration, and lookup.
"""

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


# Singleton instance
_registry: TemplateRegistry | None = None


def get_registry() -> TemplateRegistry:
    """Get or create the singleton TemplateRegistry instance."""
    global _registry
    if _registry is None:
        _registry = TemplateRegistry()
        _registry.scan()
    return _registry
