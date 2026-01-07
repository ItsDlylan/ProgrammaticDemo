"""Highlight effect for emphasizing screen regions.

Generates highlight effects to draw attention to specific
areas of the screen during demos.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class HighlightConfig:
    """Configuration for highlight effects.

    Attributes:
        color: Highlight color as hex string.
        opacity: Highlight opacity (0.0-1.0).
        border_width: Border width in pixels.
        border_color: Border color as hex string.
        padding: Padding around highlighted region.
        style: Highlight style (box, rounded, circle, spotlight).
        animation: Animation type (none, pulse, fade).
    """

    color: str = "#FFEB3B"
    opacity: float = 0.3
    border_width: int = 2
    border_color: str = "#FFC107"
    padding: int = 5
    style: str = "rounded"
    animation: str = "none"


@dataclass
class HighlightRegion:
    """A region to highlight on screen.

    Attributes:
        x: Left coordinate.
        y: Top coordinate.
        width: Width of region.
        height: Height of region.
        config: Highlight configuration.
    """

    x: int
    y: int
    width: int
    height: int
    config: HighlightConfig | None = None


class Highlight:
    """Generates highlight effects for screen regions.

    Creates visual highlights to emphasize areas of interest
    during the demo video.
    """

    def __init__(self, config: HighlightConfig | None = None) -> None:
        """Initialize the Highlight generator.

        Args:
            config: Effect configuration, uses defaults if None.
        """
        self._config = config or HighlightConfig()

    @property
    def config(self) -> HighlightConfig:
        """Get the highlight configuration."""
        return self._config

    def generate_box(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> dict[str, Any]:
        """Generate a box highlight effect.

        Args:
            x: Left coordinate.
            y: Top coordinate.
            width: Width of box.
            height: Height of box.

        Returns:
            Dict describing the highlight effect.
        """
        return {
            "type": "box",
            "x": x - self._config.padding,
            "y": y - self._config.padding,
            "width": width + 2 * self._config.padding,
            "height": height + 2 * self._config.padding,
            "color": self._config.color,
            "opacity": self._config.opacity,
            "border_width": self._config.border_width,
            "border_color": self._config.border_color,
        }

    def generate_rounded(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        corner_radius: int = 8,
    ) -> dict[str, Any]:
        """Generate a rounded rectangle highlight.

        Args:
            x: Left coordinate.
            y: Top coordinate.
            width: Width of region.
            height: Height of region.
            corner_radius: Corner radius in pixels.

        Returns:
            Dict describing the highlight effect.
        """
        return {
            "type": "rounded",
            "x": x - self._config.padding,
            "y": y - self._config.padding,
            "width": width + 2 * self._config.padding,
            "height": height + 2 * self._config.padding,
            "corner_radius": corner_radius,
            "color": self._config.color,
            "opacity": self._config.opacity,
            "border_width": self._config.border_width,
            "border_color": self._config.border_color,
        }

    def generate_circle(
        self,
        x: int,
        y: int,
        radius: int | None = None,
    ) -> dict[str, Any]:
        """Generate a circular highlight.

        Args:
            x: Center X coordinate.
            y: Center Y coordinate.
            radius: Circle radius (auto-calculated if None).

        Returns:
            Dict describing the highlight effect.
        """
        r = radius if radius is not None else 30
        return {
            "type": "circle",
            "x": x,
            "y": y,
            "radius": r + self._config.padding,
            "color": self._config.color,
            "opacity": self._config.opacity,
            "border_width": self._config.border_width,
            "border_color": self._config.border_color,
        }

    def generate_spotlight(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        screen_width: int,
        screen_height: int,
        dim_opacity: float = 0.5,
    ) -> dict[str, Any]:
        """Generate a spotlight effect (dims everything except region).

        Args:
            x: Left coordinate of spotlight region.
            y: Top coordinate of spotlight region.
            width: Width of spotlight region.
            height: Height of spotlight region.
            screen_width: Full screen width.
            screen_height: Full screen height.
            dim_opacity: Opacity of the dimmed area.

        Returns:
            Dict describing the spotlight effect.
        """
        return {
            "type": "spotlight",
            "spotlight_x": x - self._config.padding,
            "spotlight_y": y - self._config.padding,
            "spotlight_width": width + 2 * self._config.padding,
            "spotlight_height": height + 2 * self._config.padding,
            "screen_width": screen_width,
            "screen_height": screen_height,
            "dim_color": "#000000",
            "dim_opacity": dim_opacity,
            "border_width": self._config.border_width,
            "border_color": self._config.border_color,
        }

    def to_ffmpeg_filter(
        self,
        effect: dict[str, Any],
    ) -> str:
        """Convert a highlight effect to an FFmpeg filter string.

        Args:
            effect: Highlight effect dict.

        Returns:
            FFmpeg filter string.
        """
        effect_type = effect.get("type", "box")

        if effect_type in ("box", "rounded"):
            x = effect.get("x", 0)
            y = effect.get("y", 0)
            w = effect.get("width", 100)
            h = effect.get("height", 100)
            color = effect.get("color", "#FFEB3B").lstrip("#")
            opacity = effect.get("opacity", 0.3)

            # Draw a semi-transparent rectangle
            return (
                f"drawbox=x={x}:y={y}:w={w}:h={h}:"
                f"color={color}@{opacity}:t=fill"
            )
        elif effect_type == "circle":
            x = effect.get("x", 0)
            y = effect.get("y", 0)
            r = effect.get("radius", 30)
            color = effect.get("color", "#FFEB3B").lstrip("#")
            opacity = effect.get("opacity", 0.3)

            return f"drawcircle=x={x}:y={y}:r={r}:color={color}@{opacity}:t=fill"

        return ""


def create_highlight(
    x: int,
    y: int,
    width: int,
    height: int,
    config: HighlightConfig | None = None,
) -> dict[str, Any]:
    """Convenience function to create a highlight effect.

    Args:
        x: Left coordinate.
        y: Top coordinate.
        width: Width of region.
        height: Height of region.
        config: Effect configuration.

    Returns:
        Highlight effect dict.
    """
    highlight = Highlight(config)
    return highlight.generate_rounded(x, y, width, height)
