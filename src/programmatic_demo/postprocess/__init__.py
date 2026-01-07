"""Post-processing module for video editing and finalization.

This package provides video editing capabilities:
- Trimming and cutting video segments
- Adding intros, outros, and transitions
- Audio processing and narration
- Final export and encoding
"""

from programmatic_demo.postprocess.audio import (
    AudioManager,
    AudioTrack,
    SoundEffect,
    VoiceoverSegment,
    add_background_music,
    add_click_sound,
)
from programmatic_demo.postprocess.editor import (
    EditProject,
    FFmpegBuilder,
    VideoEditor,
    VideoSegment,
)
from programmatic_demo.postprocess.overlays import (
    ImageOverlayConfig,
    Overlay,
    OverlayManager,
    ProgressBarConfig,
    TextOverlayConfig,
    add_text_overlay,
)
from programmatic_demo.postprocess.transitions import (
    Transition,
    TransitionConfig,
    TransitionManager,
    TransitionType,
    create_dissolve,
    create_fade_in,
    create_fade_out,
)

__all__ = [
    # Audio
    "AudioManager",
    "AudioTrack",
    "SoundEffect",
    "VoiceoverSegment",
    "add_background_music",
    "add_click_sound",
    # Editor
    "EditProject",
    "FFmpegBuilder",
    "VideoEditor",
    "VideoSegment",
    # Overlays
    "ImageOverlayConfig",
    "Overlay",
    "OverlayManager",
    "ProgressBarConfig",
    "TextOverlayConfig",
    "add_text_overlay",
    # Transitions
    "Transition",
    "TransitionConfig",
    "TransitionManager",
    "TransitionType",
    "create_dissolve",
    "create_fade_in",
    "create_fade_out",
]
