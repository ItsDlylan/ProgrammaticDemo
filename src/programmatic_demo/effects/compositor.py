"""Video effects compositor for enhancing demo recordings.

The Compositor applies visual effects to demo videos:
- Cursor highlighting and click effects
- Zoom and focus effects
- Text annotations and callouts
- Scene transitions
"""

from bisect import insort_left
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterator


class EffectType(Enum):
    """Types of visual effects that can be applied to video."""

    ZOOM = "zoom"
    RIPPLE = "ripple"
    HIGHLIGHT = "highlight"
    CALLOUT = "callout"
    SPOTLIGHT = "spotlight"


@dataclass
class Effect:
    """A visual effect to apply to a video segment.

    Attributes:
        effect_type: Type of effect (highlight, zoom, annotation, etc.)
        start_time: Start time in seconds
        duration: Duration in seconds
        params: Effect-specific parameters
    """

    effect_type: str
    start_time: float
    duration: float
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class EffectConfig:
    """Configuration for an effect.

    Attributes:
        type: Effect type from EffectType enum
        params: Effect-specific parameters
        duration_ms: Duration in milliseconds
        easing: Easing function name (e.g., "linear", "ease-in-out")
    """

    type: EffectType
    params: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 500
    easing: str = "linear"


@dataclass
class EffectEvent:
    """An effect event at a specific point in time.

    Attributes:
        type: Effect type from EffectType enum
        timestamp_ms: Time in the video in milliseconds
        position: Position (x, y) for the effect
        config: Effect configuration
    """

    type: EffectType
    timestamp_ms: int
    position: tuple[int, int] = (0, 0)
    config: EffectConfig | None = None


@dataclass
class EventQueueItem:
    """An item in the event queue with timestamp ordering.

    Attributes:
        event: The effect event.
        timestamp_ms: Event timestamp for ordering.
    """

    event: EffectEvent
    timestamp_ms: int

    def __lt__(self, other: "EventQueueItem") -> bool:
        """Compare by timestamp for sorted insertion."""
        return self.timestamp_ms < other.timestamp_ms


class EventQueue:
    """A timestamp-ordered queue for effect events.

    Maintains events sorted by timestamp for efficient
    range queries during video processing.
    """

    def __init__(self) -> None:
        """Initialize the EventQueue."""
        self._items: list[EventQueueItem] = []

    def add_event(self, event: EffectEvent) -> None:
        """Add an event to the queue (maintains sort order).

        Args:
            event: Effect event to add.
        """
        item = EventQueueItem(event=event, timestamp_ms=event.timestamp_ms)
        insort_left(self._items, item)

    def get_events_in_range(
        self,
        start_ms: int,
        end_ms: int,
    ) -> list[EffectEvent]:
        """Get all events within a time range.

        Args:
            start_ms: Start of range (inclusive).
            end_ms: End of range (inclusive).

        Returns:
            List of EffectEvent objects in the range.
        """
        return [
            item.event
            for item in self._items
            if start_ms <= item.timestamp_ms <= end_ms
        ]

    def get_events_at(self, timestamp_ms: int) -> list[EffectEvent]:
        """Get all events at a specific timestamp.

        Args:
            timestamp_ms: Timestamp to query.

        Returns:
            List of EffectEvent objects at the timestamp.
        """
        return [
            item.event
            for item in self._items
            if item.timestamp_ms == timestamp_ms
        ]

    def get_active_events(
        self,
        timestamp_ms: int,
        default_duration_ms: int = 500,
    ) -> list[EffectEvent]:
        """Get events that would be active at a timestamp.

        An event is active if timestamp_ms is within its duration.

        Args:
            timestamp_ms: Current timestamp.
            default_duration_ms: Default duration if event doesn't specify.

        Returns:
            List of active EffectEvent objects.
        """
        active = []
        for item in self._items:
            event = item.event
            duration = default_duration_ms
            if event.config and event.config.duration_ms:
                duration = event.config.duration_ms
            if item.timestamp_ms <= timestamp_ms < item.timestamp_ms + duration:
                active.append(event)
        return active

    def clear(self) -> None:
        """Clear all events from the queue."""
        self._items.clear()

    def __len__(self) -> int:
        """Return number of events in the queue."""
        return len(self._items)

    def __iter__(self) -> Iterator[EffectEvent]:
        """Iterate over all events in order."""
        return (item.event for item in self._items)

    @property
    def events(self) -> list[EffectEvent]:
        """Get all events in order."""
        return [item.event for item in self._items]


class Compositor:
    """Applies visual effects to demo videos.

    The Compositor layers effects onto video frames and produces
    enhanced output suitable for product demos.
    """

    def __init__(self) -> None:
        """Initialize the Compositor."""
        self._effects: list[Effect] = []
        self._event_queue: EventQueue = EventQueue()

    @property
    def event_queue(self) -> EventQueue:
        """Get the effect event queue."""
        return self._event_queue

    def add_effect(self, effect: Effect) -> None:
        """Add an effect to the composition.

        Args:
            effect: Effect to add.
        """
        self._effects.append(effect)

    def clear_effects(self) -> None:
        """Clear all effects."""
        self._effects.clear()

    def add_click_highlight(
        self,
        x: int,
        y: int,
        start_time: float,
        duration: float = 0.5,
    ) -> None:
        """Add a click highlight effect at coordinates.

        Args:
            x: X coordinate of click.
            y: Y coordinate of click.
            start_time: When to show the highlight.
            duration: How long to show the highlight.
        """
        raise NotImplementedError("add_click_highlight not yet implemented")

    def add_zoom(
        self,
        x: int,
        y: int,
        scale: float,
        start_time: float,
        duration: float,
    ) -> None:
        """Add a zoom effect centered on coordinates.

        Args:
            x: X coordinate of zoom center.
            y: Y coordinate of zoom center.
            scale: Zoom scale (1.0 = no zoom, 2.0 = 2x zoom).
            start_time: When to start zooming.
            duration: Duration of zoom effect.
        """
        raise NotImplementedError("add_zoom not yet implemented")

    def add_annotation(
        self,
        text: str,
        x: int,
        y: int,
        start_time: float,
        duration: float,
    ) -> None:
        """Add a text annotation at coordinates.

        Args:
            text: Annotation text.
            x: X coordinate for annotation.
            y: Y coordinate for annotation.
            start_time: When to show annotation.
            duration: How long to show annotation.
        """
        raise NotImplementedError("add_annotation not yet implemented")

    def apply_to_video(
        self,
        input_path: str,
        output_path: str,
    ) -> dict[str, Any]:
        """Apply all effects to a video file.

        Args:
            input_path: Path to input video.
            output_path: Path for output video.

        Returns:
            Result dict with success status.
        """
        raise NotImplementedError("apply_to_video not yet implemented")
