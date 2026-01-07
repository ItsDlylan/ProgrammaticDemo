"""CLI commands for demo template management."""

import json
from pathlib import Path
from typing import Optional

import typer
import yaml

app = typer.Typer(help="Demo template commands.")


@app.command("list")
def list_templates(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed template info"),
) -> None:
    """List available demo templates.

    Examples:
        pdemo template list              # List all templates
        pdemo template list --verbose    # Show details for each template
    """
    from programmatic_demo.templates import list_templates as get_templates, get_registry

    # Ensure templates are scanned
    registry = get_registry()
    templates = get_templates()

    if not templates:
        typer.echo(json.dumps({"success": True, "templates": [], "message": "No templates found"}))
        return

    if verbose:
        template_list = []
        for t in templates:
            template_info = {
                "name": t.name,
                "description": t.description,
                "script_path": t.script_path,
                "variables": [
                    {
                        "name": v.name,
                        "description": v.description,
                        "default": v.default,
                        "required": v.required,
                    }
                    for v in t.variables
                ],
            }
            template_list.append(template_info)
        typer.echo(json.dumps({"success": True, "templates": template_list}, indent=2))
    else:
        template_list = [{"name": t.name, "description": t.description} for t in templates]
        typer.echo(json.dumps({"success": True, "templates": template_list}, indent=2))


@app.command("info")
def info(
    name: str = typer.Argument(..., help="Template name to get info for"),
) -> None:
    """Show detailed information about a template.

    Examples:
        pdemo template info cli-tool-demo
        pdemo template info web-app-walkthrough
    """
    from programmatic_demo.templates import get_template, get_registry

    # Ensure templates are scanned
    registry = get_registry()
    template = get_template(name)

    if template is None:
        available = registry.list_names()
        typer.echo(json.dumps({
            "success": False,
            "error": f"Template not found: {name}",
            "available_templates": available,
        }))
        raise typer.Exit(1)

    template_info = {
        "name": template.name,
        "description": template.description,
        "script_path": template.script_path,
        "variables": [
            {
                "name": v.name,
                "description": v.description,
                "default": v.default,
                "required": v.required,
            }
            for v in template.variables
        ],
    }
    typer.echo(json.dumps({"success": True, "template": template_info}, indent=2))


