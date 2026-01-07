"""CLI commands for browser automation."""

import json
from typing import Optional

import typer

from programmatic_demo.actuators.browser import get_browser

app = typer.Typer(help="Browser automation commands.")


@app.command("launch")
def launch(
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL to navigate to after launch"),
) -> None:
    """Launch browser."""
    browser = get_browser()
    result = browser.launch(url=url)
    typer.echo(json.dumps(result, indent=2))


@app.command("navigate")
def navigate(
    url: str = typer.Option(..., "--url", "-u", help="URL to navigate to"),
) -> None:
    """Navigate to URL."""
    browser = get_browser()
    result = browser.navigate(url)
    typer.echo(json.dumps(result, indent=2))


@app.command("click")
def click(
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector for element"),
) -> None:
    """Click on element."""
    browser = get_browser()
    result = browser.click(selector)
    typer.echo(json.dumps(result, indent=2))


@app.command("fill")
def fill(
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector for input"),
    value: str = typer.Option(..., "--value", "-v", help="Value to fill"),
) -> None:
    """Fill input field."""
    browser = get_browser()
    result = browser.fill(selector, value)
    typer.echo(json.dumps(result, indent=2))


@app.command("wait")
def wait(
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector to wait for"),
    timeout: int = typer.Option(10, "--timeout", "-t", help="Timeout in seconds"),
) -> None:
    """Wait for element to appear."""
    browser = get_browser()
    result = browser.wait_for(selector, timeout=timeout)
    typer.echo(json.dumps(result, indent=2))


@app.command("state")
def state() -> None:
    """Get current browser state."""
    browser = get_browser()
    result = browser.get_state()
    typer.echo(json.dumps(result, indent=2))


@app.command("screenshot")
def screenshot(
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
) -> None:
    """Take screenshot of page."""
    browser = get_browser()
    result = browser.screenshot(output)
    typer.echo(json.dumps(result, indent=2))


@app.command("close")
def close() -> None:
    """Close browser."""
    browser = get_browser()
    result = browser.close()
    typer.echo(json.dumps(result, indent=2))
