"""Browser automation using Playwright."""

from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from programmatic_demo.utils.output import error_response, success_response


class Browser:
    """Browser controller using Playwright in headful mode."""

    def __init__(self) -> None:
        """Initialize the browser controller."""
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    def _ensure_browser(self) -> dict[str, Any] | None:
        """Check if browser is running, return error dict if not."""
        if self._page is None:
            return error_response(
                "no_browser",
                "Browser is not running",
                recoverable=True,
                suggestion="Launch browser first with 'pdemo browser launch'",
            )
        return None

    def launch(self, url: str | None = None) -> dict[str, Any]:
        """Launch browser and optionally navigate to URL.

        Args:
            url: Optional URL to navigate to after launch.

        Returns:
            Success dict with browser info.
        """
        try:
            # Close existing browser if any
            if self._browser is not None:
                self.close()

            # Start Playwright
            self._playwright = sync_playwright().start()

            # Launch Chromium in headful mode, fullscreen
            self._browser = self._playwright.chromium.launch(
                headless=False,
                args=["--start-maximized", "--start-fullscreen"],
            )

            # Create context with no fixed viewport so it uses full screen size
            self._context = self._browser.new_context(
                no_viewport=True,
            )
            self._page = self._context.new_page()

            result = {
                "browser": "chromium",
                "headless": False,
            }

            # Navigate to URL if provided
            if url:
                self._page.goto(url, wait_until="domcontentloaded")
                result["url"] = url
                result["title"] = self._page.title()

            return success_response("browser_launch", result)

        except Exception as e:
            return error_response(
                "launch_failed",
                f"Failed to launch browser: {str(e)}",
                recoverable=True,
                suggestion="Ensure Playwright browsers are installed: playwright install chromium",
            )

    def navigate(self, url: str) -> dict[str, Any]:
        """Navigate to URL.

        Args:
            url: URL to navigate to.

        Returns:
            Success dict with url and title.
        """
        error = self._ensure_browser()
        if error:
            return error

        try:
            self._page.goto(url, wait_until="domcontentloaded")

            return success_response(
                "browser_navigate",
                {
                    "url": self._page.url,
                    "title": self._page.title(),
                },
            )
        except Exception as e:
            return error_response(
                "navigate_failed",
                f"Failed to navigate: {str(e)}",
                recoverable=True,
            )

    def click(self, selector: str) -> dict[str, Any]:
        """Click on element.

        Args:
            selector: CSS selector for element.

        Returns:
            Success dict.
        """
        error = self._ensure_browser()
        if error:
            return error

        try:
            self._page.click(selector)

            return success_response(
                "browser_click",
                {"selector": selector},
            )
        except PlaywrightTimeout:
            return error_response(
                "element_not_found",
                f"Element not found: {selector}",
                recoverable=True,
                suggestion="Check selector or wait for element to appear",
            )
        except Exception as e:
            return error_response(
                "click_failed",
                f"Failed to click: {str(e)}",
                recoverable=True,
            )

    def fill(self, selector: str, value: str) -> dict[str, Any]:
        """Fill input field.

        Args:
            selector: CSS selector for input.
            value: Value to fill.

        Returns:
            Success dict.
        """
        error = self._ensure_browser()
        if error:
            return error

        try:
            self._page.fill(selector, value)

            return success_response(
                "browser_fill",
                {"selector": selector, "value": value},
            )
        except PlaywrightTimeout:
            return error_response(
                "element_not_found",
                f"Input element not found: {selector}",
                recoverable=True,
            )
        except Exception as e:
            return error_response(
                "fill_failed",
                f"Failed to fill: {str(e)}",
                recoverable=True,
            )

    def wait_for(self, selector: str, timeout: int = 10) -> dict[str, Any]:
        """Wait for element to appear.

        Args:
            selector: CSS selector to wait for.
            timeout: Timeout in seconds.

        Returns:
            Success dict, or error dict on timeout.
        """
        error = self._ensure_browser()
        if error:
            return error

        try:
            self._page.wait_for_selector(selector, timeout=timeout * 1000)

            return success_response(
                "browser_wait_for",
                {"selector": selector, "found": True},
            )
        except PlaywrightTimeout:
            return error_response(
                "timeout",
                f"Element '{selector}' not found after {timeout}s",
                recoverable=True,
            )
        except Exception as e:
            return error_response(
                "wait_failed",
                f"Failed to wait: {str(e)}",
                recoverable=True,
            )

    def get_state(self) -> dict[str, Any]:
        """Get current browser state.

        Returns:
            Dict with url, title, viewport.
        """
        error = self._ensure_browser()
        if error:
            return error

        try:
            viewport = self._page.viewport_size

            return success_response(
                "browser_state",
                {
                    "url": self._page.url,
                    "title": self._page.title(),
                    "viewport": viewport,
                },
            )
        except Exception as e:
            return error_response(
                "state_failed",
                f"Failed to get state: {str(e)}",
                recoverable=True,
            )

    def screenshot(self, path: str) -> dict[str, Any]:
        """Take screenshot of page.

        Args:
            path: Output file path.

        Returns:
            Success dict with path and size.
        """
        error = self._ensure_browser()
        if error:
            return error

        try:
            file_path = Path(path).resolve()

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            self._page.screenshot(path=str(file_path))

            # Get file size
            file_size = file_path.stat().st_size

            return success_response(
                "browser_screenshot",
                {
                    "path": str(file_path),
                    "size": file_size,
                },
            )
        except Exception as e:
            return error_response(
                "screenshot_failed",
                f"Failed to take screenshot: {str(e)}",
                recoverable=True,
            )

    def close(self) -> dict[str, Any]:
        """Close browser.

        Returns:
            Success dict.
        """
        try:
            if self._page:
                self._page.close()
                self._page = None

            if self._context:
                self._context.close()
                self._context = None

            if self._browser:
                self._browser.close()
                self._browser = None

            if self._playwright:
                self._playwright.stop()
                self._playwright = None

            return success_response("browser_close", {})

        except Exception as e:
            # Force cleanup
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None

            return error_response(
                "close_failed",
                f"Error during close: {str(e)}",
                recoverable=True,
            )


# Singleton instance for CLI usage
_browser_instance: Browser | None = None


def get_browser() -> Browser:
    """Get or create the singleton Browser instance."""
    global _browser_instance
    if _browser_instance is None:
        _browser_instance = Browser()
    return _browser_instance
