"""INT-012: Test automatic section detection on sample pages.

This test verifies that:
1. Section type detection patterns work correctly
2. detect_section_type identifies sections from attributes
3. SectionDetector finds sections from DOM structure
4. Section filtering and lookup methods work
"""

from unittest.mock import MagicMock

import pytest

from programmatic_demo.visual.base import ElementBounds, Section
from programmatic_demo.visual.section_detector import (
    SECTION_TYPE_PATTERNS,
    SectionDetector,
    detect_section_type,
)


class TestSectionTypePatterns:
    """Test that section type patterns are defined correctly."""

    def test_hero_patterns_exist(self):
        """Test hero section patterns are defined."""
        assert "hero" in SECTION_TYPE_PATTERNS
        patterns = SECTION_TYPE_PATTERNS["hero"]
        assert len(patterns) >= 1
        assert any("hero" in p for p in patterns)

    def test_features_patterns_exist(self):
        """Test features section patterns are defined."""
        assert "features" in SECTION_TYPE_PATTERNS
        patterns = SECTION_TYPE_PATTERNS["features"]
        assert any("feature" in p for p in patterns)

    def test_pricing_patterns_exist(self):
        """Test pricing section patterns are defined."""
        assert "pricing" in SECTION_TYPE_PATTERNS
        patterns = SECTION_TYPE_PATTERNS["pricing"]
        assert any("pricing" in p for p in patterns)

    def test_cta_patterns_exist(self):
        """Test CTA section patterns are defined."""
        assert "cta" in SECTION_TYPE_PATTERNS
        patterns = SECTION_TYPE_PATTERNS["cta"]
        assert any("cta" in p or "signup" in p for p in patterns)

    def test_footer_patterns_exist(self):
        """Test footer section patterns are defined."""
        assert "footer" in SECTION_TYPE_PATTERNS
        patterns = SECTION_TYPE_PATTERNS["footer"]
        assert any("footer" in p for p in patterns)


class TestDetectSectionType:
    """Test detect_section_type function."""

    def test_detect_hero_from_id(self):
        """Test detecting hero section from element ID."""
        result = detect_section_type("hero-section", "", "", "")
        assert result == "hero"

    def test_detect_hero_from_class(self):
        """Test detecting hero section from class."""
        result = detect_section_type("", "hero-banner main-hero", "", "")
        assert result == "hero"

    def test_detect_features_from_heading(self):
        """Test detecting features section from heading."""
        result = detect_section_type("", "", "Our Amazing Features", "")
        assert result == "features"

    def test_detect_pricing_from_aria_label(self):
        """Test detecting pricing section from ARIA label."""
        result = detect_section_type("", "", "", "Pricing and Plans")
        assert result == "pricing"

    def test_detect_faq_from_id(self):
        """Test detecting FAQ section from ID."""
        result = detect_section_type("faq", "", "", "")
        assert result == "faq"

    def test_detect_cta_from_class(self):
        """Test detecting CTA section from class."""
        result = detect_section_type("", "cta-section signup-form", "", "")
        assert result == "cta"

    def test_detect_testimonials_from_heading(self):
        """Test detecting testimonials section from heading."""
        result = detect_section_type("", "", "What Our Customers Say", "")
        assert result == "testimonials"

    def test_detect_about_from_id(self):
        """Test detecting about section from ID."""
        result = detect_section_type("about-us", "", "", "")
        assert result == "about"

    def test_detect_contact_from_heading(self):
        """Test detecting contact section from heading."""
        result = detect_section_type("", "", "Contact Us Today", "")
        assert result == "contact"

    def test_detect_footer_from_id(self):
        """Test detecting footer from ID."""
        result = detect_section_type("site-footer", "", "", "")
        assert result == "footer"

    def test_detect_header_from_class(self):
        """Test detecting header from class."""
        result = detect_section_type("", "site-header navbar", "", "")
        assert result == "header"

    def test_returns_default_for_unknown(self):
        """Test unknown section returns default."""
        result = detect_section_type("some-id", "random-class", "Some Heading", "")
        assert result == "default"

    def test_case_insensitive_detection(self):
        """Test detection is case insensitive."""
        result1 = detect_section_type("HERO", "", "", "")
        result2 = detect_section_type("Hero-Section", "", "", "")
        result3 = detect_section_type("", "FEATURES", "", "")

        assert result1 == "hero"
        assert result2 == "hero"
        assert result3 == "features"

    def test_combined_attributes(self):
        """Test detection uses combined attributes."""
        # Even if ID is random, class might match
        result = detect_section_type("section1", "pricing-table", "Plans", "")
        assert result == "pricing"

    def test_partial_match(self):
        """Test partial pattern matching."""
        result = detect_section_type("my-hero-banner", "", "", "")
        assert result == "hero"

    def test_priority_of_matching(self):
        """Test that first match wins."""
        # hero patterns come before features, so hero should win
        result = detect_section_type("hero-features", "", "", "")
        assert result == "hero"


