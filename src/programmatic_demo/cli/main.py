"""Main CLI entry point for ProgrammaticDemo."""

import json
from typing import Optional

import typer

from programmatic_demo import __version__
from programmatic_demo.cli import recording, terminal, keyboard, mouse, browser, perception, script, action, run, video, effects

app = typer.Typer(
    name="pdemo",
    help="Agent-driven autonomous screen-recorded product demos.",
    no_args_is_help=True,
)

# Global state for JSON output mode
_json_output = False


def set_json_output(value: bool) -> None:
    """Set global JSON output mode."""
    global _json_output
    _json_output = value


def is_json_output() -> bool:
    """Check if JSON output mode is enabled."""
    return _json_output


def output_json(data: dict) -> None:
    """Print data as JSON if in JSON mode, otherwise do nothing."""
    if _json_output:
        typer.echo(json.dumps(data, indent=2))


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"pdemo version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output results as JSON.",
    ),
) -> None:
    """ProgrammaticDemo CLI - autonomous screen-recorded product demos."""
    set_json_output(json_output)


# Register subcommand groups
app.add_typer(recording.app, name="record")
app.add_typer(terminal.app, name="terminal")
app.add_typer(keyboard.app, name="keyboard")
app.add_typer(mouse.app, name="mouse")
app.add_typer(browser.app, name="browser")
app.add_typer(perception.app, name="observe")
app.add_typer(script.app, name="script")
app.add_typer(action.app, name="action")
app.add_typer(run.app, name="run")
app.add_typer(video.app, name="video")
app.add_typer(effects.app, name="effects")


if __name__ == "__main__":
    app()
