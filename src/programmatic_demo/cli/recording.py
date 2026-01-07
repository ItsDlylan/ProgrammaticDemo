"""CLI commands for screen recording."""

import json
from typing import Optional

import typer

from programmatic_demo.recording.recorder import get_recorder

app = typer.Typer(help="Screen recording commands.")


@app.command("start")
def start(
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    fps: int = typer.Option(60, "--fps", "-f", help="Frames per second"),
) -> None:
    """Start screen recording."""
    recorder = get_recorder()
    result = recorder.start(output, fps=fps)
    typer.echo(json.dumps(result, indent=2))


@app.command("stop")
def stop() -> None:
    """Stop screen recording."""
    recorder = get_recorder()
    result = recorder.stop()
    typer.echo(json.dumps(result, indent=2))


@app.command("status")
def status() -> None:
    """Get recording status."""
    recorder = get_recorder()
    result = recorder.get_status()
    typer.echo(json.dumps(result, indent=2))