class TestSectionDataclass:
    """Test Section dataclass."""

    def test_section_creation(self):
        """Test creating a Section object."""
        bounds = ElementBounds(top=100, left=0, width=1280, height=600)
        section = Section(
            name="hero",
            section_type="hero",
            bounds=bounds,
            scroll_position=100.0,
        )

        assert section.name == "hero"
        assert section.section_type == "hero"
        assert section.bounds.top == 100
        assert section.scroll_position == 100.0


class TestSectionDetector:
    """Test SectionDetector class with mock page."""

    def create_mock_page(self, sections_data):
        """Create a mock Playwright page that returns section data."""
        page = MagicMock()
        page.evaluate = MagicMock(return_value=sections_data)
        return page

    def test_find_sections_empty_page(self):
        """Test finding sections on page with no sections."""
        page = self.create_mock_page([])
        detector = SectionDetector(page)

        sections = detector.find_sections()

        assert sections == []

    def test_find_sections_basic(self):
        """Test finding basic sections."""
        sections_data = [
            {
                "name": "hero",
                "id": "hero",
                "classes": "hero-section",
                "headingText": "Welcome",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 0,
                "width": 1280,
                "height": 600,
            },
            {
                "name": "features",
                "id": "features",
                "classes": "features-section",
                "headingText": "Features",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 600,
                "width": 1280,
                "height": 400,
            },
        ]
        page = self.create_mock_page(sections_data)
        detector = SectionDetector(page)

        sections = detector.find_sections()

        assert len(sections) == 2
        assert sections[0].name == "hero"
        assert sections[0].section_type == "hero"
        assert sections[0].bounds.top == 0
        assert sections[1].name == "features"
        assert sections[1].section_type == "features"

    def test_find_sections_with_header_tag(self):
        """Test header tag gets header section type."""
        sections_data = [
            {
                "name": "header",
                "id": "",
                "classes": "",
                "headingText": "",
                "ariaLabel": "",
                "role": "",
                "tagName": "header",
                "x": 0,
                "y": 0,
                "width": 1280,
                "height": 80,
            },
        ]
        page = self.create_mock_page(sections_data)
        detector = SectionDetector(page)

        sections = detector.find_sections()

        assert len(sections) == 1
        assert sections[0].section_type == "header"

    def test_find_sections_with_footer_tag(self):
        """Test footer tag gets footer section type."""
        sections_data = [
            {
                "name": "footer",
                "id": "",
                "classes": "",
                "headingText": "",
                "ariaLabel": "",
                "role": "",
                "tagName": "footer",
                "x": 0,
                "y": 1000,
                "width": 1280,
                "height": 200,
            },
        ]
        page = self.create_mock_page(sections_data)
        detector = SectionDetector(page)

        sections = detector.find_sections()

        assert len(sections) == 1
        assert sections[0].section_type == "footer"

    def test_find_sections_with_banner_role(self):
        """Test banner role gets header section type."""
        sections_data = [
            {
                "name": "main-header",
                "id": "main-header",
                "classes": "",
                "headingText": "",
                "ariaLabel": "",
                "role": "banner",
                "tagName": "div",
                "x": 0,
                "y": 0,
                "width": 1280,
                "height": 100,
            },
        ]
        page = self.create_mock_page(sections_data)
        detector = SectionDetector(page)

        sections = detector.find_sections()

        assert len(sections) == 1
        assert sections[0].section_type == "header"

    def test_find_sections_with_contentinfo_role(self):
        """Test contentinfo role gets footer section type."""
        sections_data = [
            {
                "name": "site-footer",
                "id": "site-footer",
                "classes": "",
                "headingText": "",
                "ariaLabel": "",
                "role": "contentinfo",
                "tagName": "div",
                "x": 0,
                "y": 2000,
                "width": 1280,
                "height": 150,
            },
        ]
        page = self.create_mock_page(sections_data)
        detector = SectionDetector(page)

        sections = detector.find_sections()

        assert len(sections) == 1
        assert sections[0].section_type == "footer"

    def test_find_section_by_name(self):
        """Test finding section by name."""
        sections_data = [
            {
                "name": "hero",
                "id": "hero",
                "classes": "",
                "headingText": "",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 0,
                "width": 1280,
                "height": 600,
            },
            {
                "name": "pricing-section",
                "id": "pricing-section",
                "classes": "pricing",
                "headingText": "Our Pricing",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 1200,
                "width": 1280,
                "height": 500,
            },
        ]
        page = self.create_mock_page(sections_data)
        detector = SectionDetector(page)

        section = detector.find_section_by_name("pricing")

        assert section is not None
        assert "pricing" in section.name.lower()

    def test_find_section_by_name_not_found(self):
        """Test finding nonexistent section by name."""
        sections_data = [
            {
                "name": "hero",
                "id": "hero",
                "classes": "",
                "headingText": "",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 0,
                "width": 1280,
                "height": 600,
            },
        ]
        page = self.create_mock_page(sections_data)
        detector = SectionDetector(page)

        section = detector.find_section_by_name("nonexistent")

        assert section is None

    def test_find_section_by_name_case_insensitive(self):
        """Test name search is case insensitive."""
        sections_data = [
            {
                "name": "HERO-BANNER",
                "id": "HERO-BANNER",
                "classes": "hero",
                "headingText": "",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 0,
                "width": 1280,
                "height": 600,
            },
        ]
        page = self.create_mock_page(sections_data)
        detector = SectionDetector(page)

        section = detector.find_section_by_name("hero-banner")

        assert section is not None

    def test_find_sections_by_type(self):
        """Test finding all sections of a type."""
        sections_data = [
            {
                "name": "hero",
                "id": "hero",
                "classes": "",
                "headingText": "",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 0,
                "width": 1280,
                "height": 600,
            },
            {
                "name": "about",
                "id": "about",
                "classes": "",
                "headingText": "",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 600,
                "width": 1280,
                "height": 400,
            },
            {
                "name": "info",
                "id": "info",
                "classes": "",
                "headingText": "",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 1000,
                "width": 1280,
                "height": 400,
            },
        ]
        page = self.create_mock_page(sections_data)
        detector = SectionDetector(page)

        hero_sections = detector.find_sections_by_type("hero")
        about_sections = detector.find_sections_by_type("about")
        default_sections = detector.find_sections_by_type("default")

        assert len(hero_sections) == 1
        assert len(about_sections) == 1
        assert len(default_sections) == 1  # 'info' section

    def test_find_sections_by_type_none_found(self):
        """Test finding sections by type when none match."""
        sections_data = [
            {
                "name": "hero",
                "id": "hero",
                "classes": "",
                "headingText": "",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 0,
                "width": 1280,
                "height": 600,
            },
        ]
        page = self.create_mock_page(sections_data)
        detector = SectionDetector(page)

        pricing_sections = detector.find_sections_by_type("pricing")

        assert pricing_sections == []

    def test_get_section_order(self):
        """Test getting section names in order."""
        sections_data = [
            {
                "name": "header",
                "id": "",
                "classes": "",
                "headingText": "",
                "ariaLabel": "",
                "role": "",
                "tagName": "header",
                "x": 0,
                "y": 0,
                "width": 1280,
                "height": 80,
            },
            {
                "name": "hero",
                "id": "hero",
                "classes": "",
                "headingText": "",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 80,
                "width": 1280,
                "height": 600,
            },
            {
                "name": "features",
                "id": "features",
                "classes": "",
                "headingText": "Features",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 680,
                "width": 1280,
                "height": 400,
            },
            {
                "name": "footer",
                "id": "",
                "classes": "",
                "headingText": "",
                "ariaLabel": "",
                "role": "",
                "tagName": "footer",
                "x": 0,
                "y": 1080,
                "width": 1280,
                "height": 200,
            },
        ]
        page = self.create_mock_page(sections_data)
        detector = SectionDetector(page)

        order = detector.get_section_order()

        assert order == ["header", "hero", "features", "footer"]


