"""Callout effects for text annotations in demo videos.

Generates callout effects to annotate and explain
elements on screen during demos.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CalloutConfig:
    """Configuration for callout effects.

    Attributes:
        font: Font family name.
        font_size: Font size in points.
        text_color: Text color as hex string.
        bg_color: Background color.
        bg_opacity: Background opacity (0.0-1.0).
        border_color: Border color.
        border_width: Border width in pixels.
        padding: Padding around text in pixels.
        corner_radius: Corner radius for rounded background.
        arrow_size: Arrow size in pixels (0 for no arrow).
        max_width: Maximum width before text wrapping.
        animation: Animation type (none, fade, slide, pop).
        animation_duration_ms: Animation duration in milliseconds.
    """

    font: str = "Arial"
    font_size: int = 16
    text_color: str = "#FFFFFF"
    bg_color: str = "#333333"
    bg_opacity: float = 0.9
    border_color: str = "#555555"
    border_width: int = 1
    padding: int = 12
    corner_radius: int = 6
    arrow_size: int = 10
    max_width: int = 300
    animation: str = "fade"
    animation_duration_ms: int = 200


@dataclass
class CalloutPosition:
    """Position of a callout relative to its target.

    Attributes:
        x: X coordinate of the callout.
        y: Y coordinate of the callout.
        target_x: X coordinate of the target point.
        target_y: Y coordinate of the target point.
        placement: Placement relative to target (top, bottom, left, right).
    """

    x: int
    y: int
    target_x: int
    target_y: int
    placement: str = "top"


@dataclass
class Callout:
    """A callout annotation on the screen.

    Attributes:
        text: The callout text content.
        position: Position configuration.
        start_time_ms: When the callout appears.
        end_time_ms: When the callout disappears.
        config: Callout styling configuration.
    """

    text: str
    position: CalloutPosition
    start_time_ms: float = 0.0
    end_time_ms: float | None = None
    config: CalloutConfig | None = None


class CalloutEffect:
    """Generates callout effects for annotations.

    Creates text callouts with optional arrows pointing
    to specific screen elements.
    """

    def __init__(self, config: CalloutConfig | None = None) -> None:
        """Initialize the CalloutEffect generator.

        Args:
            config: Effect configuration, uses defaults if None.
        """
        self._config = config or CalloutConfig()
        self._callouts: list[Callout] = []

    @property
    def config(self) -> CalloutConfig:
        """Get the callout configuration."""
        return self._config

    @property
    def callouts(self) -> list[Callout]:
        """Get all registered callouts."""
        return self._callouts.copy()

    def add_callout(
        self,
        text: str,
        target_x: int,
        target_y: int,
        placement: str = "top",
        start_time_ms: float = 0.0,
        end_time_ms: float | None = None,
        offset: int = 20,
    ) -> Callout:
        """Add a callout annotation.

        Args:
            text: Callout text content.
            target_x: X coordinate of the target element.
            target_y: Y coordinate of the target element.
            placement: Placement relative to target.
            start_time_ms: When to show the callout.
            end_time_ms: When to hide the callout.
            offset: Distance from target in pixels.

        Returns:
            The created Callout object.
        """
        # Calculate callout position based on placement
        x, y = self._calculate_position(target_x, target_y, placement, offset)

        position = CalloutPosition(
            x=x,
            y=y,
            target_x=target_x,
            target_y=target_y,
            placement=placement,
        )

        callout = Callout(
            text=text,
            position=position,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            config=self._config,
        )
        self._callouts.append(callout)
        return callout

    def add_tooltip(
        self,
        text: str,
        x: int,
        y: int,
        duration_ms: float = 3000.0,
    ) -> Callout:
        """Add a tooltip-style callout.

        Args:
            text: Tooltip text.
            x: X coordinate.
            y: Y coordinate.
            duration_ms: How long to show the tooltip.

        Returns:
            The created Callout object.
        """
        return self.add_callout(
            text=text,
            target_x=x,
            target_y=y,
            placement="top",
            start_time_ms=0.0,
            end_time_ms=duration_ms,
        )

    def add_step_indicator(
        self,
        step_number: int,
        text: str,
        x: int,
        y: int,
        start_time_ms: float = 0.0,
        end_time_ms: float | None = None,
    ) -> Callout:
        """Add a numbered step indicator callout.

        Args:
            step_number: Step number to display.
            text: Step description.
            x: X coordinate.
            y: Y coordinate.
            start_time_ms: When to show.
            end_time_ms: When to hide.

        Returns:
            The created Callout object.
        """
        full_text = f"{step_number}. {text}"
        return self.add_callout(
            text=full_text,
            target_x=x,
            target_y=y,
            placement="right",
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
        )

    def _calculate_position(
        self,
        target_x: int,
        target_y: int,
        placement: str,
        offset: int,
    ) -> tuple[int, int]:
        """Calculate callout position based on placement.

        Args:
            target_x: Target X coordinate.
            target_y: Target Y coordinate.
            placement: Placement direction.
            offset: Offset from target.

        Returns:
            Tuple of (x, y) coordinates for the callout.
        """
        if placement == "top":
            return (target_x, target_y - offset)
        elif placement == "bottom":
            return (target_x, target_y + offset)
        elif placement == "left":
            return (target_x - offset, target_y)
        elif placement == "right":
            return (target_x + offset, target_y)
        else:
            return (target_x, target_y - offset)  # Default to top

    def clear(self) -> None:
        """Clear all callouts."""
        self._callouts.clear()

    def generate_callout_dict(self, callout: Callout) -> dict[str, Any]:
        """Generate a dict representation of a callout.

        Args:
            callout: Callout to convert.

        Returns:
            Dict with callout properties.
        """
        cfg = callout.config or self._config
        return {
            "type": "callout",
            "text": callout.text,
            "x": callout.position.x,
            "y": callout.position.y,
            "target_x": callout.position.target_x,
            "target_y": callout.position.target_y,
            "placement": callout.position.placement,
            "start_time_ms": callout.start_time_ms,
            "end_time_ms": callout.end_time_ms,
            "font": cfg.font,
            "font_size": cfg.font_size,
            "text_color": cfg.text_color,
            "bg_color": cfg.bg_color,
            "bg_opacity": cfg.bg_opacity,
            "border_color": cfg.border_color,
            "border_width": cfg.border_width,
            "padding": cfg.padding,
            "corner_radius": cfg.corner_radius,
            "arrow_size": cfg.arrow_size,
            "animation": cfg.animation,
        }

    def to_ffmpeg_filter(self, callout: Callout) -> str:
        """Generate FFmpeg filter for a callout.

        Args:
            callout: Callout to convert.

        Returns:
            FFmpeg filter string.
        """
        cfg = callout.config or self._config
        x = callout.position.x
        y = callout.position.y
        text = callout.text.replace("'", "\\'")
        color = cfg.text_color.lstrip("#")
        font_size = cfg.font_size

        filter_str = (
            f"drawtext=text='{text}':"
            f"x={x}:y={y}:fontsize={font_size}:fontcolor={color}"
        )

        # Add time constraints
        if callout.start_time_ms > 0 or callout.end_time_ms is not None:
            start = callout.start_time_ms / 1000.0
            end = (callout.end_time_ms / 1000.0) if callout.end_time_ms else 999999
            filter_str += f":enable='between(t,{start},{end})'"

        return filter_str


# Convenience functions
def create_callout(
    text: str,
    target_x: int,
    target_y: int,
    placement: str = "top",
    config: CalloutConfig | None = None,
) -> Callout:
    """Create a callout annotation.

    Args:
        text: Callout text.
        target_x: Target X coordinate.
        target_y: Target Y coordinate.
        placement: Placement relative to target.
        config: Callout configuration.

    Returns:
        Callout object.
    """
    effect = CalloutEffect(config)
    return effect.add_callout(text, target_x, target_y, placement)


def create_tooltip(
    text: str,
    x: int,
    y: int,
    duration_ms: float = 3000.0,
) -> Callout:
    """Create a tooltip-style callout.

    Args:
        text: Tooltip text.
        x: X coordinate.
        y: Y coordinate.
        duration_ms: Duration to show.

    Returns:
        Callout object.
    """
    effect = CalloutEffect()
    return effect.add_tooltip(text, x, y, duration_ms)
