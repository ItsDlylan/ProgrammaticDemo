"""CLI commands for terminal control."""

import json
from typing import Optional

import typer

from programmatic_demo.actuators.terminal import get_terminal

app = typer.Typer(help="Terminal control commands.")


def _get_terminal_with_session(session: Optional[str] = None):
    """Get terminal instance and optionally attach to existing session."""
    terminal = get_terminal()
    if session:
        # Attach to existing session
        terminal.launch(name=session)
    return terminal


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
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session name to use"),
) -> None:
    """Send text to terminal without pressing Enter."""
    terminal = _get_terminal_with_session(session)
    result = terminal.send(text)
    typer.echo(json.dumps(result, indent=2))


@app.command("exec")
def exec_cmd(
    command: str = typer.Option(..., "--command", "-c", help="Command to execute"),
    timeout: int = typer.Option(120, "--timeout", help="Timeout in seconds"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session name to use"),
) -> None:
    """Execute a command and wait for completion."""
    terminal = _get_terminal_with_session(session)
    result = terminal.exec(command, timeout=timeout)
    typer.echo(json.dumps(result, indent=2))


@app.command("read")
def read(
    lines: int = typer.Option(50, "--lines", "-l", help="Number of lines to read"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session name to use"),
) -> None:
    """Read terminal output."""
    terminal = _get_terminal_with_session(session)
    result = terminal.read(lines=lines)
    typer.echo(json.dumps(result, indent=2))


@app.command("wait-for")
def wait_for(
    text: str = typer.Option(..., "--text", "-t", help="Text to wait for"),
    timeout: int = typer.Option(30, "--timeout", help="Timeout in seconds"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session name to use"),
) -> None:
    """Wait for text to appear in terminal."""
    terminal = _get_terminal_with_session(session)
    result = terminal.wait_for(text, timeout=timeout)
    typer.echo(json.dumps(result, indent=2))


@app.command("clear")
def clear(
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session name to use"),
) -> None:
    """Clear the terminal screen."""
    terminal = _get_terminal_with_session(session)
    result = terminal.clear()
    typer.echo(json.dumps(result, indent=2))
