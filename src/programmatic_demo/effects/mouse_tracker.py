"""Mouse position and click tracking for visual effects.

Tracks mouse movements and clicks to enable visual effects
like click highlights, cursor trails, and hover indicators.
"""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class MouseEvent:
    """A mouse event (click or movement).

    Attributes:
        x: X coordinate of the event.
        y: Y coordinate of the event.
        timestamp: Timestamp of the event in milliseconds.
        event_type: Type of event (click, move, drag).
        button: Mouse button (left, right, middle) for click events.
    """

    x: int
    y: int
    timestamp: float
    event_type: str = "move"
    button: str = "left"


class MouseTracker:
    """Tracks mouse position and click events for effects.

    Records mouse movements and clicks for later use in
    generating visual effects like click highlights and cursor trails.
    """

    def __init__(self) -> None:
        """Initialize the MouseTracker."""
        self._is_tracking = False
        self._events: list[MouseEvent] = []
        self._click_callbacks: list[Callable[[MouseEvent], None]] = []
        self._move_callbacks: list[Callable[[MouseEvent], None]] = []
        self._current_position: tuple[int, int] = (0, 0)

    @property
    def is_tracking(self) -> bool:
        """Whether tracking is currently active."""
        return self._is_tracking

    @property
    def events(self) -> list[MouseEvent]:
        """Get all recorded events."""
        return self._events.copy()

    def start(self) -> None:
        """Start tracking mouse events."""
        self._is_tracking = True
        self._events.clear()

    def stop(self) -> None:
        """Stop tracking mouse events."""
        self._is_tracking = False

    def get_position(self) -> tuple[int, int]:
        """Get the current mouse position.

        Returns:
            Tuple of (x, y) coordinates.
        """
        return self._current_position

    def on_click(self, callback: Callable[[MouseEvent], None]) -> None:
        """Register a callback for click events.

        Args:
            callback: Function to call when a click occurs.
        """
        self._click_callbacks.append(callback)

    def on_move(self, callback: Callable[[MouseEvent], None]) -> None:
        """Register a callback for move events.

        Args:
            callback: Function to call when the mouse moves.
        """
        self._move_callbacks.append(callback)

    def record_click(
        self,
        x: int,
        y: int,
        timestamp: float,
        button: str = "left",
    ) -> None:
        """Record a click event.

        Args:
            x: X coordinate.
            y: Y coordinate.
            timestamp: Timestamp in milliseconds.
            button: Mouse button that was clicked.
        """
        if not self._is_tracking:
            return

        event = MouseEvent(
            x=x,
            y=y,
            timestamp=timestamp,
            event_type="click",
            button=button,
        )
        self._events.append(event)
        self._current_position = (x, y)

        for callback in self._click_callbacks:
            callback(event)

    def record_move(self, x: int, y: int, timestamp: float) -> None:
        """Record a mouse movement.

        Args:
            x: X coordinate.
            y: Y coordinate.
            timestamp: Timestamp in milliseconds.
        """
        if not self._is_tracking:
            return

        event = MouseEvent(
            x=x,
            y=y,
            timestamp=timestamp,
            event_type="move",
        )
        self._events.append(event)
        self._current_position = (x, y)

        for callback in self._move_callbacks:
            callback(event)

    def get_clicks(self) -> list[MouseEvent]:
        """Get all recorded click events.

        Returns:
            List of click events.
        """
        return [e for e in self._events if e.event_type == "click"]

    def get_path(
        self,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> list[tuple[int, int]]:
        """Get the mouse path as a list of coordinates.

        Args:
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            List of (x, y) coordinate tuples.
        """
        events = self._events
        if start_time is not None:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time is not None:
            events = [e for e in events if e.timestamp <= end_time]
        return [(e.x, e.y) for e in events]

    def clear(self) -> None:
        """Clear all recorded events."""
        self._events.clear()
        self._click_callbacks.clear()
        self._move_callbacks.clear()


# Singleton instance
_tracker: MouseTracker | None = None


def get_mouse_tracker() -> MouseTracker:
    """Get or create the singleton MouseTracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = MouseTracker()
    return _tracker
