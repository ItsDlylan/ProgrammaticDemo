"""Video overlays for adding visual elements.

This module provides overlay capabilities:
- Text overlays and watermarks
- Logo and image overlays
- Progress bars and indicators
- Lower thirds and captions
"""

from dataclasses import dataclass, field
from typing import Any

from programmatic_demo.postprocess.editor import FFmpegBuilder


@dataclass
class TextOverlayConfig:
    """Configuration for text overlays.

    Attributes:
        font: Font family name.
        font_size: Font size in points.
        color: Text color as hex string.
        bg_color: Background color (None for transparent).
        bg_opacity: Background opacity (0.0-1.0).
        padding: Padding around text in pixels.
        position: Position preset (top-left, top-center, top-right, etc.).
        x_offset: Additional X offset from position.
        y_offset: Additional Y offset from position.
    """

    font: str = "Arial"
    font_size: int = 24
    color: str = "#FFFFFF"
    bg_color: str | None = None
    bg_opacity: float = 0.7
    padding: int = 10
    position: str = "bottom-center"
    x_offset: int = 0
    y_offset: int = 0


@dataclass
class ImageOverlayConfig:
    """Configuration for image overlays.

    Attributes:
        width: Overlay width (None for original).
        height: Overlay height (None for original).
        opacity: Overlay opacity (0.0-1.0).
        position: Position preset.
        x_offset: Additional X offset.
        y_offset: Additional Y offset.
    """

    width: int | None = None
    height: int | None = None
    opacity: float = 1.0
    position: str = "top-right"
    x_offset: int = 20
    y_offset: int = 20


@dataclass
class Overlay:
    """A video overlay element.

    Attributes:
        overlay_type: Type of overlay (text, image, shape).
        content: Overlay content (text string or image path).
        start_time: Start time in seconds.
        end_time: End time in seconds (None for duration).
        config: Overlay configuration.
    """

    overlay_type: str
    content: str
    start_time: float = 0.0
    end_time: float | None = None
    config: dict[str, Any] = field(default_factory=dict)


