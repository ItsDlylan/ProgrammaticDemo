"""Effects module for visual enhancements in demo videos.

This package provides visual effects that can be applied to demos:
- Click highlights and cursor effects
- Zoom and focus effects
- Annotations and callouts
- Transitions between scenes
- Easing functions for smooth animations
"""

from programmatic_demo.effects.easing import (
    EasingFunction,
    EasingPreset,
    EASING_REGISTRY,
    SMOOTH_PRESET,
    SNAPPY_PRESET,
    ZOOM_PRESET,
    ease_in_cubic,
    ease_in_expo,
    ease_in_out_cubic,
    ease_in_out_expo,
    ease_in_out_quad,
    ease_in_quad,
    ease_out_cubic,
    ease_out_expo,
    ease_out_quad,
    get_easing,
    linear,
    list_easings,
    smootherstep,
    smoothstep,
)
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
from programmatic_demo.effects.compositor import (
    Compositor,
    Effect,
    EffectConfig,
    EffectEvent,
    EffectType,
    EventQueue,
    EventQueueItem,
)
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
    ZoomPreset,
    create_dramatic_zoom,
    create_medium_zoom,
    create_subtle_zoom,
    create_zoom_effect,
)

__all__ = [
    # Easing functions
    "EASING_REGISTRY",
    "EasingFunction",
    "EasingPreset",
    "SMOOTH_PRESET",
    "SNAPPY_PRESET",
    "ZOOM_PRESET",
    "ease_in_cubic",
    "ease_in_expo",
    "ease_in_out_cubic",
    "ease_in_out_expo",
    "ease_in_out_quad",
    "ease_in_quad",
    "ease_out_cubic",
    "ease_out_expo",
    "ease_out_quad",
    "get_easing",
    "linear",
    "list_easings",
    "smootherstep",
    "smoothstep",
    # Callout
    "Callout",
    "CalloutConfig",
    "CalloutEffect",
    "CalloutPosition",
    # Click
    "ClickEffect",
    "ClickEffectConfig",
    # Compositor
    "Compositor",
    "Effect",
    "EffectConfig",
    "EffectEvent",
    "EffectType",
    "EventQueue",
    "EventQueueItem",
    # Highlight
    "Highlight",
    "HighlightConfig",
    "HighlightRegion",
    # Mouse
    "MouseEvent",
    "MouseTracker",
    "RippleFrame",
    # Zoom
    "ZoomEffect",
    "ZoomEffectConfig",
    "ZoomFrame",
    "ZoomPreset",
    # Factory functions
    "create_callout",
    "create_click_effect",
    "create_dramatic_zoom",
    "create_highlight",
    "create_medium_zoom",
    "create_subtle_zoom",
    "create_tooltip",
    "create_zoom_effect",
    "get_mouse_tracker",
]
