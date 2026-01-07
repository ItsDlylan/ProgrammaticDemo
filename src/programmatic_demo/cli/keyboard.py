"""CLI commands for keyboard control."""

import json

import typer

from programmatic_demo.actuators.keyboard import get_keyboard

app = typer.Typer(help="Keyboard control commands.")


@app.command("type")
def type_text(
    text: str = typer.Option(..., "--text", "-t", help="Text to type"),
    delay_ms: int = typer.Option(50, "--delay-ms", "-d", help="Delay between keystrokes in ms"),
) -> None:
    """Type text with human-like delays."""
    keyboard = get_keyboard()
    result = keyboard.type_text(text, delay_ms=delay_ms)
    typer.echo(json.dumps(result, indent=2))


@app.command("press")
def press(
    key: str = typer.Option(..., "--key", "-k", help="Key to press"),
) -> None:
    """Press a key."""
    keyboard = get_keyboard()
    result = keyboard.press(key)
    typer.echo(json.dumps(result, indent=2))


@app.command("hotkey")
def hotkey(
    keys: str = typer.Option(..., "--keys", "-k", help="Key combination (e.g. 'cmd+shift+p')"),
) -> None:
    """Press a key combination."""
    keyboard = get_keyboard()
    result = keyboard.hotkey(keys)
    typer.echo(json.dumps(result, indent=2))
