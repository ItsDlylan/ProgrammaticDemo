"""Video transitions for scene changes.

This module provides transition effects:
- Fade in/out
- Cross dissolve
- Wipe transitions
- Slide transitions
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from programmatic_demo.postprocess.editor import FFmpegBuilder


class TransitionType(Enum):
    """Types of transitions available."""

    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    WIPE_UP = "wipe_up"
    WIPE_DOWN = "wipe_down"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"


@dataclass
class TransitionConfig:
    """Configuration for a transition effect.

    Attributes:
        transition_type: Type of transition.
        duration_ms: Duration in milliseconds.
        easing: Easing function (linear, ease-in, ease-out, ease-in-out).
    """

    transition_type: TransitionType = TransitionType.FADE
    duration_ms: int = 500
    easing: str = "linear"


@dataclass
class Transition:
    """A transition between video segments.

    Attributes:
        config: Transition configuration.
        position_ms: Position in timeline where transition starts.
    """

    config: TransitionConfig
    position_ms: float = 0.0


class TransitionManager:
    """Manages video transitions for post-processing.

    Provides methods to add various transition effects
    between video segments.
    """

    def __init__(self) -> None:
        """Initialize the TransitionManager."""
        self._transitions: list[Transition] = []

    @property
    def transitions(self) -> list[Transition]:
        """Get all registered transitions."""
        return self._transitions.copy()

    def add_fade_in(
        self,
        duration_ms: int = 500,
        position_ms: float = 0.0,
    ) -> Transition:
        """Add a fade-in transition at the start.

        Args:
            duration_ms: Fade duration in milliseconds.
            position_ms: Position in timeline.

        Returns:
            The created Transition object.
        """
        config = TransitionConfig(
            transition_type=TransitionType.FADE,
            duration_ms=duration_ms,
        )
        transition = Transition(config=config, position_ms=position_ms)
        self._transitions.append(transition)
        return transition

    def add_fade_out(
        self,
        duration_ms: int = 500,
        position_ms: float = 0.0,
    ) -> Transition:
        """Add a fade-out transition at the end.

        Args:
            duration_ms: Fade duration in milliseconds.
            position_ms: Position where fade-out starts.

        Returns:
            The created Transition object.
        """
        config = TransitionConfig(
            transition_type=TransitionType.FADE,
            duration_ms=duration_ms,
        )
        transition = Transition(config=config, position_ms=position_ms)
        self._transitions.append(transition)
        return transition

    def add_dissolve(
        self,
        duration_ms: int = 1000,
        position_ms: float = 0.0,
    ) -> Transition:
        """Add a cross-dissolve transition.

        Args:
            duration_ms: Dissolve duration in milliseconds.
            position_ms: Position where dissolve occurs.

        Returns:
            The created Transition object.
        """
        config = TransitionConfig(
            transition_type=TransitionType.DISSOLVE,
            duration_ms=duration_ms,
        )
        transition = Transition(config=config, position_ms=position_ms)
        self._transitions.append(transition)
        return transition

    def add_wipe(
        self,
        direction: str = "left",
        duration_ms: int = 500,
        position_ms: float = 0.0,
    ) -> Transition:
        """Add a wipe transition.

        Args:
            direction: Wipe direction (left, right, up, down).
            duration_ms: Wipe duration in milliseconds.
            position_ms: Position where wipe occurs.

        Returns:
            The created Transition object.
        """
        type_map = {
            "left": TransitionType.WIPE_LEFT,
            "right": TransitionType.WIPE_RIGHT,
            "up": TransitionType.WIPE_UP,
            "down": TransitionType.WIPE_DOWN,
        }
        config = TransitionConfig(
            transition_type=type_map.get(direction, TransitionType.WIPE_LEFT),
            duration_ms=duration_ms,
        )
        transition = Transition(config=config, position_ms=position_ms)
        self._transitions.append(transition)
        return transition

    def add_slide(
        self,
        direction: str = "left",
        duration_ms: int = 500,
        position_ms: float = 0.0,
    ) -> Transition:
        """Add a slide transition.

        Args:
            direction: Slide direction (left, right).
            duration_ms: Slide duration in milliseconds.
            position_ms: Position where slide occurs.

        Returns:
            The created Transition object.
        """
        type_map = {
            "left": TransitionType.SLIDE_LEFT,
            "right": TransitionType.SLIDE_RIGHT,
        }
        config = TransitionConfig(
            transition_type=type_map.get(direction, TransitionType.SLIDE_LEFT),
            duration_ms=duration_ms,
        )
        transition = Transition(config=config, position_ms=position_ms)
        self._transitions.append(transition)
        return transition

    def clear(self) -> None:
        """Clear all transitions."""
        self._transitions.clear()

    def to_ffmpeg_filter(self, transition: Transition) -> str:
        """Generate FFmpeg filter for a transition.

        Args:
            transition: Transition to convert.

        Returns:
            FFmpeg filter string.
        """
        config = transition.config
        duration_s = config.duration_ms / 1000.0
        start_s = transition.position_ms / 1000.0

        if config.transition_type == TransitionType.FADE:
            return (
                f"fade=t=in:st={start_s}:d={duration_s},"
                f"fade=t=out:st={start_s}:d={duration_s}"
            )
        elif config.transition_type == TransitionType.DISSOLVE:
            return f"xfade=transition=dissolve:duration={duration_s}:offset={start_s}"
        elif config.transition_type in (
            TransitionType.WIPE_LEFT,
            TransitionType.WIPE_RIGHT,
            TransitionType.WIPE_UP,
            TransitionType.WIPE_DOWN,
        ):
            direction = config.transition_type.value.replace("wipe_", "")
            return f"xfade=transition=wipe{direction}:duration={duration_s}:offset={start_s}"
        elif config.transition_type in (
            TransitionType.SLIDE_LEFT,
            TransitionType.SLIDE_RIGHT,
        ):
            direction = config.transition_type.value.replace("slide_", "")
            return f"xfade=transition=slide{direction}:duration={duration_s}:offset={start_s}"

        return ""


# Convenience functions
def create_fade_in(duration_ms: int = 500) -> Transition:
    """Create a fade-in transition.

    Args:
        duration_ms: Fade duration.

    Returns:
        Transition object.
    """
    manager = TransitionManager()
    return manager.add_fade_in(duration_ms)


def create_fade_out(duration_ms: int = 500) -> Transition:
    """Create a fade-out transition.

    Args:
        duration_ms: Fade duration.

    Returns:
        Transition object.
    """
    manager = TransitionManager()
    return manager.add_fade_out(duration_ms)


def create_dissolve(duration_ms: int = 1000) -> Transition:
    """Create a dissolve transition.

    Args:
        duration_ms: Dissolve duration.

    Returns:
        Transition object.
    """
    manager = TransitionManager()
    return manager.add_dissolve(duration_ms)
