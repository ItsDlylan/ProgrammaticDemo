"""Framing rules for calculating optimal scroll positions.

This module provides functions to calculate the optimal scroll position
to frame page elements according to different alignment rules.
"""

from programmatic_demo.visual.base import (
    DEFAULT_FRAMING_RULES,
    ElementBounds,
    FramingAlignment,
    FramingRule,
    Viewport,
)


def calculate_optimal_scroll(
    element_bounds: ElementBounds,
    viewport: Viewport,
    rule: FramingRule,
) -> float:
    """Calculate optimal scroll position to frame an element.

    Args:
        element_bounds: Bounding box of the element to frame.
        viewport: Current viewport dimensions.
        rule: Framing rule to apply.

    Returns:
        Optimal scroll Y position in pixels.
    """
    if rule.alignment == FramingAlignment.TOP:
        # Position element header at top of viewport with padding
        return element_bounds.top - rule.padding_top

    elif rule.alignment == FramingAlignment.CENTER:
        # Center the element vertically in viewport
        element_center = element_bounds.center_y
        viewport_center_offset = viewport.height / 2
        return element_center - viewport_center_offset

    elif rule.alignment == FramingAlignment.BOTTOM:
        # Position element at bottom of viewport with padding
        return element_bounds.bottom - viewport.height + rule.padding_bottom

    elif rule.alignment == FramingAlignment.FULLY_VISIBLE:
        # Ensure entire element is visible, prefer top alignment
        element_fits = element_bounds.height <= (
            viewport.height - rule.padding_top - rule.padding_bottom
        )

        if element_fits:
            # Center if element fits
            return element_bounds.center_y - viewport.height / 2
        else:
            # Show top of element if too tall
            return element_bounds.top - rule.padding_top

    # Default to top alignment
    return element_bounds.top - rule.padding_top


def is_element_properly_framed(
    element_bounds: ElementBounds,
    viewport: Viewport,
    rule: FramingRule,
) -> bool:
    """Check if an element is properly framed according to a rule.

    Args:
        element_bounds: Bounding box of the element.
        viewport: Current viewport state with scroll position.
        rule: Framing rule to check against.

    Returns:
        True if element is properly framed within tolerance.
    """
    optimal_scroll = calculate_optimal_scroll(element_bounds, viewport, rule)
    current_scroll = viewport.scroll_y

    return abs(current_scroll - optimal_scroll) <= rule.tolerance


def get_scroll_adjustment(
    element_bounds: ElementBounds,
    viewport: Viewport,
    rule: FramingRule,
) -> float:
    """Calculate how much to adjust scroll to properly frame an element.

    Args:
        element_bounds: Bounding box of the element.
        viewport: Current viewport state.
        rule: Framing rule to apply.

    Returns:
        Scroll adjustment in pixels (positive = scroll down, negative = scroll up).
    """
    optimal_scroll = calculate_optimal_scroll(element_bounds, viewport, rule)
    return optimal_scroll - viewport.scroll_y


def get_rule_for_section_type(section_type: str) -> FramingRule:
    """Get the default framing rule for a section type.

    Args:
        section_type: Type of section (hero, features, pricing, etc.).

    Returns:
        FramingRule for the section type, or default rule if unknown.
    """
    return DEFAULT_FRAMING_RULES.get(
        section_type.lower(),
        DEFAULT_FRAMING_RULES["default"],
    )


def create_custom_rule(
    alignment: FramingAlignment | str,
    padding_top: int = 50,
    padding_bottom: int = 50,
    tolerance: int = 30,
) -> FramingRule:
    """Create a custom framing rule.

    Args:
        alignment: Alignment type (enum or string like 'top', 'center').
        padding_top: Padding from top of viewport.
        padding_bottom: Padding from bottom of viewport.
        tolerance: Acceptable deviation from ideal position.

    Returns:
        FramingRule with specified parameters.
    """
    if isinstance(alignment, str):
        alignment = FramingAlignment(alignment.lower())

    return FramingRule(
        alignment=alignment,
        padding_top=padding_top,
        padding_bottom=padding_bottom,
        tolerance=tolerance,
    )


# Preset rules for common use cases
HEADER_AT_TOP = FramingRule(FramingAlignment.TOP, padding_top=0, tolerance=20)
HEADER_WITH_PADDING = FramingRule(FramingAlignment.TOP, padding_top=50, tolerance=30)
CONTENT_CENTERED = FramingRule(FramingAlignment.CENTER, tolerance=50)
FULLY_VISIBLE = FramingRule(FramingAlignment.FULLY_VISIBLE, padding_top=30, padding_bottom=30)
CTA_VISIBLE = FramingRule(FramingAlignment.FULLY_VISIBLE, padding_top=50, padding_bottom=100)
