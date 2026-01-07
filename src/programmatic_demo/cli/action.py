"""CLI commands for natural language action parsing and execution."""

import json
from dataclasses import asdict

import typer

from programmatic_demo.nlp.parser import ActionIntent, parse_action, resolve_and_execute
from programmatic_demo.nlp.resolver import get_resolver

app = typer.Typer(help="Natural language action commands.")


@app.command("parse")
def parse(
    text: str = typer.Argument(..., help="Natural language action description"),
) -> None:
    """Parse natural language text into an ActionIntent.

    Examples:
        pdemo action parse "click the Submit button"
        pdemo action parse "type hello in the search field"
        pdemo action parse "press Enter"
        pdemo action parse "scroll down"
    """
    intent = parse_action(text)

    if intent is None:
        result = {
            "status": "error",
            "message": f"Could not parse action from: {text}",
        }
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)

    result = {
        "status": "success",
        "intent": {
            "action_type": intent.action_type,
            "target_description": intent.target_description,
            "params": intent.params,
            "confidence": intent.confidence,
        },
    }
    typer.echo(json.dumps(result, indent=2))


@app.command("resolve")
def resolve(
    target: str = typer.Argument(..., help="Target description to resolve"),
) -> None:
    """Resolve a target description to screen coordinates.

    Uses OCR to find the target on the current screen.

    Examples:
        pdemo action resolve "Submit button"
        pdemo action resolve "search field"
        pdemo action resolve "File menu"
    """
    resolver = get_resolver()

    try:
        resolved = resolver.resolve(target)

        if resolved is None:
            result = {
                "status": "error",
                "message": f"Could not find target: {target}",
            }
            typer.echo(json.dumps(result, indent=2))
            raise typer.Exit(1)

        result = {
            "status": "success",
            "target": {
                "coords": {"x": resolved.coords[0], "y": resolved.coords[1]},
                "confidence": resolved.confidence,
                "element_text": resolved.element_text,
                "bounds": resolved.bounds,
            },
        }
        typer.echo(json.dumps(result, indent=2))

    except Exception as e:
        result = {"status": "error", "message": str(e)}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)


@app.command("execute")
def execute(
    text: str = typer.Argument(..., help="Natural language action to execute"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Parse and resolve only, don't execute"
    ),
) -> None:
    """Parse, resolve, and execute a natural language action.

    This command parses the natural language text into an action,
    resolves any target descriptions to screen coordinates, and
    executes the action.

    Examples:
        pdemo action execute "click the Submit button"
        pdemo action execute "type hello world"
        pdemo action execute --dry-run "click Settings"
    """
    # First parse the action
    intent = parse_action(text)

    if intent is None:
        result = {
            "status": "error",
            "message": f"Could not parse action from: {text}",
        }
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)

    if dry_run:
        # Just show what would be executed
        result = {
            "status": "dry_run",
            "intent": {
                "action_type": intent.action_type,
                "target_description": intent.target_description,
                "params": intent.params,
                "confidence": intent.confidence,
            },
            "message": "Action parsed successfully (dry run - not executed)",
        }
        typer.echo(json.dumps(result, indent=2))
        return

    try:
        # Execute the action
        exec_result = resolve_and_execute(intent)

        output = {
            "status": "success" if exec_result.get("success") else "error",
            "intent": {
                "action_type": intent.action_type,
                "target_description": intent.target_description,
                "params": intent.params,
            },
            "result": exec_result,
        }
        typer.echo(json.dumps(output, indent=2))

        if not exec_result.get("success"):
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        result = {
            "status": "error",
            "message": str(e),
            "intent": {
                "action_type": intent.action_type,
                "target_description": intent.target_description,
                "params": intent.params,
            },
        }
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)
