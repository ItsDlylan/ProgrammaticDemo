"""INT-013: Test auto-scroll correction achieves correct framing.

This test verifies that:
1. Framing rules correctly calculate optimal scroll positions
2. is_element_properly_framed detects proper framing within tolerance
3. AutoScroller adjusts scroll position to achieve framing
4. Different alignment modes (TOP, CENTER, BOTTOM, FULLY_VISIBLE) work correctly
"""

from unittest.mock import MagicMock, patch

import pytest

from programmatic_demo.visual.base import (
    DEFAULT_FRAMING_RULES,
    ElementBounds,
    FramingAlignment,
    FramingRule,
    Viewport,
)
from programmatic_demo.visual.framing_rules import (
    CONTENT_CENTERED,
    HEADER_AT_TOP,
    HEADER_WITH_PADDING,
    calculate_optimal_scroll,
    create_custom_rule,
    get_rule_for_section_type,
    get_scroll_adjustment,
    is_element_properly_framed,
)
from programmatic_demo.visual.auto_scroll import AutoScroller, ScrollResult


class TestElementBounds:
    """Test ElementBounds dataclass."""

    def test_element_bounds_properties(self):
        """Test computed properties of ElementBounds."""
        bounds = ElementBounds(top=100, left=50, width=200, height=150)

        assert bounds.center_y == 175.0  # 100 + 150/2
        assert bounds.center_x == 150.0  # 50 + 200/2
        assert bounds.bottom == 250.0  # 100 + 150
        assert bounds.right == 250.0  # 50 + 200

    def test_element_bounds_small(self):
        """Test with small element."""
        bounds = ElementBounds(top=0, left=0, width=10, height=10)

        assert bounds.center_y == 5.0
        assert bounds.center_x == 5.0
        assert bounds.bottom == 10.0
        assert bounds.right == 10.0


class TestViewport:
    """Test Viewport dataclass."""

    def test_viewport_properties(self):
        """Test computed properties of Viewport."""
        viewport = Viewport(width=1280, height=800, scroll_y=500, scroll_x=0)

        assert viewport.visible_top == 500.0
        assert viewport.visible_bottom == 1300.0  # 500 + 800
        assert viewport.visible_center_y == 900.0  # 500 + 800/2

    def test_viewport_at_top(self):
        """Test viewport at top of page."""
        viewport = Viewport(width=1280, height=800, scroll_y=0)

        assert viewport.visible_top == 0.0
        assert viewport.visible_bottom == 800.0
        assert viewport.visible_center_y == 400.0


class TestFramingRuleCalculations:
    """Test framing rule calculations."""

    def test_top_alignment_optimal_scroll(self):
        """Test TOP alignment calculates correct scroll position."""
        element = ElementBounds(top=500, left=100, width=200, height=100)
        viewport = Viewport(width=1280, height=800)
        rule = FramingRule(FramingAlignment.TOP, padding_top=50)

        optimal = calculate_optimal_scroll(element, viewport, rule)

        # Element top (500) - padding (50) = 450
        assert optimal == 450.0

    def test_top_alignment_no_padding(self):
        """Test TOP alignment with no padding."""
        element = ElementBounds(top=300, left=0, width=100, height=50)
        viewport = Viewport(width=1280, height=800)
        rule = FramingRule(FramingAlignment.TOP, padding_top=0)

        optimal = calculate_optimal_scroll(element, viewport, rule)

        assert optimal == 300.0

    def test_center_alignment_optimal_scroll(self):
        """Test CENTER alignment calculates correct scroll position."""
        element = ElementBounds(top=1000, left=100, width=200, height=200)
        viewport = Viewport(width=1280, height=800)
        rule = FramingRule(FramingAlignment.CENTER)

        optimal = calculate_optimal_scroll(element, viewport, rule)

        # Element center (1100) - viewport center offset (400) = 700
        assert optimal == 700.0

    def test_bottom_alignment_optimal_scroll(self):
        """Test BOTTOM alignment calculates correct scroll position."""
        element = ElementBounds(top=900, left=100, width=200, height=100)
        viewport = Viewport(width=1280, height=800)
        rule = FramingRule(FramingAlignment.BOTTOM, padding_bottom=50)

        optimal = calculate_optimal_scroll(element, viewport, rule)

        # Element bottom (1000) - viewport height (800) + padding (50) = 250
        assert optimal == 250.0

    def test_fully_visible_element_fits(self):
        """Test FULLY_VISIBLE alignment when element fits in viewport."""
        element = ElementBounds(top=500, left=100, width=200, height=300)
        viewport = Viewport(width=1280, height=800)
        rule = FramingRule(
            FramingAlignment.FULLY_VISIBLE, padding_top=50, padding_bottom=50
        )

        optimal = calculate_optimal_scroll(element, viewport, rule)

        # Element fits, so center it: element center (650) - viewport center (400) = 250
        assert optimal == 250.0

    def test_fully_visible_element_too_tall(self):
        """Test FULLY_VISIBLE alignment when element doesn't fit."""
        element = ElementBounds(top=200, left=100, width=200, height=900)  # Too tall
        viewport = Viewport(width=1280, height=800)
        rule = FramingRule(
            FramingAlignment.FULLY_VISIBLE, padding_top=50, padding_bottom=50
        )

        optimal = calculate_optimal_scroll(element, viewport, rule)

        # Element doesn't fit, show top: element top (200) - padding (50) = 150
        assert optimal == 150.0


