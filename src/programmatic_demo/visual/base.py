"""Base protocols and types for visual verification.

This module defines the core interfaces and data structures used by the
visual verification system for auto-framing and screenshot analysis.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from PIL import Image


class FramingAlignment(Enum):
    """Alignment options for framing rules."""

    TOP = "top"  # Element header at top of viewport
    CENTER = "center"  # Element centered in viewport
    BOTTOM = "bottom"  # Element at bottom of viewport
    FULLY_VISIBLE = "fully_visible"  # Entire element visible


@dataclass
class ElementBounds:
    """Bounding box for a page element.

    Attributes:
        top: Y coordinate of top edge (pixels from page top).
        left: X coordinate of left edge (pixels from page left).
        width: Element width in pixels.
        height: Element height in pixels.
        center_y: Y coordinate of element center.
        center_x: X coordinate of element center.
    """

    top: float
    left: float
    width: float
    height: float

    @property
    def center_y(self) -> float:
        """Y coordinate of element center."""
        return self.top + self.height / 2

    @property
    def center_x(self) -> float:
        """X coordinate of element center."""
        return self.left + self.width / 2

    @property
    def bottom(self) -> float:
        """Y coordinate of bottom edge."""
        return self.top + self.height

    @property
    def right(self) -> float:
        """X coordinate of right edge."""
        return self.left + self.width


@dataclass
class Viewport:
    """Browser viewport dimensions.

    Attributes:
        width: Viewport width in pixels.
        height: Viewport height in pixels.
        scroll_y: Current vertical scroll position.
        scroll_x: Current horizontal scroll position.
    """

    width: int
    height: int
    scroll_y: float = 0.0
    scroll_x: float = 0.0

    @property
    def visible_top(self) -> float:
        """Top Y coordinate of visible area."""
        return self.scroll_y

    @property
    def visible_bottom(self) -> float:
        """Bottom Y coordinate of visible area."""
        return self.scroll_y + self.height

    @property
    def visible_center_y(self) -> float:
        """Center Y coordinate of visible area."""
        return self.scroll_y + self.height / 2


@dataclass
class FramingRule:
    """Rule for how an element should be framed in viewport.

    Attributes:
        alignment: How the element should be positioned.
        padding_top: Extra padding from top of viewport (pixels).
        padding_bottom: Extra padding from bottom of viewport (pixels).
        tolerance: Acceptable deviation from ideal position (pixels).
    """

    alignment: FramingAlignment
    padding_top: int = 50
    padding_bottom: int = 50
    tolerance: int = 30


@dataclass
class FramingIssue:
    """A detected framing problem.

    Attributes:
        issue_type: Type of framing issue (e.g., 'cut_off', 'not_centered').
        description: Human-readable description of the issue.
        element_name: Name of the affected element.
        current_position: Current scroll position.
        suggested_position: Suggested scroll position to fix.
        confidence: Confidence score (0.0 to 1.0).
    """

    issue_type: str
    description: str
    element_name: str
    current_position: float
    suggested_position: float
    confidence: float = 1.0


@dataclass
class Section:
    """A detected page section.

    Attributes:
        name: Section identifier/name.
        section_type: Type of section (hero, features, pricing, etc.).
        bounds: Bounding box of the section.
        scroll_position: Recommended scroll position to view section.
    """

    name: str
    section_type: str
    bounds: ElementBounds
    scroll_position: float


@dataclass
class Waypoint:
    """A scroll waypoint for demo recording.

    Attributes:
        name: Waypoint identifier.
        position: Scroll Y position.
        pause: Duration to pause at this position (seconds).
        scroll_duration: Time to scroll TO this position (seconds).
        description: Human-readable description.
        framing_rule: Rule used to calculate position.
    """

    name: str
    position: float
    pause: float = 2.0
    scroll_duration: float = 2.0
    description: str = ""
    framing_rule: FramingRule | None = None


@runtime_checkable
class ElementBoundsProvider(Protocol):
    """Protocol for getting element bounding boxes."""

    async def get_element_bounds(self, selector: str) -> ElementBounds | None:
        """Get bounding box for an element by CSS selector.

        Args:
            selector: CSS selector for the element.

        Returns:
            ElementBounds if found, None otherwise.
        """
        ...

    async def get_section_bounds(self, section_name: str) -> ElementBounds | None:
        """Get bounding box for a semantic section.

        Args:
            section_name: Name/identifier of the section.

        Returns:
            ElementBounds if found, None otherwise.
        """
        ...


@runtime_checkable
class FramingAnalyzer(Protocol):
    """Protocol for analyzing screenshot framing."""

    async def is_element_visible(
        self, element_bounds: ElementBounds, viewport: Viewport
    ) -> bool:
        """Check if element is fully visible in viewport.

        Args:
            element_bounds: Bounding box of the element.
            viewport: Current viewport state.

        Returns:
            True if element is fully visible.
        """
        ...

    async def is_element_centered(
        self, element_bounds: ElementBounds, viewport: Viewport, tolerance: int = 50
    ) -> bool:
        """Check if element is centered in viewport.

        Args:
            element_bounds: Bounding box of the element.
            viewport: Current viewport state.
            tolerance: Acceptable deviation from center (pixels).

        Returns:
            True if element is centered within tolerance.
        """
        ...

    async def get_framing_issues(
        self,
        screenshot: Image.Image,
        expected_elements: list[str],
    ) -> list[FramingIssue]:
        """Analyze screenshot for framing issues.

        Args:
            screenshot: Screenshot image to analyze.
            expected_elements: List of elements that should be visible.

        Returns:
            List of detected framing issues.
        """
        ...


@runtime_checkable
class AnimationDetector(Protocol):
    """Protocol for detecting animation completion."""

    async def wait_for_animation_complete(
        self,
        take_screenshot: Any,  # Callable[[], Awaitable[Image.Image]]
        threshold: float = 0.03,
        timeout: float = 5.0,
    ) -> bool:
        """Wait for page animations to complete.

        Args:
            take_screenshot: Async function to capture current frame.
            threshold: Pixel change threshold (0.0 to 1.0).
            timeout: Maximum wait time in seconds.

        Returns:
            True if animations completed, False if timeout.
        """
        ...

    def frame_diff(
        self, image1: Image.Image, image2: Image.Image
    ) -> float:
        """Calculate pixel difference between two frames.

        Args:
            image1: First image.
            image2: Second image.

        Returns:
            Percentage of pixels changed (0.0 to 1.0).
        """
        ...


@runtime_checkable
class SectionDetector(Protocol):
    """Protocol for detecting page sections."""

    async def find_sections(self, page: Any) -> list[Section]:
        """Detect all sections on a page.

        Args:
            page: Playwright page object.

        Returns:
            List of detected sections in document order.
        """
        ...


@runtime_checkable
class WaypointGenerator(Protocol):
    """Protocol for generating scroll waypoints."""

    async def generate_waypoints(
        self,
        page: Any,
        framing_rules: dict[str, FramingRule] | None = None,
    ) -> list[Waypoint]:
        """Generate scroll waypoints from page structure.

        Args:
            page: Playwright page object.
            framing_rules: Optional custom framing rules per section type.

        Returns:
            List of waypoints for demo recording.
        """
        ...


# Default framing rules for common section types
DEFAULT_FRAMING_RULES: dict[str, FramingRule] = {
    "hero": FramingRule(FramingAlignment.TOP, padding_top=0),
    "features": FramingRule(FramingAlignment.TOP, padding_top=50),
    "pricing": FramingRule(FramingAlignment.TOP, padding_top=50),
    "faq": FramingRule(FramingAlignment.TOP, padding_top=30),
    "cta": FramingRule(FramingAlignment.CENTER),
    "footer": FramingRule(FramingAlignment.BOTTOM, padding_bottom=0),
    "default": FramingRule(FramingAlignment.CENTER),
}
