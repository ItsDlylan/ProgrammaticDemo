"""Semantic section detection from DOM structure.

This module identifies page sections based on HTML structure, ARIA landmarks,
heading tags, and common class/id patterns.
"""

import re
from typing import Any

from programmatic_demo.visual.base import ElementBounds, Section


# Common patterns for section type detection
SECTION_TYPE_PATTERNS = {
    "hero": [
        r"hero",
        r"banner",
        r"jumbotron",
        r"masthead",
        r"splash",
        r"intro",
        r"landing",
    ],
    "features": [
        r"features?",
        r"benefits?",
        r"services?",
        r"capabilities",
        r"highlights?",
        r"why-us",
        r"what-we",
    ],
    "pricing": [
        r"pricing",
        r"plans?",
        r"packages?",
        r"subscription",
        r"tiers?",
    ],
    "faq": [
        r"faq",
        r"questions?",
        r"answers?",
        r"help",
        r"support",
        r"accordion",
    ],
    "cta": [
        r"cta",
        r"call-to-action",
        r"signup",
        r"sign-up",
        r"register",
        r"get-started",
        r"join",
        r"trial",
        r"waitlist",
    ],
    "testimonials": [
        r"testimonials?",
        r"reviews?",
        r"quotes?",
        r"social-proof",
        r"customers?",
    ],
    "about": [
        r"about",
        r"team",
        r"story",
        r"mission",
        r"company",
    ],
    "contact": [
        r"contact",
        r"get-in-touch",
        r"reach",
        r"form",
    ],
    "footer": [
        r"footer",
        r"bottom",
        r"site-footer",
    ],
    "header": [
        r"header",
        r"navbar",
        r"nav",
        r"top-bar",
        r"site-header",
    ],
}


def detect_section_type(
    element_id: str,
    element_classes: str,
    heading_text: str,
    aria_label: str,
) -> str:
    """Detect section type from element attributes.

    Args:
        element_id: Element ID attribute.
        element_classes: Element class attribute.
        heading_text: Text from first heading in section.
        aria_label: ARIA label if present.

    Returns:
        Section type string (hero, features, pricing, etc.) or 'default'.
    """
    # Combine all text for matching
    search_text = " ".join([
        element_id or "",
        element_classes or "",
        heading_text or "",
        aria_label or "",
    ]).lower()

    for section_type, patterns in SECTION_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, search_text, re.IGNORECASE):
                return section_type

    return "default"


class SectionDetector:
    """Detects semantic sections on a page."""

    def __init__(self, page: Any) -> None:
        """Initialize with a Playwright page object.

        Args:
            page: Playwright page (sync).
        """
        self._page = page

    def find_sections(self) -> list[Section]:
        """Find all semantic sections on the page.

        Returns:
            List of Section objects in document order.
        """
        sections_data = self._page.evaluate(
            """() => {
            const sections = [];
            const scrollY = window.scrollY;

            // Find all section-like elements
            const selectors = [
                'section',
                '[role="region"]',
                '[role="main"]',
                '[role="banner"]',
                '[role="contentinfo"]',
                '[data-section]',
                'main',
                'header',
                'footer',
                'article',
            ];

            const candidates = document.querySelectorAll(selectors.join(', '));
            const seen = new Set();

            for (const el of candidates) {
                // Skip if already processed (nested sections)
                if (seen.has(el)) continue;

                // Mark all parent sections as seen to avoid duplicates
                let parent = el.parentElement;
                while (parent) {
                    if (parent.tagName === 'SECTION' || parent.hasAttribute('data-section')) {
                        seen.add(parent);
                    }
                    parent = parent.parentElement;
                }

                const rect = el.getBoundingClientRect();

                // Skip tiny or hidden elements
                if (rect.height < 50 || rect.width < 50) continue;

                // Get section identifier
                const id = el.id || '';
                const classes = el.className || '';
                const dataSection = el.getAttribute('data-section') || '';
                const ariaLabel = el.getAttribute('aria-label') || '';
                const role = el.getAttribute('role') || '';

                // Get first heading text
                const heading = el.querySelector('h1, h2, h3, h4');
                const headingText = heading ? heading.textContent.trim() : '';

                // Determine name (prefer data-section, then id, then heading)
                let name = dataSection || id || headingText || el.tagName.toLowerCase();
                name = name.slice(0, 50);

                sections.push({
                    name: name,
                    id: id,
                    classes: typeof classes === 'string' ? classes : '',
                    headingText: headingText,
                    ariaLabel: ariaLabel,
                    role: role,
                    tagName: el.tagName.toLowerCase(),
                    x: rect.left,
                    y: rect.top + scrollY,
                    width: rect.width,
                    height: rect.height,
                });
            }

            // Sort by vertical position
            sections.sort((a, b) => a.y - b.y);

            return sections;
        }"""
        )

        # Convert to Section objects
        result = []
        for s in sections_data:
            bounds = ElementBounds(
                top=s["y"],
                left=s["x"],
                width=s["width"],
                height=s["height"],
            )

            section_type = detect_section_type(
                s["id"],
                s["classes"],
                s["headingText"],
                s["ariaLabel"],
            )

            # Handle special cases based on tag
            if s["tagName"] == "header" and section_type == "default":
                section_type = "header"
            elif s["tagName"] == "footer" and section_type == "default":
                section_type = "footer"
            elif s["role"] == "banner" and section_type == "default":
                section_type = "header"
            elif s["role"] == "contentinfo" and section_type == "default":
                section_type = "footer"

            section = Section(
                name=s["name"],
                section_type=section_type,
                bounds=bounds,
                scroll_position=bounds.top,
            )
            result.append(section)

        return result

    def find_section_by_name(self, name: str) -> Section | None:
        """Find a specific section by name.

        Args:
            name: Section name to find (case-insensitive partial match).

        Returns:
            Section if found, None otherwise.
        """
        sections = self.find_sections()
        name_lower = name.lower()

        for section in sections:
            if name_lower in section.name.lower():
                return section

        return None

    def find_sections_by_type(self, section_type: str) -> list[Section]:
        """Find all sections of a specific type.

        Args:
            section_type: Type to filter by (hero, features, pricing, etc.).

        Returns:
            List of matching sections.
        """
        sections = self.find_sections()
        return [s for s in sections if s.section_type == section_type]

    def get_section_order(self) -> list[str]:
        """Get list of section names in document order.

        Returns:
            List of section names from top to bottom.
        """
        sections = self.find_sections()
        return [s.name for s in sections]


