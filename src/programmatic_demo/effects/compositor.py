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

    def build_filter_chain(
        self,
        video_width: int = 1920,
        video_height: int = 1080,
    ) -> str:
        """Build FFmpeg filter chain from all queued effect events.

        Converts all effect events in the queue to FFmpeg filter strings
        and chains them together in the correct order for video processing.

        Args:
            video_width: Width of the video in pixels.
            video_height: Height of the video in pixels.

        Returns:
            FFmpeg filter_complex string ready for use with ffmpeg -filter_complex.
            Returns empty string if no effects are queued.
        """
        from programmatic_demo.effects.highlight import Highlight, HighlightConfig
        from programmatic_demo.effects.click_effect import ClickEffect, ClickEffectConfig
        from programmatic_demo.effects.zoom_effect import ZoomEffect, ZoomEffectConfig
        from programmatic_demo.effects.callout import CalloutEffect, Callout, CalloutPosition

        filters: list[str] = []

        # Group events by type for efficient processing
        highlight_events: list[EffectEvent] = []
        ripple_events: list[EffectEvent] = []
        zoom_events: list[EffectEvent] = []
        spotlight_events: list[EffectEvent] = []
        callout_events: list[EffectEvent] = []

        for event in self._event_queue:
            if event.type == EffectType.HIGHLIGHT:
                highlight_events.append(event)
            elif event.type == EffectType.RIPPLE:
                ripple_events.append(event)
            elif event.type == EffectType.ZOOM:
                zoom_events.append(event)
            elif event.type == EffectType.SPOTLIGHT:
                spotlight_events.append(event)
            elif event.type == EffectType.CALLOUT:
                callout_events.append(event)

        # Process highlight effects
        for event in highlight_events:
            config = event.config
            duration_ms = config.duration_ms if config else 500
            start_sec = event.timestamp_ms / 1000.0
            end_sec = start_sec + duration_ms / 1000.0

            # Get dimensions from config params or use defaults
            width = config.params.get("width", 100) if config else 100
            height = config.params.get("height", 50) if config else 50
            color = config.params.get("color", "FFEB3B") if config else "FFEB3B"
            opacity = config.params.get("opacity", 0.3) if config else 0.3

            x = event.position[0]
            y = event.position[1]

            filter_str = (
                f"drawbox=x={x}:y={y}:w={width}:h={height}:"
                f"color={color}@{opacity}:t=fill:"
                f"enable='between(t,{start_sec},{end_sec})'"
            )
            filters.append(filter_str)

        # Process ripple/click effects
        for event in ripple_events:
            config = event.config
            duration_ms = config.duration_ms if config else 300
            start_sec = event.timestamp_ms / 1000.0
            end_sec = start_sec + duration_ms / 1000.0

            radius = config.params.get("radius", 30) if config else 30
            color = config.params.get("color", "FF5722") if config else "FF5722"

            x = event.position[0]
            y = event.position[1]

            # Simplified ripple as a circle that fades
            filter_str = (
                f"drawbox=x={x-radius}:y={y-radius}:w={radius*2}:h={radius*2}:"
                f"color={color}@0.5:t=2:"
                f"enable='between(t,{start_sec},{end_sec})'"
            )
            filters.append(filter_str)

        # Process zoom effects
        for event in zoom_events:
            config = event.config
            duration_ms = config.duration_ms if config else 500

            zoom_factor = config.params.get("zoom_factor", 1.5) if config else 1.5
            start_sec = event.timestamp_ms / 1000.0

            # Calculate normalized center from position
            center_x = event.position[0] / video_width
            center_y = event.position[1] / video_height

            # Zoompan filter for zoom effect
            num_frames = max(1, duration_ms // 16)
            filter_str = (
                f"zoompan=z='1+({zoom_factor-1})*on/{num_frames}':"
                f"x='(iw-iw/zoom)*{center_x}':"
                f"y='(ih-ih/zoom)*{center_y}':"
                f"d={num_frames}:s={video_width}x{video_height}"
            )
            filters.append(filter_str)

        # Process spotlight effects
        for event in spotlight_events:
            config = event.config
            duration_ms = config.duration_ms if config else 500
            start_sec = event.timestamp_ms / 1000.0
            end_sec = start_sec + duration_ms / 1000.0

            # Spotlight dims area outside the focus region
            width = config.params.get("width", 200) if config else 200
            height = config.params.get("height", 100) if config else 100
            dim_opacity = config.params.get("dim_opacity", 0.5) if config else 0.5

            x = event.position[0]
            y = event.position[1]

            # Create dimmed overlay around spotlight
            # Top area
            filter_str = (
                f"drawbox=x=0:y=0:w={video_width}:h={y}:"
                f"color=000000@{dim_opacity}:t=fill:"
                f"enable='between(t,{start_sec},{end_sec})'"
            )
            filters.append(filter_str)
            # Bottom area
            bottom_y = y + height
            filter_str = (
                f"drawbox=x=0:y={bottom_y}:w={video_width}:h={video_height-bottom_y}:"
                f"color=000000@{dim_opacity}:t=fill:"
                f"enable='between(t,{start_sec},{end_sec})'"
            )
            filters.append(filter_str)
            # Left area
            filter_str = (
                f"drawbox=x=0:y={y}:w={x}:h={height}:"
                f"color=000000@{dim_opacity}:t=fill:"
                f"enable='between(t,{start_sec},{end_sec})'"
            )
            filters.append(filter_str)
            # Right area
            right_x = x + width
            filter_str = (
                f"drawbox=x={right_x}:y={y}:w={video_width-right_x}:h={height}:"
                f"color=000000@{dim_opacity}:t=fill:"
                f"enable='between(t,{start_sec},{end_sec})'"
            )
            filters.append(filter_str)

        # Process callout effects
        for event in callout_events:
            config = event.config
            duration_ms = config.duration_ms if config else 3000
            start_sec = event.timestamp_ms / 1000.0
            end_sec = start_sec + duration_ms / 1000.0

            text = config.params.get("text", "") if config else ""
            font_size = config.params.get("font_size", 16) if config else 16
            text_color = config.params.get("text_color", "FFFFFF") if config else "FFFFFF"

            # Escape special characters for FFmpeg
            text = text.replace("'", "\\'").replace(":", "\\:")

            x = event.position[0]
            y = event.position[1]

            filter_str = (
                f"drawtext=text='{text}':"
                f"x={x}:y={y}:fontsize={font_size}:fontcolor={text_color}:"
                f"enable='between(t,{start_sec},{end_sec})'"
            )
            filters.append(filter_str)

        # Also process effects from the _effects list
        for effect in self._effects:
            effect_type = effect.effect_type
            start = effect.start_time
            end = start + effect.duration

            if effect_type == "highlight":
                x = effect.params.get("x", 0)
                y = effect.params.get("y", 0)
                w = effect.params.get("width", 100)
                h = effect.params.get("height", 50)
                color = effect.params.get("color", "FFEB3B").lstrip("#")
                opacity = effect.params.get("opacity", 0.3)

                filter_str = (
                    f"drawbox=x={x}:y={y}:w={w}:h={h}:"
                    f"color={color}@{opacity}:t=fill:"
                    f"enable='between(t,{start},{end})'"
                )
                filters.append(filter_str)

            elif effect_type == "zoom":
                zoom = effect.params.get("zoom_factor", 1.5)
                cx = effect.params.get("center_x", 0.5)
                cy = effect.params.get("center_y", 0.5)
                frames = max(1, int(effect.duration * 60))

                filter_str = (
                    f"zoompan=z='1+({zoom-1})*on/{frames}':"
                    f"x='(iw-iw/zoom)*{cx}':"
                    f"y='(ih-ih/zoom)*{cy}':"
                    f"d={frames}:s={video_width}x{video_height}"
                )
                filters.append(filter_str)

            elif effect_type == "callout":
                text = effect.params.get("text", "").replace("'", "\\'").replace(":", "\\:")
                x = effect.params.get("x", 0)
                y = effect.params.get("y", 0)
                font_size = effect.params.get("font_size", 16)
                color = effect.params.get("text_color", "FFFFFF").lstrip("#")

                filter_str = (
                    f"drawtext=text='{text}':"
                    f"x={x}:y={y}:fontsize={font_size}:fontcolor={color}:"
                    f"enable='between(t,{start},{end})'"
                )
                filters.append(filter_str)

        # Chain filters together
        if not filters:
            return ""

        return ",".join(filters)

    def apply_to_video(
        self,
        input_path: str,
        output_path: str,
        video_width: int = 1920,
        video_height: int = 1080,
    ) -> dict[str, Any]:
        """Apply all effects to a video file.

        Uses FFmpeg to apply the effect filter chain to the input video
        and produce an output video with all effects rendered.

        Args:
            input_path: Path to input video.
            output_path: Path for output video.
            video_width: Video width for effect calculations.
            video_height: Video height for effect calculations.

        Returns:
            Result dict with success status.
        """
        import os
        import subprocess

        if not os.path.exists(input_path):
            return {"success": False, "error": f"Input file not found: {input_path}"}

        filter_chain = self.build_filter_chain(video_width, video_height)

        if not filter_chain:
            # No effects to apply, just copy the file
            try:
                cmd = ["ffmpeg", "-y", "-i", input_path, "-c", "copy", output_path]
                subprocess.run(cmd, capture_output=True, check=True)
                return {"success": True, "output": output_path, "effects_applied": 0}
            except subprocess.CalledProcessError as e:
                return {"success": False, "error": e.stderr.decode() if e.stderr else str(e)}

        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vf", filter_chain,
                "-c:a", "copy",
                output_path,
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            effects_count = len(self._effects) + len(self._event_queue)
            return {"success": True, "output": output_path, "effects_applied": effects_count}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr.decode() if e.stderr else str(e)}

    def apply_effects(
        self,
        input_path: str,
        output_path: str,
        mode: str = "post",
        video_width: int = 1920,
        video_height: int = 1080,
    ) -> dict[str, Any]:
        """Apply effects to a video using specified mode.

        This is the main entry point for effect rendering, supporting
        different rendering modes for various use cases.

        Args:
            input_path: Path to input video.
            output_path: Path for output video.
            mode: Rendering mode - "post" for post-processing,
                  "realtime" for frame-by-frame (placeholder).
            video_width: Video width for effect calculations.
            video_height: Video height for effect calculations.

        Returns:
            Result dict with success status and rendering info.
        """
        if mode == "post":
            result = self.apply_to_video(input_path, output_path, video_width, video_height)
            result["mode"] = "post"
            return result
        elif mode == "realtime":
            # Realtime mode is a placeholder for future frame-by-frame rendering
            # This would integrate with the recorder for live effect application
            return {
                "success": False,
                "error": "Realtime mode not yet implemented",
                "mode": "realtime",
            }
        else:
            return {"success": False, "error": f"Unknown mode: {mode}"}

    def get_effect_summary(self) -> dict[str, Any]:
        """Get a summary of all configured effects.

        Returns:
            Dict with effect counts and types.
        """
        event_types: dict[str, int] = {}
        for event in self._event_queue:
            type_name = event.type.value
            event_types[type_name] = event_types.get(type_name, 0) + 1

        effect_types: dict[str, int] = {}
        for effect in self._effects:
            effect_types[effect.effect_type] = effect_types.get(effect.effect_type, 0) + 1

        return {
            "total_events": len(self._event_queue),
            "total_effects": len(self._effects),
            "event_types": event_types,
            "effect_types": effect_types,
        }
