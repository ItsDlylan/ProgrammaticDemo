"""Zoom effect generation for focus and emphasis.

Generates zoom effects to focus on specific areas:
- Smooth zoom in/out animations
- Ken Burns effect (pan + zoom)
- Focus-follow zoom
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ZoomPreset(Enum):
    """Zoom level presets for common use cases."""

    SUBTLE = "subtle"       # Gentle zoom for small UI elements
    MEDIUM = "medium"       # Default zoom for most use cases
    DRAMATIC = "dramatic"   # Strong zoom for emphasis


@dataclass
class ZoomEffectConfig:
    """Configuration for zoom effects.

    Attributes:
        zoom_factor: Maximum zoom level (1.0 = no zoom, 2.0 = 2x).
        duration_ms: Duration of the zoom animation.
        hold_ms: Duration to hold at max zoom before zooming out.
        easing: Easing function name (linear, ease-in, ease-out, ease-in-out).
        center_x: Zoom center X coordinate (normalized 0-1).
        center_y: Zoom center Y coordinate (normalized 0-1).
    """

    zoom_factor: float = 1.5
    duration_ms: int = 500
    hold_ms: int = 1000
    easing: str = "ease-in-out"
    center_x: float = 0.5
    center_y: float = 0.5

    @classmethod
    def from_preset(cls, preset: ZoomPreset | str) -> "ZoomEffectConfig":
        """Create config from a preset.

        Args:
            preset: Preset name or ZoomPreset enum.

        Returns:
            ZoomEffectConfig with preset values.
        """
        if isinstance(preset, str):
            preset = ZoomPreset(preset)

        presets = {
            ZoomPreset.SUBTLE: cls(zoom_factor=1.25, duration_ms=400, hold_ms=800),
            ZoomPreset.MEDIUM: cls(zoom_factor=1.5, duration_ms=500, hold_ms=1000),
            ZoomPreset.DRAMATIC: cls(zoom_factor=2.0, duration_ms=600, hold_ms=1500),
        }
        return presets.get(preset, cls())


@dataclass
class ZoomFrame:
    """A single frame of a zoom animation.

    Attributes:
        timestamp_ms: Timestamp in the animation.
        zoom: Current zoom level.
        center_x: Current center X (normalized 0-1).
        center_y: Current center Y (normalized 0-1).
    """

    timestamp_ms: float
    zoom: float
    center_x: float
    center_y: float


class ZoomEffect:
    """Generates zoom effects for video.

    Creates smooth zoom animations to focus attention
    on specific areas of the screen.
    """

    def __init__(self, config: ZoomEffectConfig | None = None) -> None:
        """Initialize the ZoomEffect generator.

        Args:
            config: Effect configuration, uses defaults if None.
        """
        self._config = config or ZoomEffectConfig()

    @property
    def config(self) -> ZoomEffectConfig:
        """Get the effect configuration."""
        return self._config

    def _apply_easing(self, progress: float) -> float:
        """Apply easing function to progress value.

        Args:
            progress: Linear progress (0.0 to 1.0).

        Returns:
            Eased progress value.
        """
        if self._config.easing == "linear":
            return progress
        elif self._config.easing == "ease-in":
            return progress * progress
        elif self._config.easing == "ease-out":
            return 1 - (1 - progress) ** 2
        elif self._config.easing == "ease-in-out":
            if progress < 0.5:
                return 2 * progress * progress
            else:
                return 1 - ((-2 * progress + 2) ** 2) / 2
        return progress

    def interpolate_zoom(
        self,
        start_zoom: float,
        end_zoom: float,
        timestamp_ms: float,
        start_time_ms: float,
        duration_ms: float | None = None,
    ) -> float:
        """Interpolate zoom level at a given timestamp with easing.

        Provides smooth transitions between any two zoom levels using
        the configured easing function.

        Args:
            start_zoom: Starting zoom level.
            end_zoom: Ending zoom level.
            timestamp_ms: Current timestamp.
            start_time_ms: Animation start time.
            duration_ms: Duration of interpolation (uses config if None).

        Returns:
            Interpolated zoom level.
        """
        dur = duration_ms if duration_ms is not None else self._config.duration_ms
        elapsed = timestamp_ms - start_time_ms

        if elapsed <= 0:
            return start_zoom
        if elapsed >= dur:
            return end_zoom

        progress = elapsed / dur
        eased = self._apply_easing(progress)

        return start_zoom + (end_zoom - start_zoom) * eased

    def calculate_zoom(
        self,
        timestamp_ms: float,
        start_time_ms: float = 0,
    ) -> ZoomFrame:
        """Calculate zoom parameters for a given timestamp.

        Args:
            timestamp_ms: Current timestamp.
            start_time_ms: Start time of the zoom animation.

        Returns:
            ZoomFrame with current zoom parameters.
        """
        elapsed = timestamp_ms - start_time_ms

        if elapsed < 0:
            # Before animation starts
            return ZoomFrame(
                timestamp_ms=timestamp_ms,
                zoom=1.0,
                center_x=self._config.center_x,
                center_y=self._config.center_y,
            )

        if elapsed >= self._config.duration_ms:
            # After animation ends
            return ZoomFrame(
                timestamp_ms=timestamp_ms,
                zoom=self._config.zoom_factor,
                center_x=self._config.center_x,
                center_y=self._config.center_y,
            )

        # During animation
        progress = elapsed / self._config.duration_ms
        eased = self._apply_easing(progress)
        current_zoom = 1.0 + (self._config.zoom_factor - 1.0) * eased

        return ZoomFrame(
            timestamp_ms=timestamp_ms,
            zoom=current_zoom,
            center_x=self._config.center_x,
            center_y=self._config.center_y,
        )

    def generate_zoom_in(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        start_time_ms: float = 0,
    ) -> list[ZoomFrame]:
        """Generate zoom-in animation frames.

        Args:
            x: Focus point X coordinate.
            y: Focus point Y coordinate.
            width: Video width.
            height: Video height.
            start_time_ms: Starting timestamp.

        Returns:
            List of ZoomFrame objects for the animation.
        """
        # Convert coordinates to normalized (0-1)
        center_x = x / width if width > 0 else 0.5
        center_y = y / height if height > 0 else 0.5

        frames: list[ZoomFrame] = []
        num_frames = max(1, self._config.duration_ms // 16)  # ~60fps

        for i in range(num_frames + 1):
            timestamp = start_time_ms + (self._config.duration_ms * i / num_frames)
            progress = i / num_frames
            eased = self._apply_easing(progress)
            zoom = 1.0 + (self._config.zoom_factor - 1.0) * eased

            frames.append(
                ZoomFrame(
                    timestamp_ms=timestamp,
                    zoom=zoom,
                    center_x=center_x,
                    center_y=center_y,
                )
            )

        return frames

    def generate_zoom_out(
        self,
        start_time_ms: float = 0,
    ) -> list[ZoomFrame]:
        """Generate zoom-out animation frames.

        Args:
            start_time_ms: Starting timestamp.

        Returns:
            List of ZoomFrame objects for the animation.
        """
        frames: list[ZoomFrame] = []
        num_frames = max(1, self._config.duration_ms // 16)

        for i in range(num_frames + 1):
            timestamp = start_time_ms + (self._config.duration_ms * i / num_frames)
            progress = i / num_frames
            eased = self._apply_easing(progress)
            # Reverse: start zoomed, end at 1.0
            zoom = self._config.zoom_factor - (self._config.zoom_factor - 1.0) * eased

            frames.append(
                ZoomFrame(
                    timestamp_ms=timestamp,
                    zoom=zoom,
                    center_x=self._config.center_x,
                    center_y=self._config.center_y,
                )
            )

        return frames

    def to_ffmpeg_filter(
        self,
        frames: list[ZoomFrame],
        width: int,
        height: int,
    ) -> str:
        """Convert frames to an FFmpeg filter string.

        Args:
            frames: List of ZoomFrame objects.
            width: Video width.
            height: Video height.

        Returns:
            FFmpeg filter string for the zoom effect.
        """
        if not frames:
            return ""

        first = frames[0]
        last = frames[-1]

        # Simplified zoompan filter
        return (
            f"zoompan=z='{first.zoom}+({last.zoom}-{first.zoom})*on/{len(frames)}':"
            f"x='(iw-iw/zoom)*{first.center_x}':"
            f"y='(ih-ih/zoom)*{first.center_y}':"
            f"d={len(frames)}:s={width}x{height}"
        )


def create_zoom_effect(
    x: int,
    y: int,
    width: int,
    height: int,
    zoom_factor: float = 1.5,
    duration_ms: int = 500,
) -> list[ZoomFrame]:
    """Convenience function to create a zoom-in effect.

    Args:
        x: Focus point X coordinate.
        y: Focus point Y coordinate.
        width: Video width.
        height: Video height.
        zoom_factor: Maximum zoom level.
        duration_ms: Animation duration.

    Returns:
        List of ZoomFrame objects.
    """
    config = ZoomEffectConfig(zoom_factor=zoom_factor, duration_ms=duration_ms)
    effect = ZoomEffect(config)
    return effect.generate_zoom_in(x, y, width, height)


def create_subtle_zoom() -> ZoomEffectConfig:
    """Create a subtle zoom config (1.25x).

    Returns:
        ZoomEffectConfig with subtle preset values.
    """
    return ZoomEffectConfig.from_preset(ZoomPreset.SUBTLE)


def create_medium_zoom() -> ZoomEffectConfig:
    """Create a medium zoom config (1.5x).

    Returns:
        ZoomEffectConfig with medium preset values.
    """
    return ZoomEffectConfig.from_preset(ZoomPreset.MEDIUM)


def create_dramatic_zoom() -> ZoomEffectConfig:
    """Create a dramatic zoom config (2.0x).

    Returns:
        ZoomEffectConfig with dramatic preset values.
    """
    return ZoomEffectConfig.from_preset(ZoomPreset.DRAMATIC)
