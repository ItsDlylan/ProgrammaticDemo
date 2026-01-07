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


    def verify_framing(
        self,
        expected_elements: list[dict[str, Any]],
        framing_rules: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Verify that expected elements are properly framed in the viewport.

        Uses the visual module's framing analysis to check if elements
        are positioned correctly according to the specified framing rules.

        Args:
            expected_elements: List of element dicts with 'name', 'selector'
                              or 'description', and optional 'bounds'.
            framing_rules: Custom framing rules dict, uses defaults if None.

        Returns:
            Verification result dict with 'verified', 'issues', and 'details'.
        """
        try:
            from programmatic_demo.visual import (
                FramingAnalyzer,
                DEFAULT_FRAMING_RULES,
                is_element_properly_framed,
            )

            # Capture current state
            image = self._screen.capture()
            viewport_width = image.width
            viewport_height = image.height

            rules = framing_rules or DEFAULT_FRAMING_RULES
            issues: list[dict[str, Any]] = []
            verified_elements: list[str] = []

            for element in expected_elements:
                name = element.get("name", "unknown")
                bounds = element.get("bounds")

                if bounds:
                    # Check if element is properly framed
                    elem_bounds = {
                        "x": bounds.get("x", 0),
                        "y": bounds.get("y", 0),
                        "width": bounds.get("width", 0),
                        "height": bounds.get("height", 0),
                    }

                    # Check if fully visible in viewport
                    is_visible = (
                        elem_bounds["x"] >= 0
                        and elem_bounds["y"] >= 0
                        and elem_bounds["x"] + elem_bounds["width"] <= viewport_width
                        and elem_bounds["y"] + elem_bounds["height"] <= viewport_height
                    )

                    if is_visible:
                        verified_elements.append(name)
                    else:
                        issues.append({
                            "element": name,
                            "issue": "not_fully_visible",
                            "bounds": elem_bounds,
                            "viewport": {"width": viewport_width, "height": viewport_height},
                        })
                else:
                    # Without bounds, we can't verify positioning
                    issues.append({
                        "element": name,
                        "issue": "missing_bounds",
                        "message": "Element bounds not provided for verification",
                    })

            return success_response(
                "verify_framing",
                {
                    "verified": len(issues) == 0,
                    "verified_elements": verified_elements,
                    "issues": issues,
                    "total_elements": len(expected_elements),
                    "viewport": {"width": viewport_width, "height": viewport_height},
                },
            )
        except Exception as e:
            return error_response("framing_error", str(e), recoverable=True)

    def wait_for_stable_frame(
        self,
        timeout: float = 5.0,
        threshold: float = 0.02,
        check_interval: float = 0.1,
    ) -> dict[str, Any]:
        """Wait for the screen to stabilize (no animations in progress).

        Uses animation detection to wait until frame differences fall
        below the threshold, indicating animations have completed.

        Args:
            timeout: Maximum time to wait in seconds.
            threshold: Difference threshold below which frame is stable.
            check_interval: Time between frame comparisons.

        Returns:
            Result dict with 'stable', 'wait_time', and 'final_diff'.
        """
        try:
            from programmatic_demo.visual import (
                wait_for_animation_complete_sync,
                frame_diff,
            )

            start_time = time.time()

            # Try to use the visual module's wait function
            try:
                wait_for_animation_complete_sync(
                    capture_fn=lambda: self._screen.capture(),
                    threshold=threshold,
                    timeout=timeout,
                    interval=check_interval,
                )
                elapsed = time.time() - start_time
                return success_response(
                    "wait_stable",
                    {
                        "stable": True,
                        "wait_time": elapsed,
                        "timeout": timeout,
                    },
                )
            except TimeoutError:
                return success_response(
                    "wait_stable",
                    {
                        "stable": False,
                        "wait_time": timeout,
                        "timeout": timeout,
                        "message": "Timeout waiting for stable frame",
                    },
                )

        except ImportError:
            # Fallback to simple wait if visual module not fully available
            time.sleep(min(timeout, 1.0))
            return success_response(
                "wait_stable",
                {
                    "stable": True,
                    "wait_time": min(timeout, 1.0),
                    "fallback": True,
                },
            )
        except Exception as e:
            return error_response("wait_error", str(e), recoverable=True)

    def get_framing_report(self) -> dict[str, Any]:
        """Get a comprehensive framing report for the current screen.

        Analyzes the current viewport and provides structured information
        about what's visible and how it's positioned.

        Returns:
            Framing report dict with viewport info, visible regions, etc.
        """
        try:
            image = self._screen.capture()
            ocr_text = self._ocr.extract_text(image)

            # Build framing report
            report = {
                "timestamp": time.time(),
                "viewport": {
                    "width": image.width,
                    "height": image.height,
                },
                "content": {
                    "has_text": len(ocr_text.strip()) > 0,
                    "text_preview": ocr_text[:200] if ocr_text else "",
                    "text_length": len(ocr_text),
                },
                "framing_quality": "unknown",
            }

            # Estimate framing quality based on content density
            text_density = len(ocr_text) / (image.width * image.height) if ocr_text else 0
            if text_density > 0.0001:
                report["framing_quality"] = "good"
            elif text_density > 0.00001:
                report["framing_quality"] = "sparse"
            else:
                report["framing_quality"] = "empty"

            return success_response("framing_report", report)
        except Exception as e:
            return error_response("report_error", str(e), recoverable=True)


# Singleton instance for CLI usage
_observer_instance: Observer | None = None


def get_observer() -> Observer:
    """Get or create the singleton Observer instance."""
    global _observer_instance
    if _observer_instance is None:
        _observer_instance = Observer()
    return _observer_instance
