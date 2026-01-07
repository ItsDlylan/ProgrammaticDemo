"""Element bounds detection via DOM queries.

This module provides functions to get bounding boxes of page elements
using Playwright's DOM APIs.
"""

from functools import lru_cache
from typing import Any

from programmatic_demo.visual.base import ElementBounds, Viewport


class ElementBoundsDetector:
    """Detects element bounding boxes on a page."""

    def __init__(self, page: Any) -> None:
        """Initialize with a Playwright page object.

        Args:
            page: Playwright page (sync or async).
        """
        self._page = page
        self._cache: dict[str, ElementBounds | None] = {}

    def clear_cache(self) -> None:
        """Clear the element bounds cache."""
        self._cache.clear()

    def get_element_bounds(self, selector: str) -> ElementBounds | None:
        """Get bounding box for an element by CSS selector.

        Args:
            selector: CSS selector for the element.

        Returns:
            ElementBounds if found, None otherwise.
        """
        # Check cache first
        cache_key = f"selector:{selector}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            element = self._page.query_selector(selector)
            if element is None:
                self._cache[cache_key] = None
                return None

            box = element.bounding_box()
            if box is None:
                self._cache[cache_key] = None
                return None

            bounds = ElementBounds(
                top=box["y"],
                left=box["x"],
                width=box["width"],
                height=box["height"],
            )
            self._cache[cache_key] = bounds
            return bounds

        except Exception:
            self._cache[cache_key] = None
            return None

    def get_element_bounds_by_text(self, text: str) -> ElementBounds | None:
        """Get bounding box for an element containing specific text.

        Args:
            text: Text content to search for.

        Returns:
            ElementBounds if found, None otherwise.
        """
        cache_key = f"text:{text}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # Use Playwright's text selector
            element = self._page.query_selector(f"text={text}")
            if element is None:
                self._cache[cache_key] = None
                return None

            box = element.bounding_box()
            if box is None:
                self._cache[cache_key] = None
                return None

            bounds = ElementBounds(
                top=box["y"],
                left=box["x"],
                width=box["width"],
                height=box["height"],
            )
            self._cache[cache_key] = bounds
            return bounds

        except Exception:
            self._cache[cache_key] = None
            return None

    def get_element_bounds_by_role(
        self, role: str, name: str | None = None
    ) -> ElementBounds | None:
        """Get bounding box for an element by accessibility role.

        Args:
            role: ARIA role (button, heading, navigation, etc.).
            name: Optional accessible name to match.

        Returns:
            ElementBounds if found, None otherwise.
        """
        cache_key = f"role:{role}:{name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            if name:
                element = self._page.get_by_role(role, name=name).first
            else:
                element = self._page.get_by_role(role).first

            if element is None:
                self._cache[cache_key] = None
                return None

            box = element.bounding_box()
            if box is None:
                self._cache[cache_key] = None
                return None

            bounds = ElementBounds(
                top=box["y"],
                left=box["x"],
                width=box["width"],
                height=box["height"],
            )
            self._cache[cache_key] = bounds
            return bounds

        except Exception:
            self._cache[cache_key] = None
            return None

    def get_section_bounds(self, section_name: str) -> ElementBounds | None:
        """Get bounding box for a semantic section.

        Searches for sections using common patterns:
        - ID matching (id="section_name")
        - Data attribute (data-section="section_name")
        - Heading text containing section_name
        - ARIA landmarks

        Args:
            section_name: Name/identifier of the section.

        Returns:
            ElementBounds if found, None otherwise.
        """
        cache_key = f"section:{section_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try various selectors in order of specificity
        selectors = [
            f"#{section_name}",
            f"[data-section='{section_name}']",
            f"[data-testid='{section_name}']",
            f"section#{section_name}",
            f"div#{section_name}",
            f"[id*='{section_name}' i]",  # Case-insensitive partial match
        ]

        for selector in selectors:
            bounds = self.get_element_bounds(selector)
            if bounds is not None:
                self._cache[cache_key] = bounds
                return bounds

        # Try finding by heading text
        bounds = self.get_element_bounds_by_text(section_name)
        if bounds is not None:
            # Found heading, try to get parent section
            parent_bounds = self._get_parent_section_bounds(section_name)
            if parent_bounds is not None:
                self._cache[cache_key] = parent_bounds
                return parent_bounds
            self._cache[cache_key] = bounds
            return bounds

        self._cache[cache_key] = None
        return None

    def _get_parent_section_bounds(self, heading_text: str) -> ElementBounds | None:
        """Get bounds of the section containing a heading.

        Args:
            heading_text: Text of the heading.

        Returns:
            ElementBounds of parent section if found.
        """
        try:
            # Find the heading's parent section/div
            result = self._page.evaluate(
                """(headingText) => {
                const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
                const heading = headings.find(h => h.textContent.includes(headingText));
                if (!heading) return null;

                // Walk up to find a section-like container
                let parent = heading.parentElement;
                while (parent && parent !== document.body) {
                    const tag = parent.tagName.toLowerCase();
                    if (tag === 'section' || tag === 'article' ||
                        (tag === 'div' && (parent.id || parent.className.includes('section')))) {
                        const rect = parent.getBoundingClientRect();
                        const scrollY = window.scrollY;
                        return {
                            x: rect.left,
                            y: rect.top + scrollY,
                            width: rect.width,
                            height: rect.height
                        };
                    }
                    parent = parent.parentElement;
                }
                return null;
            }""",
                heading_text,
            )

            if result:
                return ElementBounds(
                    top=result["y"],
                    left=result["x"],
                    width=result["width"],
                    height=result["height"],
                )
            return None

        except Exception:
            return None

    def get_viewport(self) -> Viewport:
        """Get current viewport dimensions and scroll position.

        Returns:
            Viewport with current dimensions and scroll.
        """
        try:
            viewport_size = self._page.viewport_size or {"width": 1280, "height": 800}
            scroll_y = self._page.evaluate("window.scrollY")
            scroll_x = self._page.evaluate("window.scrollX")

            return Viewport(
                width=viewport_size["width"],
                height=viewport_size["height"],
                scroll_y=scroll_y,
                scroll_x=scroll_x,
            )
        except Exception:
            return Viewport(width=1280, height=800)

    def get_page_height(self) -> float:
        """Get total page height.

        Returns:
            Page height in pixels.
        """
        try:
            return self._page.evaluate(
                "Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
            )
        except Exception:
            return 0.0

    def get_all_sections(self) -> list[tuple[str, ElementBounds]]:
        """Get all identifiable sections on the page.

        Returns:
            List of (section_name, ElementBounds) tuples.
        """
        try:
            sections_data = self._page.evaluate(
                """() => {
                const sections = [];

                // Find all section-like elements
                const candidates = document.querySelectorAll(
                    'section, [data-section], [role="region"], ' +
                    'main, header, footer, article, aside, nav'
                );

                for (const el of candidates) {
                    const rect = el.getBoundingClientRect();
                    const scrollY = window.scrollY;

                    // Get section identifier
                    let name = el.id ||
                               el.getAttribute('data-section') ||
                               el.getAttribute('aria-label') ||
                               el.tagName.toLowerCase();

                    // Try to get name from first heading
                    const heading = el.querySelector('h1, h2, h3');
                    if (heading && !el.id) {
                        name = heading.textContent.trim().slice(0, 50);
                    }

                    sections.push({
                        name: name,
                        x: rect.left,
                        y: rect.top + scrollY,
                        width: rect.width,
                        height: rect.height
                    });
                }

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
                result.append((s["name"], bounds))

            return result

        except Exception:
            return []


class AsyncElementBoundsDetector:
    """Async version of ElementBoundsDetector for async Playwright pages."""

    def __init__(self, page: Any) -> None:
        """Initialize with an async Playwright page object.

        Args:
            page: Async Playwright page.
        """
        self._page = page
        self._cache: dict[str, ElementBounds | None] = {}

    def clear_cache(self) -> None:
        """Clear the element bounds cache."""
        self._cache.clear()

    async def get_element_bounds(self, selector: str) -> ElementBounds | None:
        """Get bounding box for an element by CSS selector.

        Args:
            selector: CSS selector for the element.

        Returns:
            ElementBounds if found, None otherwise.
        """
        cache_key = f"selector:{selector}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            element = await self._page.query_selector(selector)
            if element is None:
                self._cache[cache_key] = None
                return None

            box = await element.bounding_box()
            if box is None:
                self._cache[cache_key] = None
                return None

            bounds = ElementBounds(
                top=box["y"],
                left=box["x"],
                width=box["width"],
                height=box["height"],
            )
            self._cache[cache_key] = bounds
            return bounds

        except Exception:
            self._cache[cache_key] = None
            return None

    async def get_element_bounds_by_text(self, text: str) -> ElementBounds | None:
        """Get bounding box for an element containing specific text."""
        cache_key = f"text:{text}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            element = await self._page.query_selector(f"text={text}")
            if element is None:
                self._cache[cache_key] = None
                return None

            box = await element.bounding_box()
            if box is None:
                self._cache[cache_key] = None
                return None

            bounds = ElementBounds(
                top=box["y"],
                left=box["x"],
                width=box["width"],
                height=box["height"],
            )
            self._cache[cache_key] = bounds
            return bounds

        except Exception:
            self._cache[cache_key] = None
            return None

    async def get_section_bounds(self, section_name: str) -> ElementBounds | None:
        """Get bounding box for a semantic section."""
        cache_key = f"section:{section_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        selectors = [
            f"#{section_name}",
            f"[data-section='{section_name}']",
            f"[data-testid='{section_name}']",
            f"[id*='{section_name}' i]",
        ]

        for selector in selectors:
            bounds = await self.get_element_bounds(selector)
            if bounds is not None:
                self._cache[cache_key] = bounds
                return bounds

        bounds = await self.get_element_bounds_by_text(section_name)
        if bounds is not None:
            self._cache[cache_key] = bounds
            return bounds

        self._cache[cache_key] = None
        return None

    async def get_viewport(self) -> Viewport:
        """Get current viewport dimensions and scroll position."""
        try:
            viewport_size = self._page.viewport_size or {"width": 1280, "height": 800}
            scroll_y = await self._page.evaluate("window.scrollY")
            scroll_x = await self._page.evaluate("window.scrollX")

            return Viewport(
                width=viewport_size["width"],
                height=viewport_size["height"],
                scroll_y=scroll_y,
                scroll_x=scroll_x,
            )
        except Exception:
            return Viewport(width=1280, height=800)

    async def get_page_height(self) -> float:
        """Get total page height."""
        try:
            return await self._page.evaluate(
                "Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
            )
        except Exception:
            return 0.0
