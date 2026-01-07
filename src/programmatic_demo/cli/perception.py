"""CLI commands for observation and perception."""

import json
from typing import Optional

import typer

from programmatic_demo.sensors.screen import get_screen
from programmatic_demo.sensors.ocr import get_ocr
from programmatic_demo.sensors.state import get_observer
from programmatic_demo.utils.output import success_response

app = typer.Typer(help="Observation and perception commands.")


@app.command("screenshot")
def screenshot(
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
) -> None:
    """Capture screenshot and save to file."""
    screen = get_screen()
    image = screen.capture()
    result = screen.save(image, output)
    typer.echo(json.dumps(result, indent=2))


@app.command("ocr")
def ocr(
    screenshot_path: Optional[str] = typer.Option(None, "--screenshot", "-s", help="Path to screenshot (captures new if not provided)"),
) -> None:
    """Extract text from screen using OCR."""
    screen = get_screen()
    ocr_instance = get_ocr()

    if screenshot_path:
        from PIL import Image
        image = Image.open(screenshot_path)
    else:
        image = screen.capture()

    text = ocr_instance.extract_text(image)
    elements = ocr_instance.extract_elements(image)

    result = success_response(
        "ocr",
        {
            "text": text,
            "elements": elements,
            "element_count": len(elements),
        },
    )
    typer.echo(json.dumps(result, indent=2))


@app.command("window")
def window() -> None:
    """Get active window information."""
    observer = get_observer()
    result = observer.get_window_info()
    typer.echo(json.dumps(result, indent=2))


@app.command("full")
def full() -> None:
    """Get full observation (screenshot, OCR, window, terminal)."""
    observer = get_observer()
    result = observer.get_observation()
    typer.echo(json.dumps(result, indent=2))
