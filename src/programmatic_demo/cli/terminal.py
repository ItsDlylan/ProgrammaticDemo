"""CLI commands for terminal control."""

import json
from typing import Optional

import typer

from programmatic_demo.actuators.terminal import get_terminal

app = typer.Typer(help="Terminal control commands.")


@app.command("launch")
def launch(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Session name"),
) -> None:
    """Launch a new terminal session."""
    terminal = get_terminal()
    result = terminal.launch(name=name)
    typer.echo(json.dumps(result, indent=2))


@app.command("send")
def send(
    text: str = typer.Option(..., "--text", "-t", help="Text to send"),
) -> None:
    """Send text to terminal without pressing Enter."""
    terminal = get_terminal()
    result = terminal.send(text)
    typer.echo(json.dumps(result, indent=2))


@app.command("exec")
def exec_cmd(
    command: str = typer.Option(..., "--command", "-c", help="Command to execute"),
    timeout: int = typer.Option(120, "--timeout", help="Timeout in seconds"),
) -> None:
    """Execute a command and wait for completion."""
    terminal = get_terminal()
    result = terminal.exec(command, timeout=timeout)
    typer.echo(json.dumps(result, indent=2))


@app.command("read")
def read(
    lines: int = typer.Option(50, "--lines", "-l", help="Number of lines to read"),
) -> None:
    """Read terminal output."""
    terminal = get_terminal()
    result = terminal.read(lines=lines)
    typer.echo(json.dumps(result, indent=2))


@app.command("wait-for")
def wait_for(
    text: str = typer.Option(..., "--text", "-t", help="Text to wait for"),
    timeout: int = typer.Option(30, "--timeout", help="Timeout in seconds"),
) -> None:
    """Wait for text to appear in terminal."""
    terminal = get_terminal()
    result = terminal.wait_for(text, timeout=timeout)
    typer.echo(json.dumps(result, indent=2))


@app.command("clear")
def clear() -> None:
    """Clear the terminal screen."""
    terminal = get_terminal()
    result = terminal.clear()
    typer.echo(json.dumps(result, indent=2))
