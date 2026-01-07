"""Dynamic waypoint generation from page structure.

This module automatically generates scroll waypoints by analyzing
page sections and applying framing rules.
"""

import json
from typing import Any

from programmatic_demo.visual.base import (
    DEFAULT_FRAMING_RULES,
    FramingRule,
    Section,
    Viewport,
    Waypoint,
)
from programmatic_demo.visual.framing_rules import (
    calculate_optimal_scroll,
    get_rule_for_section_type,
)
from programmatic_demo.visual.section_detector import SectionDetector, AsyncSectionDetector


# Default pause durations based on section type
DEFAULT_PAUSE_DURATIONS = {
    "hero": 3.0,
    "features": 3.0,
    "pricing": 3.5,
    "faq": 2.5,
    "cta": 2.0,
    "testimonials": 2.5,
    "about": 2.0,
    "contact": 2.0,
    "footer": 1.5,
    "header": 1.0,
    "default": 2.0,
}

# Default scroll durations based on distance
def estimate_scroll_duration(distance: float) -> float:
    """Estimate scroll duration based on distance.

    Args:
        distance: Distance to scroll in pixels.

    Returns:
        Duration in seconds for smooth scrolling.
    """
    # Base duration + distance-based component
    # Roughly 1 second per 500 pixels, minimum 0.5 seconds
    return max(0.5, 0.5 + abs(distance) / 500)


def estimate_pause_duration(section: Section) -> float:
    """Estimate pause duration based on section type and size.

    Args:
        section: Section to estimate pause for.

    Returns:
        Pause duration in seconds.
    """
    base_duration = DEFAULT_PAUSE_DURATIONS.get(
        section.section_type,
        DEFAULT_PAUSE_DURATIONS["default"],
    )

    # Adjust based on section height (more content = longer pause)
    height_factor = min(1.5, section.bounds.height / 800)
    return base_duration * height_factor


class WaypointGenerator:
    """Generates scroll waypoints from page structure."""

    def __init__(
        self,
        page: Any,
        viewport_height: int = 800,
        custom_rules: dict[str, FramingRule] | None = None,
        custom_pauses: dict[str, float] | None = None,
    ):
        """Initialize the waypoint generator.

        Args:
            page: Playwright page object (sync).
            viewport_height: Viewport height for framing calculations.
            custom_rules: Optional custom framing rules per section type.
            custom_pauses: Optional custom pause durations per section type.
        """
        self._page = page
        self._section_detector = SectionDetector(page)
        self.viewport_height = viewport_height
        self.custom_rules = custom_rules or {}
        self.custom_pauses = custom_pauses or {}

    def get_framing_rule(self, section_type: str) -> FramingRule:
        """Get framing rule for a section type.

        Args:
            section_type: Type of section.

        Returns:
            FramingRule to apply.
        """
        if section_type in self.custom_rules:
            return self.custom_rules[section_type]
        return get_rule_for_section_type(section_type)

    def get_pause_duration(self, section: Section) -> float:
        """Get pause duration for a section.

        Args:
            section: Section to get pause for.

        Returns:
            Pause duration in seconds.
        """
        if section.section_type in self.custom_pauses:
            return self.custom_pauses[section.section_type]
        if section.name in self.custom_pauses:
            return self.custom_pauses[section.name]
        return estimate_pause_duration(section)

    def generate_waypoints(
        self,
        include_return_to_top: bool = True,
        min_section_height: float = 200,
    ) -> list[Waypoint]:
        """Generate waypoints from page sections.

        Args:
            include_return_to_top: Whether to add a final waypoint returning to top.
            min_section_height: Minimum section height to include.

        Returns:
            List of Waypoint objects.
        """
        sections = self._section_detector.find_sections()

        # Filter sections
        sections = [s for s in sections if s.bounds.height >= min_section_height]

        # Create viewport for calculations
        viewport = Viewport(
            width=1280,  # Default width
            height=self.viewport_height,
            scroll_y=0,
        )

        waypoints = []
        prev_position = 0

        for section in sections:
            rule = self.get_framing_rule(section.section_type)

            # Calculate optimal scroll position
            position = calculate_optimal_scroll(section.bounds, viewport, rule)
            position = max(0, position)  # Don't scroll above top

            # Calculate scroll duration based on distance
            distance = abs(position - prev_position)
            scroll_duration = estimate_scroll_duration(distance)

            # Get pause duration
            pause = self.get_pause_duration(section)

            waypoint = Waypoint(
                name=section.name,
                position=position,
                pause=pause,
                scroll_duration=scroll_duration,
                description=f"{section.section_type.title()} section: {section.name}",
                framing_rule=rule,
            )
            waypoints.append(waypoint)
            prev_position = position

        # Add return to top if requested
        if include_return_to_top and waypoints:
            distance = prev_position
            waypoints.append(
                Waypoint(
                    name="return_to_top",
                    position=0,
                    pause=2.0,
                    scroll_duration=estimate_scroll_duration(distance),
                    description="Return to top of page",
                    framing_rule=None,
                )
            )

        return waypoints

    def generate_waypoints_dict(
        self,
        include_return_to_top: bool = True,
    ) -> list[dict[str, Any]]:
        """Generate waypoints as dictionaries (compatible with demo scripts).

        Args:
            include_return_to_top: Whether to add a final waypoint returning to top.

        Returns:
            List of waypoint dictionaries.
        """
        waypoints = self.generate_waypoints(include_return_to_top)

        return [
            {
                "name": w.name,
                "position": w.position,
                "pause": w.pause,
                "scroll_duration": w.scroll_duration,
                "description": w.description,
            }
            for w in waypoints
        ]

    def export_waypoints_json(
        self,
        filepath: str,
        include_return_to_top: bool = True,
    ) -> None:
        """Export waypoints to a JSON file.

        Args:
            filepath: Path to output file.
            include_return_to_top: Whether to include return to top waypoint.
        """
        waypoints = self.generate_waypoints_dict(include_return_to_top)

        with open(filepath, "w") as f:
            json.dump({"waypoints": waypoints}, f, indent=2)

    def merge_with_overrides(
        self,
        overrides: list[dict[str, Any]],
    ) -> list[Waypoint]:
        """Generate waypoints and merge with manual overrides.

        Args:
            overrides: List of override dicts with at least 'name' and optional
                      'position', 'pause', 'scroll_duration' to override.

        Returns:
            List of Waypoint objects with overrides applied.
        """
        waypoints = self.generate_waypoints(include_return_to_top=False)

        # Create lookup for overrides
        override_map = {o["name"]: o for o in overrides}

        # Apply overrides
        result = []
        for wp in waypoints:
            if wp.name in override_map:
                override = override_map[wp.name]
                wp = Waypoint(
                    name=wp.name,
                    position=override.get("position", wp.position),
                    pause=override.get("pause", wp.pause),
                    scroll_duration=override.get("scroll_duration", wp.scroll_duration),
                    description=override.get("description", wp.description),
                    framing_rule=wp.framing_rule,
                )
            result.append(wp)

        # Add any override-only waypoints (not in detected sections)
        detected_names = {wp.name for wp in waypoints}
        for override in overrides:
            if override["name"] not in detected_names:
                result.append(
                    Waypoint(
                        name=override["name"],
                        position=override.get("position", 0),
                        pause=override.get("pause", 2.0),
                        scroll_duration=override.get("scroll_duration", 1.5),
                        description=override.get("description", ""),
                        framing_rule=None,
                    )
                )

        # Sort by position
        result.sort(key=lambda w: w.position)

        return result