class OverlayManager:
    """Manages video overlays for post-processing.

    Provides methods to add text, images, and other visual
    elements as overlays on the video.
    """

    def __init__(self) -> None:
        """Initialize the OverlayManager."""
        self._overlays: list[Overlay] = []

    @property
    def overlays(self) -> list[Overlay]:
        """Get all registered overlays."""
        return self._overlays.copy()

    def add_text(
        self,
        text: str,
        start_time: float = 0.0,
        end_time: float | None = None,
        config: TextOverlayConfig | None = None,
    ) -> Overlay:
        """Add a text overlay.

        Args:
            text: Text content to display.
            start_time: Start time in seconds.
            end_time: End time (None for full duration).
            config: Text overlay configuration.

        Returns:
            The created Overlay object.
        """
        cfg = config or TextOverlayConfig()
        overlay = Overlay(
            overlay_type="text",
            content=text,
            start_time=start_time,
            end_time=end_time,
            config={
                "font": cfg.font,
                "font_size": cfg.font_size,
                "color": cfg.color,
                "bg_color": cfg.bg_color,
                "bg_opacity": cfg.bg_opacity,
                "padding": cfg.padding,
                "position": cfg.position,
                "x_offset": cfg.x_offset,
                "y_offset": cfg.y_offset,
            },
        )
        self._overlays.append(overlay)
        return overlay

    def add_image(
        self,
        image_path: str,
        start_time: float = 0.0,
        end_time: float | None = None,
        config: ImageOverlayConfig | None = None,
    ) -> Overlay:
        """Add an image overlay (logo, watermark, etc.).

        Args:
            image_path: Path to the image file.
            start_time: Start time in seconds.
            end_time: End time (None for full duration).
            config: Image overlay configuration.

        Returns:
            The created Overlay object.
        """
        cfg = config or ImageOverlayConfig()
        overlay = Overlay(
            overlay_type="image",
            content=image_path,
            start_time=start_time,
            end_time=end_time,
            config={
                "width": cfg.width,
                "height": cfg.height,
                "opacity": cfg.opacity,
                "position": cfg.position,
                "x_offset": cfg.x_offset,
                "y_offset": cfg.y_offset,
            },
        )
        self._overlays.append(overlay)
        return overlay

    def add_watermark(
        self,
        image_path: str,
        position: str = "bottom-right",
        opacity: float = 0.5,
    ) -> Overlay:
        """Add a watermark overlay.

        Args:
            image_path: Path to watermark image.
            position: Position preset.
            opacity: Watermark opacity.

        Returns:
            The created Overlay object.
        """
        config = ImageOverlayConfig(position=position, opacity=opacity)
        return self.add_image(image_path, config=config)

    def add_lower_third(
        self,
        title: str,
        subtitle: str = "",
        start_time: float = 0.0,
        duration: float = 5.0,
    ) -> Overlay:
        """Add a lower third overlay.

        Args:
            title: Main title text.
            subtitle: Subtitle text.
            start_time: Start time in seconds.
            duration: Display duration in seconds.

        Returns:
            The created Overlay object.
        """
        content = f"{title}\n{subtitle}" if subtitle else title
        config = TextOverlayConfig(
            position="bottom-left",
            font_size=28,
            bg_color="#000000",
            bg_opacity=0.6,
            padding=15,
            y_offset=50,
        )
        return self.add_text(
            content,
            start_time=start_time,
            end_time=start_time + duration,
            config=config,
        )

    def clear(self) -> None:
        """Clear all overlays."""
        self._overlays.clear()

    def to_ffmpeg_filter(
        self,
        video_width: int = 1920,
        video_height: int = 1080,
    ) -> str:
        """Generate FFmpeg filter string for all overlays.

        Args:
            video_width: Video width for position calculations.
            video_height: Video height for position calculations.

        Returns:
            FFmpeg filter string.
        """
        filters = []

        for overlay in self._overlays:
            if overlay.overlay_type == "text":
                # Calculate position
                x, y = self._get_position(
                    overlay.config.get("position", "bottom-center"),
                    video_width,
                    video_height,
                    overlay.config.get("x_offset", 0),
                    overlay.config.get("y_offset", 0),
                )

                color = overlay.config.get("color", "#FFFFFF").lstrip("#")
                font_size = overlay.config.get("font_size", 24)

                filter_str = (
                    f"drawtext=text='{overlay.content}':"
                    f"x={x}:y={y}:fontsize={font_size}:fontcolor={color}"
                )

                # Add time constraints
                if overlay.start_time > 0 or overlay.end_time is not None:
                    end = overlay.end_time or 999999
                    filter_str += f":enable='between(t,{overlay.start_time},{end})'"

                filters.append(filter_str)

        return ",".join(filters) if filters else ""

    def _get_position(
        self,
        position: str,
        width: int,
        height: int,
        x_offset: int,
        y_offset: int,
    ) -> tuple[str, str]:
        """Calculate X,Y position from preset.

        Args:
            position: Position preset name.
            width: Video width.
            height: Video height.
            x_offset: Additional X offset.
            y_offset: Additional Y offset.

        Returns:
            Tuple of (x, y) as FFmpeg expressions.
        """
        positions = {
            "top-left": ("10", "10"),
            "top-center": ("(w-text_w)/2", "10"),
            "top-right": ("w-text_w-10", "10"),
            "center-left": ("10", "(h-text_h)/2"),
            "center": ("(w-text_w)/2", "(h-text_h)/2"),
            "center-right": ("w-text_w-10", "(h-text_h)/2"),
            "bottom-left": ("10", "h-text_h-10"),
            "bottom-center": ("(w-text_w)/2", "h-text_h-10"),
            "bottom-right": ("w-text_w-10", "h-text_h-10"),
        }

        x, y = positions.get(position, ("10", "10"))

        # Add offsets
        if x_offset != 0:
            x = f"{x}+{x_offset}"
        if y_offset != 0:
            y = f"{y}+{y_offset}"

        return x, y


# Convenience functions
def add_text_overlay(
    text: str,
    start_time: float = 0.0,
    end_time: float | None = None,
    **config_kwargs: Any,
) -> Overlay:
    """Convenience function to create a text overlay.

    Args:
        text: Text content.
        start_time: Start time in seconds.
        end_time: End time in seconds.
        **config_kwargs: Additional TextOverlayConfig options.

    Returns:
        Overlay object.
    """
    manager = OverlayManager()
    config = TextOverlayConfig(**config_kwargs) if config_kwargs else None
    return manager.add_text(text, start_time, end_time, config)
