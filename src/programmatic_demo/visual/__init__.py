"""Visual verification module for auto-framing and screenshot analysis.

This module provides tools for:
- Element bounds detection via DOM/accessibility tree
- Framing rules for different content types
- Screenshot analysis for framing verification
- Animation completion detection
- Auto-scroll correction loops
- Semantic section detection
- Dynamic waypoint generation
"""

from programmatic_demo.visual.base import (
    AnimationDetector,
    DEFAULT_FRAMING_RULES,
    ElementBounds,
    ElementBoundsProvider,
    FramingAlignment,
    FramingAnalyzer,
    FramingIssue,
    FramingRule,
    Section,
    SectionDetector,
    Viewport,
    Waypoint,
    WaypointGenerator,
)
from programmatic_demo.visual.framing_rules import (
    CONTENT_CENTERED,
    CTA_VISIBLE,
    FULLY_VISIBLE,
    HEADER_AT_TOP,
    HEADER_WITH_PADDING,
    calculate_optimal_scroll,
    create_custom_rule,
    get_rule_for_section_type,
    get_scroll_adjustment,
    is_element_properly_framed,
)
from programmatic_demo.visual.element_bounds import (
    AsyncElementBoundsDetector,
    ElementBoundsDetector,
)
from programmatic_demo.visual.animation_detector import (
    AnimationWatcher,
    frame_diff,
    frame_diff_region,
    wait_for_animation_complete,
    wait_for_animation_complete_sync,
)
from programmatic_demo.visual.framing_analyzer import FramingAnalyzer
from programmatic_demo.visual.section_detector import (
    AsyncSectionDetector,
    SectionDetector,
    detect_section_type,
)
from programmatic_demo.visual.auto_scroll import (
    AsyncAutoScroller,
    AutoScroller,
    ScrollResult,
)
from programmatic_demo.visual.waypoint_generator import (
    AsyncWaypointGenerator,
    WaypointGenerator,
    estimate_pause_duration,
    estimate_scroll_duration,
)
from programmatic_demo.visual.smart_recorder import (
    AsyncSmartDemoRecorder,
    RecordingConfig,
    RecordingProgress,
    RecordingResult,
    SmartDemoRecorder,
    WaypointOverride,
)
from programmatic_demo.visual.preview_mode import (
    AsyncWaypointPreviewer,
    PreviewConfig,
    PreviewReport,
    WaypointPreview,
    WaypointPreviewer,
    approve_all_waypoints,
    generate_preview_report,
    preview_waypoints,
    preview_waypoints_async,
)

__all__ = [
    # Enums
    "FramingAlignment",
    # Data classes
    "ElementBounds",
    "Viewport",
    "FramingRule",
    "FramingIssue",
    "Section",
    "Waypoint",
    # Protocols
    "ElementBoundsProvider",
    "FramingAnalyzer",
    "AnimationDetector",
    "SectionDetector",
    "WaypointGenerator",
    # Constants
    "DEFAULT_FRAMING_RULES",
    # Framing rules functions
    "calculate_optimal_scroll",
    "is_element_properly_framed",
    "get_scroll_adjustment",
    "get_rule_for_section_type",
    "create_custom_rule",
    # Preset rules
    "HEADER_AT_TOP",
    "HEADER_WITH_PADDING",
    "CONTENT_CENTERED",
    "FULLY_VISIBLE",
    "CTA_VISIBLE",
    # Element bounds detectors
    "ElementBoundsDetector",
    "AsyncElementBoundsDetector",
    # Animation detection
    "frame_diff",
    "frame_diff_region",
    "wait_for_animation_complete",
    "wait_for_animation_complete_sync",
    "AnimationWatcher",
    # Framing analyzer
    "FramingAnalyzer",
    # Section detection
    "SectionDetector",
    "AsyncSectionDetector",
    "detect_section_type",
    # Auto-scroll correction
    "AutoScroller",
    "AsyncAutoScroller",
    "ScrollResult",
    # Waypoint generation
    "WaypointGenerator",
    "AsyncWaypointGenerator",
    "estimate_scroll_duration",
    "estimate_pause_duration",
    # Smart recorder
    "SmartDemoRecorder",
    "AsyncSmartDemoRecorder",
    "RecordingConfig",
    "RecordingProgress",
    "RecordingResult",
    "WaypointOverride",
    # Preview mode
    "WaypointPreviewer",
    "AsyncWaypointPreviewer",
    "PreviewConfig",
    "PreviewReport",
    "WaypointPreview",
    "preview_waypoints",
    "preview_waypoints_async",
    "generate_preview_report",
    "approve_all_waypoints",
]