class TestIsElementProperlyFramed:
    """Test is_element_properly_framed function."""

    def test_element_properly_framed_within_tolerance(self):
        """Test element is properly framed when within tolerance."""
        element = ElementBounds(top=500, left=100, width=200, height=100)
        viewport = Viewport(width=1280, height=800, scroll_y=450)  # Exactly right
        rule = FramingRule(FramingAlignment.TOP, padding_top=50, tolerance=30)

        assert is_element_properly_framed(element, viewport, rule) is True

    def test_element_properly_framed_at_tolerance_edge(self):
        """Test element is properly framed at tolerance edge."""
        element = ElementBounds(top=500, left=100, width=200, height=100)
        # Optimal is 450, tolerance is 30, so 420-480 should pass
        viewport = Viewport(width=1280, height=800, scroll_y=420)
        rule = FramingRule(FramingAlignment.TOP, padding_top=50, tolerance=30)

        assert is_element_properly_framed(element, viewport, rule) is True

    def test_element_not_properly_framed(self):
        """Test element is not properly framed when outside tolerance."""
        element = ElementBounds(top=500, left=100, width=200, height=100)
        # Optimal is 450, but scroll is 200 (250px off)
        viewport = Viewport(width=1280, height=800, scroll_y=200)
        rule = FramingRule(FramingAlignment.TOP, padding_top=50, tolerance=30)

        assert is_element_properly_framed(element, viewport, rule) is False

    def test_centered_element_properly_framed(self):
        """Test centered element is properly framed."""
        element = ElementBounds(top=500, left=100, width=200, height=200)
        # Element center = 600, optimal scroll = 600 - 400 = 200
        viewport = Viewport(width=1280, height=800, scroll_y=200)
        rule = FramingRule(FramingAlignment.CENTER, tolerance=50)

        assert is_element_properly_framed(element, viewport, rule) is True


class TestGetScrollAdjustment:
    """Test get_scroll_adjustment function."""

    def test_positive_adjustment_scroll_down(self):
        """Test positive adjustment means scroll down."""
        element = ElementBounds(top=1000, left=100, width=200, height=100)
        viewport = Viewport(width=1280, height=800, scroll_y=0)
        rule = FramingRule(FramingAlignment.TOP, padding_top=50)

        adjustment = get_scroll_adjustment(element, viewport, rule)

        # Optimal is 950, current is 0, so +950
        assert adjustment == 950.0
        assert adjustment > 0

    def test_negative_adjustment_scroll_up(self):
        """Test negative adjustment means scroll up."""
        element = ElementBounds(top=100, left=100, width=200, height=100)
        viewport = Viewport(width=1280, height=800, scroll_y=500)
        rule = FramingRule(FramingAlignment.TOP, padding_top=50)

        adjustment = get_scroll_adjustment(element, viewport, rule)

        # Optimal is 50, current is 500, so -450
        assert adjustment == -450.0
        assert adjustment < 0

    def test_zero_adjustment_already_framed(self):
        """Test zero adjustment when already framed."""
        element = ElementBounds(top=500, left=100, width=200, height=100)
        viewport = Viewport(width=1280, height=800, scroll_y=450)
        rule = FramingRule(FramingAlignment.TOP, padding_top=50)

        adjustment = get_scroll_adjustment(element, viewport, rule)

        assert adjustment == 0.0


