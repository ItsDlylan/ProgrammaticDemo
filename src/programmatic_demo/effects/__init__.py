"""Effects module for visual enhancements in demo videos.

This package provides visual effects that can be applied to demos:
- Click highlights and cursor effects
- Zoom and focus effects
- Annotations and callouts
- Transitions between scenes
"""

from programmatic_demo.effects.callout import (
    Callout,
    CalloutConfig,
    CalloutEffect,
    CalloutPosition,
    create_callout,
    create_tooltip,
)
from programmatic_demo.effects.click_effect import (
    ClickEffect,
    ClickEffectConfig,
    RippleFrame,
    create_click_effect,
)
from programmatic_demo.effects.compositor import Compositor, Effect, EffectConfig, EffectEvent, EffectType
from programmatic_demo.effects.highlight import (
    Highlight,
    HighlightConfig,
    HighlightRegion,
    create_highlight,
)
from programmatic_demo.effects.mouse_tracker import MouseEvent, MouseTracker, get_mouse_tracker
from programmatic_demo.effects.zoom_effect import (
    ZoomEffect,
    ZoomEffectConfig,
    ZoomFrame,
    create_zoom_effect,
)

__all__ = [
    "Callout",
    "CalloutConfig",
    "CalloutEffect",
    "CalloutPosition",
    "ClickEffect",
    "ClickEffectConfig",
    "Compositor",
    "Effect",
    "EffectConfig",
    "EffectEvent",
    "EffectType",
    "Highlight",
    "HighlightConfig",
    "HighlightRegion",
    "MouseEvent",
    "MouseTracker",
    "RippleFrame",
    "ZoomEffect",
    "ZoomEffectConfig",
    "ZoomFrame",
    "create_callout",
    "create_click_effect",
    "create_highlight",
    "create_tooltip",
    "create_zoom_effect",
    "get_mouse_tracker",
]