class AsyncWaypointGenerator:
    """Async version of WaypointGenerator."""

    def __init__(
        self,
        page: Any,
        viewport_height: int = 800,
        custom_rules: dict[str, FramingRule] | None = None,
        custom_pauses: dict[str, float] | None = None,
    ):
        """Initialize the async waypoint generator."""
        self._page = page
        self._section_detector = AsyncSectionDetector(page)
        self.viewport_height = viewport_height
        self.custom_rules = custom_rules or {}
        self.custom_pauses = custom_pauses or {}

    def get_framing_rule(self, section_type: str) -> FramingRule:
        """Get framing rule for a section type."""
        if section_type in self.custom_rules:
            return self.custom_rules[section_type]
        return get_rule_for_section_type(section_type)

    def get_pause_duration(self, section: Section) -> float:
        """Get pause duration for a section."""
        if section.section_type in self.custom_pauses:
            return self.custom_pauses[section.section_type]
        if section.name in self.custom_pauses:
            return self.custom_pauses[section.name]
        return estimate_pause_duration(section)

    async def generate_waypoints(
        self,
        include_return_to_top: bool = True,
        min_section_height: float = 200,
    ) -> list[Waypoint]:
        """Generate waypoints from page sections."""
        sections = await self._section_detector.find_sections()
        sections = [s for s in sections if s.bounds.height >= min_section_height]

        viewport = Viewport(
            width=1280,
            height=self.viewport_height,
            scroll_y=0,
        )

        waypoints = []
        prev_position = 0

        for section in sections:
            rule = self.get_framing_rule(section.section_type)
            position = calculate_optimal_scroll(section.bounds, viewport, rule)
            position = max(0, position)

            distance = abs(position - prev_position)
            scroll_duration = estimate_scroll_duration(distance)
            pause = self.get_pause_duration(section)

            waypoint = Waypoint(
                name=section.name,
                position=position,
                pause=pause,
                scroll_duration=scroll_duration,
                description=f"{section.section_type.title()} section: {section.name}",
                framing_rule=rule,
            )
            waypoints.append(waypoint)
            prev_position = position

        if include_return_to_top and waypoints:
            distance = prev_position
            waypoints.append(
                Waypoint(
                    name="return_to_top",
                    position=0,
                    pause=2.0,
                    scroll_duration=estimate_scroll_duration(distance),
                    description="Return to top of page",
                    framing_rule=None,
                )
            )

        return waypoints

    async def generate_waypoints_dict(
        self,
        include_return_to_top: bool = True,
    ) -> list[dict[str, Any]]:
        """Generate waypoints as dictionaries."""
        waypoints = await self.generate_waypoints(include_return_to_top)

        return [
            {
                "name": w.name,
                "position": w.position,
                "pause": w.pause,
                "scroll_duration": w.scroll_duration,
                "description": w.description,
            }
            for w in waypoints
        ]
