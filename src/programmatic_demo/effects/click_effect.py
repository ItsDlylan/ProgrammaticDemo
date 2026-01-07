"""Click effect generation for visual feedback.

Generates visual effects for mouse clicks such as:
- Ripple animations expanding from click point
- Highlight circles/rings
- Color overlays
"""

from dataclasses import dataclass
from typing import Any

import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@dataclass
class ClickEffectConfig:
    """Configuration for click effects.

    Attributes:
        radius: Maximum radius of the effect in pixels.
        duration_ms: Duration of the effect in milliseconds.
        color: Effect color as hex string or RGB tuple.
        opacity: Starting opacity (0.0-1.0).
        style: Effect style (ripple, highlight, pulse).
        enable_sound: Whether to play click sound effect.
        sound_path: Path to custom click sound file.
    """

    radius: int = 30
    duration_ms: int = 300
    color: str = "#FF5722"
    opacity: float = 0.7
    style: str = "ripple"
    enable_sound: bool = False
    sound_path: str | None = None


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

    def generate_ripple_frames(
        self,
        x: int,
        y: int,
        frame_size: tuple[int, int] = (100, 100),
        start_time_ms: float = 0,
    ) -> list[Any]:
        """Generate ripple animation as PIL Image sequence.

        Creates a sequence of PNG-compatible images showing an expanding
        ripple effect with fading opacity.

        Args:
            x: X coordinate of the ripple center (used for metadata).
            y: Y coordinate of the ripple center (used for metadata).
            frame_size: Size of each frame (width, height).
            start_time_ms: Starting timestamp for the animation.

        Returns:
            List of PIL Image objects representing the animation frames.
            Returns empty list if PIL is not available.
        """
        if not HAS_PIL:
            return []

        images: list[Any] = []
        num_frames = max(1, self._config.duration_ms // 16)  # ~60fps

        # Parse color from hex
        color_hex = self._config.color.lstrip("#")
        if len(color_hex) == 6:
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)
        else:
            r, g, b = 255, 87, 34  # Default orange

        center_x, center_y = frame_size[0] // 2, frame_size[1] // 2

        for i in range(num_frames + 1):
            progress = i / num_frames

            # Create transparent image
            img = Image.new("RGBA", frame_size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Calculate current radius and opacity
            radius = int(self._config.radius * progress)
            opacity = int(255 * self._config.opacity * (1 - progress))

            if radius > 0 and opacity > 0:
                # Draw expanding circle with fading opacity
                bbox = (
                    center_x - radius,
                    center_y - radius,
                    center_x + radius,
                    center_y + radius,
                )
                draw.ellipse(bbox, outline=(r, g, b, opacity), width=2)

            images.append(img)

        return images

    def play_click_sound(
        self,
        sound_path: str | None = None,
        blocking: bool = False,
    ) -> dict[str, Any]:
        """Play a click sound effect.

        Args:
            sound_path: Path to custom click sound file.
                        Uses config sound_path or default if None.
            blocking: If True, wait for sound to finish.

        Returns:
            Dict with success status and any error message.
        """
        # Determine sound file path
        if sound_path is None:
            sound_path = self._config.sound_path

        if sound_path is None:
            # Default to assets directory
            assets_dir = Path(__file__).parent.parent / "assets" / "sounds"
            sound_path = str(assets_dir / "click.wav")

        if not os.path.exists(sound_path):
            return {
                "success": False,
                "error": f"Sound file not found: {sound_path}",
            }

        try:
            # Try simpleaudio first (cross-platform, non-blocking support)
            try:
                import simpleaudio as sa
                wave_obj = sa.WaveObject.from_wave_file(sound_path)
                play_obj = wave_obj.play()
                if blocking:
                    play_obj.wait_done()
                return {"success": True, "sound": sound_path}
            except ImportError:
                pass

            # Fallback to playsound
            try:
                from playsound import playsound
                playsound(sound_path, block=blocking)
                return {"success": True, "sound": sound_path}
            except ImportError:
                pass

            return {
                "success": False,
                "error": "No audio library available (install simpleaudio or playsound)",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


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