class AsyncSectionDetector:
    """Async version of SectionDetector."""

    def __init__(self, page: Any) -> None:
        """Initialize with an async Playwright page object.

        Args:
            page: Async Playwright page.
        """
        self._page = page

    async def find_sections(self) -> list[Section]:
        """Find all semantic sections on the page.

        Returns:
            List of Section objects in document order.
        """
        sections_data = await self._page.evaluate(
            """() => {
            const sections = [];
            const scrollY = window.scrollY;

            const selectors = [
                'section',
                '[role="region"]',
                '[role="main"]',
                '[role="banner"]',
                '[role="contentinfo"]',
                '[data-section]',
                'main',
                'header',
                'footer',
                'article',
            ];

            const candidates = document.querySelectorAll(selectors.join(', '));
            const seen = new Set();

            for (const el of candidates) {
                if (seen.has(el)) continue;

                let parent = el.parentElement;
                while (parent) {
                    if (parent.tagName === 'SECTION' || parent.hasAttribute('data-section')) {
                        seen.add(parent);
                    }
                    parent = parent.parentElement;
                }

                const rect = el.getBoundingClientRect();
                if (rect.height < 50 || rect.width < 50) continue;

                const id = el.id || '';
                const classes = el.className || '';
                const dataSection = el.getAttribute('data-section') || '';
                const ariaLabel = el.getAttribute('aria-label') || '';
                const role = el.getAttribute('role') || '';

                const heading = el.querySelector('h1, h2, h3, h4');
                const headingText = heading ? heading.textContent.trim() : '';

                let name = dataSection || id || headingText || el.tagName.toLowerCase();
                name = name.slice(0, 50);

                sections.push({
                    name: name,
                    id: id,
                    classes: typeof classes === 'string' ? classes : '',
                    headingText: headingText,
                    ariaLabel: ariaLabel,
                    role: role,
                    tagName: el.tagName.toLowerCase(),
                    x: rect.left,
                    y: rect.top + scrollY,
                    width: rect.width,
                    height: rect.height,
                });
            }

            sections.sort((a, b) => a.y - b.y);
            return sections;
        }"""
        )

        result = []
        for s in sections_data:
            bounds = ElementBounds(
                top=s["y"],
                left=s["x"],
                width=s["width"],
                height=s["height"],
            )

            section_type = detect_section_type(
                s["id"],
                s["classes"],
                s["headingText"],
                s["ariaLabel"],
            )

            if s["tagName"] == "header" and section_type == "default":
                section_type = "header"
            elif s["tagName"] == "footer" and section_type == "default":
                section_type = "footer"
            elif s["role"] == "banner" and section_type == "default":
                section_type = "header"
            elif s["role"] == "contentinfo" and section_type == "default":
                section_type = "footer"

            section = Section(
                name=s["name"],
                section_type=section_type,
                bounds=bounds,
                scroll_position=bounds.top,
            )
            result.append(section)

        return result

    async def find_section_by_name(self, name: str) -> Section | None:
        """Find a specific section by name."""
        sections = await self.find_sections()
        name_lower = name.lower()

        for section in sections:
            if name_lower in section.name.lower():
                return section

        return None

    async def find_sections_by_type(self, section_type: str) -> list[Section]:
        """Find all sections of a specific type."""
        sections = await self.find_sections()
        return [s for s in sections if s.section_type == section_type]
