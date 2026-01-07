"""Unified observation state collection."""

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from programmatic_demo.sensors.ocr import OCR, get_ocr
from programmatic_demo.sensors.screen import Screen, get_screen
from programmatic_demo.utils.output import error_response, success_response


class Observer:
    """Unified observer for collecting screen state."""

    def __init__(
        self,
        screen: Screen | None = None,
        ocr: OCR | None = None,
    ) -> None:
        """Initialize the observer.

        Args:
            screen: Screen instance (uses singleton if None).
            ocr: OCR instance (uses singleton if None).
        """
        self._screen = screen or get_screen()
        self._ocr = ocr or get_ocr()

    def get_window_info(self) -> dict[str, Any]:
        """Get active window information using yabai.

        Returns:
            Dict with title, app, bounds, or error info.
        """
        try:
            result = subprocess.run(
                ["yabai", "-m", "query", "--windows", "--window"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return {
                    "error": "yabai_not_available",
                    "message": result.stderr or "yabai command failed",
                }

            data = json.loads(result.stdout)

            return {
                "title": data.get("title", ""),
                "app": data.get("app", ""),
                "bounds": {
                    "x": data.get("frame", {}).get("x", 0),
                    "y": data.get("frame", {}).get("y", 0),
                    "width": data.get("frame", {}).get("w", 0),
                    "height": data.get("frame", {}).get("h", 0),
                },
            }
        except FileNotFoundError:
            return {
                "error": "yabai_not_installed",
                "message": "yabai is not installed",
            }
        except json.JSONDecodeError:
            return {
                "error": "parse_error",
                "message": "Failed to parse yabai output",
            }
        except Exception as e:
            return {
                "error": "unknown_error",
                "message": str(e),
            }

    def get_observation(self) -> dict[str, Any]:
        """Get full observation including screenshot, OCR, terminal, window.

        Returns:
            Complete observation dict.
        """
        timestamp = time.time()

        # Capture screenshot
        image = self._screen.capture()

        # Save to temp file
        temp_path = Path(tempfile.gettempdir()) / f"pdemo_obs_{int(timestamp)}.png"
        save_result = self._screen.save(image, str(temp_path))

        # Get base64 of screenshot
        base64_data = self._screen.to_base64(image)

        # Extract OCR text
        ocr_text = self._ocr.extract_text(image)

        # Get terminal output if available
        terminal_output = None
        try:
            from programmatic_demo.actuators.terminal import get_terminal
            terminal = get_terminal()
            if terminal._session_name:
                read_result = terminal.read(lines=50)
                if read_result.get("success"):
                    terminal_output = read_result.get("result", {}).get("output")
        except Exception:
            pass

        # Get window info
        window_info = self.get_window_info()

        return success_response(
            "observe_full",
            {
                "timestamp": timestamp,
                "screenshot": {
                    "path": str(temp_path) if save_result.get("success") else None,
                    "base64": base64_data,
                    "dimensions": {
                        "width": image.width,
                        "height": image.height,
                    },
                },
                "ocr_text": ocr_text,
                "terminal_output": terminal_output,
                "active_window": window_info,
            },
        )


# Singleton instance for CLI usage
_observer_instance: Observer | None = None


def get_observer() -> Observer:
    """Get or create the singleton Observer instance."""
    global _observer_instance
    if _observer_instance is None:
        _observer_instance = Observer()
    return _observer_instance