@app.command("use")
def use(
    name: str = typer.Argument(..., help="Template name to instantiate"),
    output: str = typer.Option(..., "--output", "-o", help="Output file path for generated script"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Prompt for variable values interactively"),
    values: Optional[str] = typer.Option(None, "--values", "-V", help="JSON string of variable values"),
    values_file: Optional[str] = typer.Option(None, "--values-file", "-f", help="JSON file with variable values"),
) -> None:
    """Instantiate a template to create a demo script.

    Either use --interactive to prompt for values, or provide values via
    --values (JSON string) or --values-file (JSON file).

    Examples:
        pdemo template use cli-tool-demo -o demo.yaml -i
        pdemo template use cli-tool-demo -o demo.yaml -V '{"tool_name": "git", "commands": "status,log"}'
        pdemo template use cli-tool-demo -o demo.yaml -f values.json
    """
    from programmatic_demo.templates import (
        get_template,
        get_registry,
        substitute_variables,
        validate_variable_values,
    )

    # Ensure templates are scanned
    registry = get_registry()
    template = get_template(name)

    if template is None:
        available = registry.list_names()
        typer.echo(json.dumps({
            "success": False,
            "error": f"Template not found: {name}",
            "available_templates": available,
        }))
        raise typer.Exit(1)

    # Collect variable values
    var_values: dict = {}

    if interactive:
        # Use interactive mode
        try:
            script = registry.instantiate_interactive(template)
        except KeyboardInterrupt:
            typer.echo(json.dumps({"success": False, "error": "Cancelled by user"}))
            raise typer.Exit(1)
        except ValueError as e:
            typer.echo(json.dumps({"success": False, "error": str(e)}))
            raise typer.Exit(1)

        # Write script to output file
        output_path = Path(output)
        script_dict = script.to_dict()

        if output_path.suffix.lower() in {".yaml", ".yml"}:
            with open(output_path, "w") as f:
                yaml.dump(script_dict, f, default_flow_style=False, sort_keys=False)
        else:
            with open(output_path, "w") as f:
                json.dump(script_dict, f, indent=2)

        typer.echo(json.dumps({
            "success": True,
            "output": str(output_path),
            "template": name,
            "script_name": script.name,
        }))
        return

    # Non-interactive mode - get values from options
    if values_file:
        values_path = Path(values_file)
        if not values_path.exists():
            typer.echo(json.dumps({"success": False, "error": f"Values file not found: {values_file}"}))
            raise typer.Exit(1)
        with open(values_path) as f:
            var_values = json.load(f)
    elif values:
        try:
            var_values = json.loads(values)
        except json.JSONDecodeError as e:
            typer.echo(json.dumps({"success": False, "error": f"Invalid JSON in --values: {e}"}))
            raise typer.Exit(1)
    else:
        # Check if all variables have defaults
        required_vars = [v for v in template.variables if v.required and v.default is None]
        if required_vars:
            var_names = [v.name for v in required_vars]
            typer.echo(json.dumps({
                "success": False,
                "error": "Missing required variable values",
                "required_variables": var_names,
                "hint": "Use --interactive, --values, or --values-file to provide values",
            }))
            raise typer.Exit(1)

    # Validate values
    is_valid, errors = validate_variable_values(template, var_values)
    if not is_valid:
        typer.echo(json.dumps({
            "success": False,
            "error": "Validation failed",
            "validation_errors": errors,
        }))
        raise typer.Exit(1)

    # Substitute variables and create script
    try:
        script = substitute_variables(template, var_values)
    except Exception as e:
        typer.echo(json.dumps({"success": False, "error": f"Failed to substitute variables: {e}"}))
        raise typer.Exit(1)

    # Write script to output file
    output_path = Path(output)
    script_dict = script.to_dict()

    if output_path.suffix.lower() in {".yaml", ".yml"}:
        with open(output_path, "w") as f:
            yaml.dump(script_dict, f, default_flow_style=False, sort_keys=False)
    else:
        with open(output_path, "w") as f:
            json.dump(script_dict, f, indent=2)

    typer.echo(json.dumps({
        "success": True,
        "output": str(output_path),
        "template": name,
        "script_name": script.name,
    }))


@app.command("create")
def create(
    name: str = typer.Argument(..., help="Name for the new template"),
    output_dir: str = typer.Option(".", "--output-dir", "-d", help="Directory to create template in"),
    description: str = typer.Option("", "--description", "-D", help="Template description"),
    variables: Optional[str] = typer.Option(None, "--variables", "-v", help="Comma-separated variable names"),
) -> None:
    """Create a new template file with boilerplate structure.

    Examples:
        pdemo template create my-demo
        pdemo template create my-demo -d ./templates -D "My custom demo template"
        pdemo template create my-demo -v "app_name,feature,version"
    """
    output_path = Path(output_dir) / f"{name}.yaml"

    if output_path.exists():
        typer.echo(json.dumps({
            "success": False,
            "error": f"Template file already exists: {output_path}",
        }))
        raise typer.Exit(1)

    # Parse variables if provided
    var_list = []
    if variables:
        for var_name in variables.split(","):
            var_name = var_name.strip()
            if var_name:
                var_list.append({
                    "name": var_name,
                    "description": f"Value for {var_name}",
                    "required": True,
                })

    # Build template structure
    template_content = {
        "name": name,
        "description": description or f"Template for {name}",
        "variables": var_list if var_list else [
            {
                "name": "example_var",
                "description": "An example variable",
                "default": "default_value",
                "required": False,
            }
        ],
        "metadata": {
            "template": name,
            "type": "custom",
        },
        "scenes": [
            {
                "name": "intro",
                "goal": "Introduce the demo",
                "steps": [
                    {
                        "action": "wait",
                        "params": {"seconds": 1},
                        "narration": "Welcome to the demo",
                    }
                ],
            },
            {
                "name": "main",
                "goal": "Main demo content",
                "steps": [
                    {
                        "action": "wait",
                        "params": {"seconds": 2},
                        "narration": "Main demonstration goes here",
                    }
                ],
            },
            {
                "name": "outro",
                "goal": "Conclude the demo",
                "steps": [
                    {
                        "action": "wait",
                        "params": {"seconds": 1},
                        "narration": "Thank you for watching",
                    }
                ],
            },
        ],
    }

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write template file
    with open(output_path, "w") as f:
        # Add header comment
        f.write(f"# {name} Demo Template\n")
        f.write(f"# {description or 'Custom demo template'}\n\n")
        yaml.dump(template_content, f, default_flow_style=False, sort_keys=False)

    typer.echo(json.dumps({
        "success": True,
        "output": str(output_path),
        "template_name": name,
        "variables": [v["name"] for v in template_content["variables"]],
    }))
