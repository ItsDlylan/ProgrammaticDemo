"""Post-processing module for video editing and finalization.

This package provides video editing capabilities:
- Trimming and cutting video segments
- Adding intros, outros, and transitions
- Audio processing and narration
- Final export and encoding
"""

from programmatic_demo.postprocess.editor import (
    EditProject,
    FFmpegBuilder,
    VideoEditor,
    VideoSegment,
)

__all__ = ["EditProject", "FFmpegBuilder", "VideoEditor", "VideoSegment"]