class TestGetRuleForSectionType:
    """Test get_rule_for_section_type function."""

    def test_known_section_types(self):
        """Test getting rules for known section types."""
        hero_rule = get_rule_for_section_type("hero")
        assert hero_rule.alignment == FramingAlignment.TOP
        assert hero_rule.padding_top == 0

        cta_rule = get_rule_for_section_type("cta")
        assert cta_rule.alignment == FramingAlignment.CENTER

        footer_rule = get_rule_for_section_type("footer")
        assert footer_rule.alignment == FramingAlignment.BOTTOM

    def test_unknown_section_type_returns_default(self):
        """Test unknown section type returns default rule."""
        rule = get_rule_for_section_type("unknown_section_xyz")

        assert rule == DEFAULT_FRAMING_RULES["default"]
        assert rule.alignment == FramingAlignment.CENTER

    def test_case_insensitive(self):
        """Test section type lookup is case insensitive."""
        rule1 = get_rule_for_section_type("HERO")
        rule2 = get_rule_for_section_type("hero")
        rule3 = get_rule_for_section_type("Hero")

        assert rule1 == rule2 == rule3


class TestCreateCustomRule:
    """Test create_custom_rule function."""

    def test_create_with_enum(self):
        """Test creating rule with enum alignment."""
        rule = create_custom_rule(FramingAlignment.CENTER, padding_top=100)

        assert rule.alignment == FramingAlignment.CENTER
        assert rule.padding_top == 100

    def test_create_with_string(self):
        """Test creating rule with string alignment."""
        rule = create_custom_rule("top", padding_top=25, tolerance=10)

        assert rule.alignment == FramingAlignment.TOP
        assert rule.padding_top == 25
        assert rule.tolerance == 10

    def test_preset_rules(self):
        """Test preset rule constants."""
        assert HEADER_AT_TOP.alignment == FramingAlignment.TOP
        assert HEADER_AT_TOP.padding_top == 0

        assert HEADER_WITH_PADDING.alignment == FramingAlignment.TOP
        assert HEADER_WITH_PADDING.padding_top == 50

        assert CONTENT_CENTERED.alignment == FramingAlignment.CENTER


class TestScrollResult:
    """Test ScrollResult dataclass."""

    def test_successful_result(self):
        """Test successful scroll result."""
        result = ScrollResult(
            success=True,
            final_position=450.0,
            iterations=2,
            adjustments=[(0.0, 450.0), (400.0, 50.0)],
        )

        assert result.success is True
        assert result.final_position == 450.0
        assert result.iterations == 2
        assert len(result.adjustments) == 2
        assert result.error is None

    def test_failed_result(self):
        """Test failed scroll result."""
        result = ScrollResult(
            success=False,
            final_position=100.0,
            iterations=5,
            adjustments=[],
            error="Max iterations reached",
        )

        assert result.success is False
        assert result.error == "Max iterations reached"


