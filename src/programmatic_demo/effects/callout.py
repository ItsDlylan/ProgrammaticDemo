"""Callout effects for text annotations in demo videos.

Generates callout effects to annotate and explain
elements on screen during demos.
"""

from dataclasses import dataclass, field
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


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

    def generate_callout(
        self,
        callout: Callout,
        frame_size: tuple[int, int] = (400, 200),
    ) -> Any:
        """Generate a callout with arrow as a PIL Image.

        Renders the callout text box with background, border, and
        an arrow pointing to the target position.

        Args:
            callout: Callout object to render.
            frame_size: Size of the output image (width, height).

        Returns:
            PIL Image with the callout rendered, or None if PIL unavailable.
        """
        if not HAS_PIL:
            return None

        cfg = callout.config or self._config
        pos = callout.position

        # Create transparent image
        img = Image.new("RGBA", frame_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Parse colors
        def parse_color(hex_color: str, opacity: float = 1.0) -> tuple[int, int, int, int]:
            h = hex_color.lstrip("#")
            if len(h) == 6:
                r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            else:
                r, g, b = 51, 51, 51  # Default gray
            return (r, g, b, int(255 * opacity))

        bg_color = parse_color(cfg.bg_color, cfg.bg_opacity)
        text_color = parse_color(cfg.text_color)
        border_color = parse_color(cfg.border_color)

        # Try to load font
        try:
            font = ImageFont.truetype(cfg.font, cfg.font_size)
        except (IOError, OSError):
            try:
                font = ImageFont.truetype("Arial", cfg.font_size)
            except (IOError, OSError):
                font = ImageFont.load_default()

        # Get text bounding box
        text_bbox = draw.textbbox((0, 0), callout.text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Box dimensions
        box_width = min(text_width + 2 * cfg.padding, cfg.max_width)
        box_height = text_height + 2 * cfg.padding

        # Box position
        box_x = pos.x
        box_y = pos.y

        # Ensure box stays within frame
        box_x = max(0, min(box_x, frame_size[0] - box_width))
        box_y = max(0, min(box_y, frame_size[1] - box_height))

        # Draw rounded rectangle background
        box_rect = (box_x, box_y, box_x + box_width, box_y + box_height)
        if cfg.corner_radius > 0:
            draw.rounded_rectangle(box_rect, radius=cfg.corner_radius, fill=bg_color)
            if cfg.border_width > 0:
                draw.rounded_rectangle(
                    box_rect,
                    radius=cfg.corner_radius,
                    outline=border_color,
                    width=cfg.border_width,
                )
        else:
            draw.rectangle(box_rect, fill=bg_color)
            if cfg.border_width > 0:
                draw.rectangle(box_rect, outline=border_color, width=cfg.border_width)

        # Draw text
        text_x = box_x + cfg.padding
        text_y = box_y + cfg.padding
        draw.text((text_x, text_y), callout.text, font=font, fill=text_color)

        # Draw arrow pointing to target
        if cfg.arrow_size > 0:
            arrow_points = self._calculate_arrow_points(
                box_x, box_y, box_width, box_height,
                pos.target_x, pos.target_y,
                pos.placement, cfg.arrow_size
            )
            if arrow_points:
                draw.polygon(arrow_points, fill=bg_color)

        return img

    def _calculate_arrow_points(
        self,
        box_x: int,
        box_y: int,
        box_width: int,
        box_height: int,
        target_x: int,
        target_y: int,
        placement: str,
        arrow_size: int,
    ) -> list[tuple[int, int]] | None:
        """Calculate arrow polygon points.

        Args:
            box_x: Box left edge.
            box_y: Box top edge.
            box_width: Box width.
            box_height: Box height.
            target_x: Target X coordinate.
            target_y: Target Y coordinate.
            placement: Placement direction.
            arrow_size: Arrow base width.

        Returns:
            List of (x, y) tuples for polygon, or None if no arrow needed.
        """
        if placement == "top":
            # Arrow points down from bottom of box to target
            mid_x = box_x + box_width // 2
            return [
                (mid_x - arrow_size, box_y + box_height),
                (mid_x + arrow_size, box_y + box_height),
                (target_x, target_y),
            ]
        elif placement == "bottom":
            # Arrow points up from top of box to target
            mid_x = box_x + box_width // 2
            return [
                (mid_x - arrow_size, box_y),
                (mid_x + arrow_size, box_y),
                (target_x, target_y),
            ]
        elif placement == "left":
            # Arrow points right from right side of box to target
            mid_y = box_y + box_height // 2
            return [
                (box_x + box_width, mid_y - arrow_size),
                (box_x + box_width, mid_y + arrow_size),
                (target_x, target_y),
            ]
        elif placement == "right":
            # Arrow points left from left side of box to target
            mid_y = box_y + box_height // 2
            return [
                (box_x, mid_y - arrow_size),
                (box_x, mid_y + arrow_size),
                (target_x, target_y),
            ]
        return None


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
