"""Effects module for visual enhancements in demo videos.

This package provides visual effects that can be applied to demos:
- Click highlights and cursor effects
- Zoom and focus effects
- Annotations and callouts
- Transitions between scenes
"""

from programmatic_demo.effects.compositor import Compositor, Effect, EffectConfig, EffectEvent, EffectType

__all__ = ["Compositor", "Effect", "EffectConfig", "EffectEvent", "EffectType"]