class TestAutoScroller:
    """Test AutoScroller class."""

    def create_mock_page(self, viewport_size=None, scroll_y=0.0):
        """Create a mock Playwright page."""
        page = MagicMock()
        page.viewport_size = viewport_size or {"width": 1280, "height": 800}
        page.evaluate = MagicMock(return_value=scroll_y)
        return page

    def test_get_viewport(self):
        """Test getting viewport from page."""
        mock_page = self.create_mock_page(scroll_y=500.0)
        scroller = AutoScroller(mock_page)

        viewport = scroller.get_viewport()

        assert viewport.width == 1280
        assert viewport.height == 800
        # Note: evaluate is called for both scroll_y and scroll_x

    def test_scroll_to(self):
        """Test scroll_to method."""
        mock_page = self.create_mock_page()
        scroller = AutoScroller(mock_page)

        scroller.scroll_to(500.0)

        mock_page.evaluate.assert_called_with("window.scrollTo(0, 500.0)")

    def test_scroll_to_frame_already_framed(self):
        """Test scroll_to_frame when element is already properly framed."""
        mock_page = self.create_mock_page()
        # Mock evaluate to return current scroll position
        mock_page.evaluate = MagicMock(return_value=450.0)

        scroller = AutoScroller(mock_page)

        element = ElementBounds(top=500, left=100, width=200, height=100)
        rule = FramingRule(FramingAlignment.TOP, padding_top=50, tolerance=30)

        result = scroller.scroll_to_frame(element, rule, smooth=False)

        assert result.success is True
        assert result.iterations == 0

    def test_scroll_to_frame_needs_adjustment(self):
        """Test scroll_to_frame when element needs scrolling."""
        mock_page = MagicMock()
        mock_page.viewport_size = {"width": 1280, "height": 800}

        # First call returns 0 (not framed), then 450 (framed)
        call_count = [0]
        def mock_evaluate(script):
            result = 0.0 if call_count[0] < 2 else 450.0
            call_count[0] += 1
            return result

        mock_page.evaluate = mock_evaluate

        scroller = AutoScroller(mock_page, max_iterations=5, min_adjustment=5.0)

        element = ElementBounds(top=500, left=100, width=200, height=100)
        rule = FramingRule(FramingAlignment.TOP, padding_top=50, tolerance=30)

        result = scroller.scroll_to_frame(element, rule, smooth=False)

        assert result.success is True
        assert result.iterations >= 1

    def test_scroll_to_frame_max_iterations(self):
        """Test scroll_to_frame respects max iterations."""
        mock_page = MagicMock()
        mock_page.viewport_size = {"width": 1280, "height": 800}
        # Always return a position that's not properly framed
        mock_page.evaluate = MagicMock(return_value=0.0)

        scroller = AutoScroller(mock_page, max_iterations=3, min_adjustment=5.0)

        element = ElementBounds(top=1000, left=100, width=200, height=100)
        rule = FramingRule(FramingAlignment.TOP, padding_top=50, tolerance=10)

        result = scroller.scroll_to_frame(element, rule, smooth=False)

        assert result.success is False
        assert result.iterations == 3
        assert "Max iterations" in result.error

    def test_scroll_to_element_not_found(self):
        """Test scroll_to_element when element doesn't exist."""
        mock_page = MagicMock()
        mock_page.viewport_size = {"width": 1280, "height": 800}
        mock_page.evaluate = MagicMock(return_value=0.0)
        mock_page.query_selector = MagicMock(return_value=None)

        scroller = AutoScroller(mock_page)
        rule = FramingRule(FramingAlignment.TOP)

        result = scroller.scroll_to_element("#nonexistent", rule)

        assert result.success is False
        assert "Element not found" in result.error

    def test_scroll_to_element_no_bounding_box(self):
        """Test scroll_to_element when bounding box unavailable."""
        mock_page = MagicMock()
        mock_page.viewport_size = {"width": 1280, "height": 800}
        mock_page.evaluate = MagicMock(return_value=0.0)

        mock_element = MagicMock()
        mock_element.bounding_box = MagicMock(return_value=None)
        mock_page.query_selector = MagicMock(return_value=mock_element)

        scroller = AutoScroller(mock_page)
        rule = FramingRule(FramingAlignment.TOP)

        result = scroller.scroll_to_element("#hidden-element", rule)

        assert result.success is False
        assert "bounding box" in result.error.lower()

    def test_min_adjustment_threshold(self):
        """Test that tiny adjustments are accepted as success."""
        mock_page = MagicMock()
        mock_page.viewport_size = {"width": 1280, "height": 800}
        # Return a position very close to optimal
        mock_page.evaluate = MagicMock(return_value=448.0)

        scroller = AutoScroller(mock_page, min_adjustment=5.0)

        element = ElementBounds(top=500, left=100, width=200, height=100)
        # Optimal is 450, current is 448, adjustment would be 2px (< min_adjustment)
        rule = FramingRule(FramingAlignment.TOP, padding_top=50, tolerance=1)

        result = scroller.scroll_to_frame(element, rule, smooth=False)

        # Should succeed because adjustment is too small to bother
        assert result.success is True


class TestDefaultFramingRules:
    """Test default framing rules constant."""

    def test_default_rules_defined(self):
        """Test that default rules are defined for common sections."""
        assert "hero" in DEFAULT_FRAMING_RULES
        assert "features" in DEFAULT_FRAMING_RULES
        assert "pricing" in DEFAULT_FRAMING_RULES
        assert "cta" in DEFAULT_FRAMING_RULES
        assert "footer" in DEFAULT_FRAMING_RULES
        assert "default" in DEFAULT_FRAMING_RULES

    def test_hero_rule(self):
        """Test hero section rule."""
        rule = DEFAULT_FRAMING_RULES["hero"]
        assert rule.alignment == FramingAlignment.TOP
        assert rule.padding_top == 0

    def test_cta_rule(self):
        """Test CTA section rule."""
        rule = DEFAULT_FRAMING_RULES["cta"]
        assert rule.alignment == FramingAlignment.CENTER

    def test_footer_rule(self):
        """Test footer section rule."""
        rule = DEFAULT_FRAMING_RULES["footer"]
        assert rule.alignment == FramingAlignment.BOTTOM
        assert rule.padding_bottom == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