class TestSamplePagePatterns:
    """Test section detection on typical landing page patterns."""

    def create_landing_page_data(self):
        """Create mock data for a typical landing page."""
        return [
            {
                "name": "header",
                "id": "main-nav",
                "classes": "navbar fixed-top",
                "headingText": "",
                "ariaLabel": "Main navigation",
                "role": "navigation",
                "tagName": "header",
                "x": 0,
                "y": 0,
                "width": 1280,
                "height": 64,
            },
            {
                "name": "hero-banner",
                "id": "hero-banner",
                "classes": "hero-section bg-gradient",
                "headingText": "Build Something Amazing",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 64,
                "width": 1280,
                "height": 600,
            },
            {
                "name": "key-features",
                "id": "key-features",
                "classes": "features-grid",
                "headingText": "Key Features",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 664,
                "width": 1280,
                "height": 500,
            },
            {
                "name": "testimonials-section",
                "id": "testimonials-section",
                "classes": "testimonials customer-reviews",
                "headingText": "What Our Customers Say",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 1164,
                "width": 1280,
                "height": 400,
            },
            {
                "name": "pricing-plans",
                "id": "pricing-plans",
                "classes": "pricing-table",
                "headingText": "Simple, Transparent Pricing",
                "ariaLabel": "Pricing options",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 1564,
                "width": 1280,
                "height": 600,
            },
            {
                "name": "faq-section",
                "id": "faq-section",
                "classes": "faq accordion-section",
                "headingText": "Frequently Asked Questions",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 2164,
                "width": 1280,
                "height": 400,
            },
            {
                "name": "cta-section",
                "id": "cta-section",
                "classes": "cta-section get-started",
                "headingText": "Ready to Get Started?",
                "ariaLabel": "",
                "role": "",
                "tagName": "section",
                "x": 0,
                "y": 2564,
                "width": 1280,
                "height": 300,
            },
            {
                "name": "site-footer",
                "id": "site-footer",
                "classes": "footer-main",
                "headingText": "",
                "ariaLabel": "",
                "role": "contentinfo",
                "tagName": "footer",
                "x": 0,
                "y": 2864,
                "width": 1280,
                "height": 200,
            },
        ]

    def test_landing_page_section_types(self):
        """Test section types are correctly detected for landing page."""
        page = MagicMock()
        page.evaluate = MagicMock(return_value=self.create_landing_page_data())
        detector = SectionDetector(page)

        sections = detector.find_sections()
        types = {s.name: s.section_type for s in sections}

        assert types["header"] == "header"
        assert types["hero-banner"] == "hero"
        assert types["key-features"] == "features"
        assert types["testimonials-section"] == "testimonials"
        assert types["pricing-plans"] == "pricing"
        assert types["faq-section"] == "faq"
        assert types["cta-section"] == "cta"
        assert types["site-footer"] == "footer"

    def test_landing_page_section_order(self):
        """Test sections are in correct document order."""
        page = MagicMock()
        page.evaluate = MagicMock(return_value=self.create_landing_page_data())
        detector = SectionDetector(page)

        order = detector.get_section_order()

        expected_order = [
            "header",
            "hero-banner",
            "key-features",
            "testimonials-section",
            "pricing-plans",
            "faq-section",
            "cta-section",
            "site-footer",
        ]
        assert order == expected_order

    def test_landing_page_scroll_positions(self):
        """Test scroll positions are calculated from bounds."""
        page = MagicMock()
        page.evaluate = MagicMock(return_value=self.create_landing_page_data())
        detector = SectionDetector(page)

        sections = detector.find_sections()

        # Verify scroll positions match section tops
        for section in sections:
            assert section.scroll_position == section.bounds.top


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
