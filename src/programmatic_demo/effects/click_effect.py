"""Click effect generation for visual feedback.

Generates visual effects for mouse clicks such as:
- Ripple animations expanding from click point
- Highlight circles/rings
- Color overlays
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ClickEffectConfig:
    """Configuration for click effects.

    Attributes:
        radius: Maximum radius of the effect in pixels.
        duration_ms: Duration of the effect in milliseconds.
        color: Effect color as hex string or RGB tuple.
        opacity: Starting opacity (0.0-1.0).
        style: Effect style (ripple, highlight, pulse).
    """

    radius: int = 30
    duration_ms: int = 300
    color: str = "#FF5722"
    opacity: float = 0.7
    style: str = "ripple"


@dataclass
class RippleFrame:
    """A single frame of a ripple animation.

    Attributes:
        timestamp_ms: Timestamp in the animation.
        x: Center X coordinate.
        y: Center Y coordinate.
        radius: Current radius of the ripple.
        opacity: Current opacity.
    """

    timestamp_ms: float
    x: int
    y: int
    radius: float
    opacity: float


class ClickEffect:
    """Generates visual effects for mouse clicks.

    Creates ripple, highlight, and other visual effects
    to indicate where clicks occurred in the demo.
    """

    def __init__(self, config: ClickEffectConfig | None = None) -> None:
        """Initialize the ClickEffect generator.

        Args:
            config: Effect configuration, uses defaults if None.
        """
        self._config = config or ClickEffectConfig()

    @property
    def config(self) -> ClickEffectConfig:
        """Get the effect configuration."""
        return self._config

    def generate_ripple(
        self,
        x: int,
        y: int,
        start_time_ms: float = 0,
    ) -> list[RippleFrame]:
        """Generate ripple animation frames for a click.

        Args:
            x: X coordinate of the click.
            y: Y coordinate of the click.
            start_time_ms: Starting timestamp for the animation.

        Returns:
            List of RippleFrame objects representing the animation.
        """
        frames: list[RippleFrame] = []
        num_frames = max(1, self._config.duration_ms // 16)  # ~60fps

        for i in range(num_frames + 1):
            progress = i / num_frames
            timestamp = start_time_ms + (self._config.duration_ms * progress)

            # Radius expands linearly
            radius = self._config.radius * progress

            # Opacity fades out
            opacity = self._config.opacity * (1 - progress)

            frames.append(
                RippleFrame(
                    timestamp_ms=timestamp,
                    x=x,
                    y=y,
                    radius=radius,
                    opacity=opacity,
                )
            )

        return frames

    def generate_highlight(
        self,
        x: int,
        y: int,
        duration_ms: int | None = None,
    ) -> dict[str, Any]:
        """Generate a static highlight effect for a click.

        Args:
            x: X coordinate of the click.
            y: Y coordinate of the click.
            duration_ms: Override duration for the highlight.

        Returns:
            Dict describing the highlight effect.
        """
        return {
            "type": "highlight",
            "x": x,
            "y": y,
            "radius": self._config.radius,
            "color": self._config.color,
            "opacity": self._config.opacity,
            "duration_ms": duration_ms or self._config.duration_ms,
        }

    def generate_pulse(
        self,
        x: int,
        y: int,
        pulses: int = 2,
    ) -> list[RippleFrame]:
        """Generate a pulsing animation effect.

        Args:
            x: X coordinate of the click.
            y: Y coordinate of the click.
            pulses: Number of pulses in the animation.

        Returns:
            List of RippleFrame objects for the pulse animation.
        """
        frames: list[RippleFrame] = []
        pulse_duration = self._config.duration_ms / pulses

        for pulse in range(pulses):
            pulse_start = pulse * pulse_duration
            ripple_frames = self.generate_ripple(x, y, pulse_start)
            frames.extend(ripple_frames)

        return frames

    def to_ffmpeg_filter(
        self,
        frames: list[RippleFrame],
    ) -> str:
        """Convert frames to an FFmpeg filter string.

        Args:
            frames: List of RippleFrame objects.

        Returns:
            FFmpeg filter string for the effect.
        """
        if not frames:
            return ""

        # This is a placeholder - actual implementation would generate
        # complex FFmpeg filter chains for drawing the ripple effect
        first = frames[0]
        last = frames[-1]
        return (
            f"drawcircle=x={first.x}:y={first.y}:"
            f"r={self._config.radius}:color={self._config.color}@0.5:"
            f"enable='between(t,{first.timestamp_ms/1000},{last.timestamp_ms/1000})'"
        )


def create_click_effect(
    x: int,
    y: int,
    config: ClickEffectConfig | None = None,
) -> list[RippleFrame]:
    """Convenience function to create a click effect.

    Args:
        x: X coordinate of the click.
        y: Y coordinate of the click.
        config: Effect configuration.

    Returns:
        List of RippleFrame objects.
    """
    effect = ClickEffect(config)
    return effect.generate_ripple(x, y)
