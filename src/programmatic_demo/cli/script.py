"""CLI commands for script management."""

import json
from pathlib import Path

import typer

from programmatic_demo.models import Script

app = typer.Typer(help="Script management commands.")


@app.command("validate")
def validate(
    file: Path = typer.Argument(..., help="Path to script file (YAML or JSON)"),
) -> None:
    """Validate a script file."""
    if not file.exists():
        result = {"status": "error", "message": f"File not found: {file}"}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)

    try:
        if file.suffix in (".yaml", ".yml"):
            script = Script.from_yaml(file)
        elif file.suffix == ".json":
            script = Script.from_json(file)
        else:
            result = {"status": "error", "message": f"Unsupported file type: {file.suffix}"}
            typer.echo(json.dumps(result, indent=2))
            raise typer.Exit(1)

        errors = script.validate()
        if errors:
            result = {"status": "invalid", "errors": errors}
            typer.echo(json.dumps(result, indent=2))
            raise typer.Exit(1)
        else:
            result = {"status": "valid", "message": "Script is valid"}
            typer.echo(json.dumps(result, indent=2))

    except Exception as e:
        result = {"status": "error", "message": str(e)}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)


@app.command("show")
def show(
    file: Path = typer.Argument(..., help="Path to script file (YAML or JSON)"),
) -> None:
    """Pretty print script structure."""
    if not file.exists():
        result = {"status": "error", "message": f"File not found: {file}"}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)

    try:
        if file.suffix in (".yaml", ".yml"):
            script = Script.from_yaml(file)
        elif file.suffix == ".json":
            script = Script.from_json(file)
        else:
            result = {"status": "error", "message": f"Unsupported file type: {file.suffix}"}
            typer.echo(json.dumps(result, indent=2))
            raise typer.Exit(1)

        # Pretty print structure
        typer.echo(f"Script: {script.name}")
        if script.description:
            typer.echo(f"  Description: {script.description}")
        if script.scenes:
            typer.echo(f"  Scenes: {len(script.scenes)}")
            for i, scene in enumerate(script.scenes):
                typer.echo(f"    [{i}] {scene.name}")
                if scene.goal:
                    typer.echo(f"        Goal: {scene.goal}")
                if scene.steps:
                    typer.echo(f"        Steps: {len(scene.steps)}")
                    for j, step in enumerate(scene.steps):
                        target_info = ""
                        if step.target:
                            target_info = f" -> {step.target.type.value}"
                            if step.target.description:
                                target_info += f": {step.target.description}"
                        typer.echo(f"          [{j}] {step.action.value}{target_info}")

    except Exception as e:
        result = {"status": "error", "message": str(e)}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)


@app.command("export")
def export(
    file: Path = typer.Argument(..., help="Path to script file (YAML or JSON)"),
    output: Path = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json or yaml"),
) -> None:
    """Convert script between YAML and JSON formats."""
    if not file.exists():
        result = {"status": "error", "message": f"File not found: {file}"}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)

    try:
        # Load script
        if file.suffix in (".yaml", ".yml"):
            script = Script.from_yaml(file)
        elif file.suffix == ".json":
            script = Script.from_json(file)
        else:
            result = {"status": "error", "message": f"Unsupported file type: {file.suffix}"}
            typer.echo(json.dumps(result, indent=2))
            raise typer.Exit(1)

        # Convert to dict
        data = script.to_dict()

        # Export
        if format.lower() == "json":
            output_str = json.dumps(data, indent=2)
        elif format.lower() in ("yaml", "yml"):
            import yaml
            output_str = yaml.dump(data, default_flow_style=False, sort_keys=False)
        else:
            result = {"status": "error", "message": f"Unsupported format: {format}"}
            typer.echo(json.dumps(result, indent=2))
            raise typer.Exit(1)

        if output:
            with open(output, "w") as f:
                f.write(output_str)
            result = {"status": "success", "message": f"Exported to {output}"}
            typer.echo(json.dumps(result, indent=2))
        else:
            typer.echo(output_str)

    except Exception as e:
        result = {"status": "error", "message": str(e)}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)
