"""CLI commands for mouse control."""

import json

import typer

from programmatic_demo.actuators.mouse import get_mouse

app = typer.Typer(help="Mouse control commands.")


@app.command("move")
def move(
    x: int = typer.Option(..., "--x", help="Target X coordinate"),
    y: int = typer.Option(..., "--y", help="Target Y coordinate"),
    duration: float = typer.Option(0.5, "--duration", "-d", help="Movement duration in seconds"),
) -> None:
    """Move mouse to position with smooth bezier curve."""
    mouse = get_mouse()
    result = mouse.move_to(x, y, duration=duration)
    typer.echo(json.dumps(result, indent=2))


@app.command("click")
def click(
    x: int = typer.Option(None, "--x", help="X coordinate (optional, uses current position)"),
    y: int = typer.Option(None, "--y", help="Y coordinate (optional, uses current position)"),
    button: str = typer.Option("left", "--button", "-b", help="Button to click"),
    clicks: int = typer.Option(1, "--clicks", "-c", help="Number of clicks"),
) -> None:
    """Click at position."""
    mouse = get_mouse()
    if x is not None and y is not None:
        result = mouse.click_at(x, y, button=button)
    else:
        result = mouse.click(button=button, clicks=clicks)
    typer.echo(json.dumps(result, indent=2))


@app.command("scroll")
def scroll(
    direction: str = typer.Option(..., "--direction", "-d", help="Scroll direction (up/down/left/right)"),
    amount: int = typer.Option(3, "--amount", "-a", help="Scroll amount"),
) -> None:
    """Scroll in direction."""
    mouse = get_mouse()
    result = mouse.scroll(direction, amount)
    typer.echo(json.dumps(result, indent=2))


@app.command("drag")
def drag(
    from_x: int = typer.Option(..., "--from-x", help="Start X coordinate"),
    from_y: int = typer.Option(..., "--from-y", help="Start Y coordinate"),
    to_x: int = typer.Option(..., "--to-x", help="End X coordinate"),
    to_y: int = typer.Option(..., "--to-y", help="End Y coordinate"),
    duration: float = typer.Option(0.5, "--duration", "-d", help="Drag duration in seconds"),
) -> None:
    """Drag from one position to another."""
    mouse = get_mouse()
    result = mouse.drag(from_x, from_y, to_x, to_y, duration=duration)
    typer.echo(json.dumps(result, indent=2))
