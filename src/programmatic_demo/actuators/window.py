"""Window management using yabai."""

import json
import subprocess
from typing import Any

from programmatic_demo.utils.output import error_response, success_response


class Window:
    """Window controller using yabai."""

    def __init__(self) -> None:
        """Initialize the window controller."""
        pass

    def _run_yabai(self, *args: str) -> tuple[int, str, str]:
        """Run a yabai command and return (returncode, stdout, stderr)."""
        cmd = ["yabai", "-m"] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    def get_windows(self) -> list[dict[str, Any]]:
        """Get list of all windows.

        Returns:
            List of dicts with id, title, app, bounds.
        """
        try:
            code, stdout, stderr = self._run_yabai("query", "--windows")

            if code != 0:
                return []

            data = json.loads(stdout)
            windows = []

            for win in data:
                frame = win.get("frame", {})
                windows.append({
                    "id": win.get("id"),
                    "title": win.get("title", ""),
                    "app": win.get("app", ""),
                    "bounds": {
                        "x": frame.get("x", 0),
                        "y": frame.get("y", 0),
                        "width": frame.get("w", 0),
                        "height": frame.get("h", 0),
                    },
                })

            return windows

        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            return []
        except Exception:
            return []

    def focus(self, app_or_title: str) -> dict[str, Any]:
        """Focus a window by app name or title.

        Args:
            app_or_title: Application name or window title to find.

        Returns:
            Success dict with window info, or error dict.
        """
        windows = self.get_windows()

        if not windows:
            return error_response(
                "no_windows",
                "No windows found or yabai not available",
                recoverable=True,
                suggestion="Ensure yabai is installed and running",
            )

        # Search for matching window (case-insensitive)
        search_lower = app_or_title.lower()
        matching_window = None

        for win in windows:
            if (search_lower in win["app"].lower() or
                search_lower in win["title"].lower()):
                matching_window = win
                break

        if not matching_window:
            return error_response(
                "window_not_found",
                f"No window matching '{app_or_title}' found",
                recoverable=True,
                suggestion="Check app name or window title",
            )

        # Focus the window
        try:
            code, _, stderr = self._run_yabai("window", "--focus", str(matching_window["id"]))

            if code != 0:
                return error_response(
                    "focus_failed",
                    f"Failed to focus window: {stderr}",
                    recoverable=True,
                )

            return success_response(
                "window_focus",
                {
                    "window": matching_window,
                },
            )

        except Exception as e:
            return error_response(
                "focus_failed",
                f"Failed to focus window: {str(e)}",
                recoverable=True,
            )


# Singleton instance for CLI usage
_window_instance: Window | None = None


def get_window() -> Window:
    """Get or create the singleton Window instance."""
    global _window_instance
    if _window_instance is None:
        _window_instance = Window()
    return _window_instance
