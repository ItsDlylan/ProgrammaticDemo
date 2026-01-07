"""Effects module for visual enhancements in demo videos.

This package provides visual effects that can be applied to demos:
- Click highlights and cursor effects
- Zoom and focus effects
- Annotations and callouts
- Transitions between scenes
"""

from programmatic_demo.effects.compositor import Compositor, Effect, EffectConfig, EffectEvent, EffectType
from programmatic_demo.effects.mouse_tracker import MouseEvent, MouseTracker, get_mouse_tracker

__all__ = [
    "Compositor",
    "Effect",
    "EffectConfig",
    "EffectEvent",
    "EffectType",
    "MouseEvent",
    "MouseTracker",
    "get_mouse_tracker",
]
