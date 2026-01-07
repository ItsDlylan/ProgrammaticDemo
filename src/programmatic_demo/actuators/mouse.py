"""Mouse control using pyautogui with bezier curve smoothing."""

import random
import time
from typing import Any

import pyautogui

from programmatic_demo.utils.output import error_response, success_response
from programmatic_demo.utils.timing import hover_pause


def _bezier_point(t: float, p0: tuple, p1: tuple, p2: tuple, p3: tuple) -> tuple:
    """Calculate a point on a cubic bezier curve.

    Args:
        t: Parameter from 0 to 1.
        p0, p1, p2, p3: Control points.

    Returns:
        (x, y) point on the curve.
    """
    u = 1 - t
    x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
    y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def _generate_bezier_path(
    start: tuple, end: tuple, num_points: int = 50
) -> list[tuple]:
    """Generate a bezier curve path between two points.

    Args:
        start: (x, y) start position.
        end: (x, y) end position.
        num_points: Number of points to generate.

    Returns:
        List of (x, y) points along the curve.
    """
    # Calculate midpoint and curve offset
    mid_x = (start[0] + end[0]) / 2
    mid_y = (start[1] + end[1]) / 2

    # Add randomness to control points for natural curve
    dx = end[0] - start[0]
    dy = end[1] - start[1]

    # Control points offset perpendicular to the line
    offset1 = random.uniform(-0.3, 0.3)
    offset2 = random.uniform(-0.3, 0.3)

    # Control point 1 (1/3 of the way)
    cp1 = (
        start[0] + dx * 0.33 + dy * offset1,
        start[1] + dy * 0.33 - dx * offset1,
    )

    # Control point 2 (2/3 of the way)
    cp2 = (
        start[0] + dx * 0.67 + dy * offset2,
        start[1] + dy * 0.67 - dx * offset2,
    )

    # Generate points along the curve
    points = []
    for i in range(num_points + 1):
        t = i / num_points
        point = _bezier_point(t, start, cp1, cp2, end)
        # Add small random jitter
        jitter_x = random.uniform(-1, 1)
        jitter_y = random.uniform(-1, 1)
        points.append((int(point[0] + jitter_x), int(point[1] + jitter_y)))

    return points


class Mouse:
    """Mouse controller with human-like movement."""

    def __init__(self) -> None:
        """Initialize the mouse controller."""
        # Disable pyautogui failsafe for automated use
        pyautogui.FAILSAFE = False

    def move_to(self, x: int, y: int, duration: float = 0.5) -> dict[str, Any]:
        """Move mouse to position with bezier curve.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            duration: Movement duration in seconds.

        Returns:
            Success dict with position.
        """
        try:
            start_pos = pyautogui.position()
            start = (start_pos.x, start_pos.y)
            end = (x, y)

            # Generate bezier path
            num_points = max(10, int(duration * 100))
            path = _generate_bezier_path(start, end, num_points)

            # Calculate delay between points
            delay = duration / len(path)

            # Move through path
            for point in path:
                pyautogui.moveTo(point[0], point[1], _pause=False)
                time.sleep(delay)

            # Ensure we end at the exact target
            pyautogui.moveTo(x, y, _pause=False)

            return success_response(
                "mouse_move",
                {"x": x, "y": y, "duration": duration},
            )
        except Exception as e:
            return error_response(
                "move_failed",
                f"Failed to move mouse: {str(e)}",
                recoverable=True,
            )

    def click(self, button: str = "left", clicks: int = 1) -> dict[str, Any]:
        """Click at current position.

        Args:
            button: Button to click ('left', 'right', 'middle').
            clicks: Number of clicks.

        Returns:
            Success dict with position.
        """
        try:
            # Pause before clicking (human-like)
            time.sleep(hover_pause())

            pos = pyautogui.position()
            pyautogui.click(button=button, clicks=clicks)

            return success_response(
                "mouse_click",
                {"x": pos.x, "y": pos.y, "button": button, "clicks": clicks},
            )
        except Exception as e:
            return error_response(
                "click_failed",
                f"Failed to click: {str(e)}",
                recoverable=True,
            )

    def click_at(self, x: int, y: int, button: str = "left") -> dict[str, Any]:
        """Move to position and click.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            button: Button to click.

        Returns:
            Success dict with position.
        """
        # Move to position first
        move_result = self.move_to(x, y)
        if not move_result.get("success"):
            return move_result

        # Then click
        return self.click(button=button)

    def scroll(self, direction: str, amount: int) -> dict[str, Any]:
        """Scroll in direction.

        Args:
            direction: Scroll direction ('up', 'down', 'left', 'right').
            amount: Scroll amount.

        Returns:
            Success dict.
        """
        try:
            direction_lower = direction.lower()

            # Map direction to scroll delta
            if direction_lower == "up":
                delta = amount
            elif direction_lower == "down":
                delta = -amount
            elif direction_lower == "left":
                pyautogui.hscroll(-amount)
                return success_response(
                    "mouse_scroll",
                    {"direction": direction, "amount": amount},
                )
            elif direction_lower == "right":
                pyautogui.hscroll(amount)
                return success_response(
                    "mouse_scroll",
                    {"direction": direction, "amount": amount},
                )
            else:
                return error_response(
                    "invalid_direction",
                    f"Invalid direction: {direction}",
                    recoverable=True,
                    suggestion="Valid directions: up, down, left, right",
                )

            # Scroll in small increments for smooth animation
            for _ in range(abs(amount)):
                pyautogui.scroll(1 if delta > 0 else -1)
                time.sleep(0.05)

            return success_response(
                "mouse_scroll",
                {"direction": direction, "amount": amount},
            )
        except Exception as e:
            return error_response(
                "scroll_failed",
                f"Failed to scroll: {str(e)}",
                recoverable=True,
            )

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        duration: float = 0.5,
    ) -> dict[str, Any]:
        """Drag from one position to another.

        Args:
            from_x: Start X coordinate.
            from_y: Start Y coordinate.
            to_x: End X coordinate.
            to_y: End Y coordinate.
            duration: Drag duration in seconds.

        Returns:
            Success dict with start and end positions.
        """
        try:
            # Move to start position
            self.move_to(from_x, from_y, duration=0.3)

            # Brief pause before pressing
            time.sleep(hover_pause())

            # Press and hold
            pyautogui.mouseDown()

            # Generate bezier path for drag
            start = (from_x, from_y)
            end = (to_x, to_y)
            num_points = max(10, int(duration * 100))
            path = _generate_bezier_path(start, end, num_points)

            # Move through path while holding
            delay = duration / len(path)
            for point in path:
                pyautogui.moveTo(point[0], point[1], _pause=False)
                time.sleep(delay)

            # Ensure we end at the exact target
            pyautogui.moveTo(to_x, to_y, _pause=False)

            # Release
            pyautogui.mouseUp()

            return success_response(
                "mouse_drag",
                {
                    "from": {"x": from_x, "y": from_y},
                    "to": {"x": to_x, "y": to_y},
                    "duration": duration,
                },
            )
        except Exception as e:
            # Make sure to release mouse if error occurs
            pyautogui.mouseUp()
            return error_response(
                "drag_failed",
                f"Failed to drag: {str(e)}",
                recoverable=True,
            )


# Singleton instance for CLI usage
_mouse_instance: Mouse | None = None


def get_mouse() -> Mouse:
    """Get or create the singleton Mouse instance."""
    global _mouse_instance
    if _mouse_instance is None:
        _mouse_instance = Mouse()
    return _mouse_instance
