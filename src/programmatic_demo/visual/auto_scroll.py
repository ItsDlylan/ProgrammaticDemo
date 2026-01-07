"""Auto-scroll correction loop for achieving proper framing.

This module provides functions to automatically adjust scroll position
until page elements are properly framed according to specified rules.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from programmatic_demo.visual.base import (
    ElementBounds,
    FramingRule,
    Viewport,
)
from programmatic_demo.visual.framing_rules import (
    calculate_optimal_scroll,
    is_element_properly_framed,
)

logger = logging.getLogger(__name__)


@dataclass
class ScrollResult:
    """Result of an auto-scroll correction operation.

    Attributes:
        success: Whether proper framing was achieved.
        final_position: Final scroll Y position.
        iterations: Number of scroll adjustments made.
        adjustments: List of (position, adjustment) tuples for debugging.
        error: Error message if operation failed.
    """

    success: bool
    final_position: float
    iterations: int
    adjustments: list[tuple[float, float]]
    error: str | None = None


class AutoScroller:
    """Automatically adjusts scroll position to achieve proper framing."""

    def __init__(
        self,
        page: Any,
        max_iterations: int = 5,
        min_adjustment: float = 5.0,
    ):
        """Initialize the auto-scroller.

        Args:
            page: Playwright page object (sync).
            max_iterations: Maximum scroll adjustments to attempt.
            min_adjustment: Minimum scroll adjustment to make (pixels).
        """
        self._page = page
        self.max_iterations = max_iterations
        self.min_adjustment = min_adjustment

    def get_viewport(self) -> Viewport:
        """Get current viewport state."""
        viewport_size = self._page.viewport_size or {"width": 1280, "height": 800}
        scroll_y = self._page.evaluate("window.scrollY")
        scroll_x = self._page.evaluate("window.scrollX")

        return Viewport(
            width=viewport_size["width"],
            height=viewport_size["height"],
            scroll_y=scroll_y,
            scroll_x=scroll_x,
        )

    def scroll_to(self, y: float) -> None:
        """Scroll to a specific Y position."""
        self._page.evaluate(f"window.scrollTo(0, {y})")

    def smooth_scroll_to(self, y: float, duration: float = 0.5) -> None:
        """Smooth scroll to a Y position.

        Args:
            y: Target scroll Y position.
            duration: Animation duration in seconds.
        """
        self._page.evaluate(
            f"""
            (async () => {{
                const start = window.scrollY;
                const target = {y};
                const duration = {duration * 1000};
                const startTime = performance.now();

                function easeInOutCubic(t) {{
                    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
                }}

                return new Promise(resolve => {{
                    function step(currentTime) {{
                        const elapsed = currentTime - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        const eased = easeInOutCubic(progress);

                        window.scrollTo(0, start + (target - start) * eased);

                        if (progress < 1) {{
                            requestAnimationFrame(step);
                        }} else {{
                            resolve();
                        }}
                    }}
                    requestAnimationFrame(step);
                }});
            }})()
        """
        )
        # Wait for animation
        import time
        time.sleep(duration + 0.1)

    def scroll_to_frame(
        self,
        element_bounds: ElementBounds,
        rule: FramingRule,
        smooth: bool = True,
    ) -> ScrollResult:
        """Scroll to properly frame an element.

        Args:
            element_bounds: Bounding box of element to frame.
            rule: Framing rule to apply.
            smooth: Whether to use smooth scrolling.

        Returns:
            ScrollResult with success status and details.
        """
        adjustments = []
        viewport = self.get_viewport()

        for iteration in range(self.max_iterations):
            # Check if already properly framed
            if is_element_properly_framed(element_bounds, viewport, rule):
                logger.debug(
                    f"Element properly framed after {iteration} iterations "
                    f"at position {viewport.scroll_y}"
                )
                return ScrollResult(
                    success=True,
                    final_position=viewport.scroll_y,
                    iterations=iteration,
                    adjustments=adjustments,
                )

            # Calculate optimal scroll position
            optimal = calculate_optimal_scroll(element_bounds, viewport, rule)
            adjustment = optimal - viewport.scroll_y

            # Skip tiny adjustments
            if abs(adjustment) < self.min_adjustment:
                logger.debug(
                    f"Adjustment too small ({adjustment:.1f}px), accepting current position"
                )
                return ScrollResult(
                    success=True,
                    final_position=viewport.scroll_y,
                    iterations=iteration,
                    adjustments=adjustments,
                )

            logger.debug(
                f"Iteration {iteration + 1}: scroll {viewport.scroll_y:.0f} -> {optimal:.0f} "
                f"(adjustment: {adjustment:+.0f}px)"
            )

            adjustments.append((viewport.scroll_y, adjustment))

            # Perform scroll
            if smooth:
                self.smooth_scroll_to(optimal)
            else:
                self.scroll_to(optimal)

            # Update viewport
            viewport = self.get_viewport()

        # Max iterations reached
        logger.warning(
            f"Max iterations ({self.max_iterations}) reached without achieving "
            f"proper framing. Final position: {viewport.scroll_y}"
        )

        return ScrollResult(
            success=False,
            final_position=viewport.scroll_y,
            iterations=self.max_iterations,
            adjustments=adjustments,
            error=f"Max iterations ({self.max_iterations}) reached",
        )

    def scroll_to_element(
        self,
        selector: str,
        rule: FramingRule,
        smooth: bool = True,
    ) -> ScrollResult:
        """Scroll to frame a specific element by selector.

        Args:
            selector: CSS selector for the element.
            rule: Framing rule to apply.
            smooth: Whether to use smooth scrolling.

        Returns:
            ScrollResult with success status and details.
        """
        try:
            element = self._page.query_selector(selector)
            if element is None:
                return ScrollResult(
                    success=False,
                    final_position=self.get_viewport().scroll_y,
                    iterations=0,
                    adjustments=[],
                    error=f"Element not found: {selector}",
                )

            box = element.bounding_box()
            if box is None:
                return ScrollResult(
                    success=False,
                    final_position=self.get_viewport().scroll_y,
                    iterations=0,
                    adjustments=[],
                    error=f"Could not get bounding box for: {selector}",
                )

            # Bounding box is relative to viewport, need to adjust for scroll
            scroll_y = self._page.evaluate("window.scrollY")
            bounds = ElementBounds(
                top=box["y"] + scroll_y,
                left=box["x"],
                width=box["width"],
                height=box["height"],
            )

            return self.scroll_to_frame(bounds, rule, smooth)

        except Exception as e:
            return ScrollResult(
                success=False,
                final_position=self.get_viewport().scroll_y,
                iterations=0,
                adjustments=[],
                error=str(e),
            )


class AsyncAutoScroller:
    """Async version of AutoScroller."""

    def __init__(
        self,
        page: Any,
        max_iterations: int = 5,
        min_adjustment: float = 5.0,
    ):
        """Initialize the async auto-scroller.

        Args:
            page: Async Playwright page object.
            max_iterations: Maximum scroll adjustments to attempt.
            min_adjustment: Minimum scroll adjustment to make (pixels).
        """
        self._page = page
        self.max_iterations = max_iterations
        self.min_adjustment = min_adjustment

    async def get_viewport(self) -> Viewport:
        """Get current viewport state."""
        viewport_size = self._page.viewport_size or {"width": 1280, "height": 800}
        scroll_y = await self._page.evaluate("window.scrollY")
        scroll_x = await self._page.evaluate("window.scrollX")

        return Viewport(
            width=viewport_size["width"],
            height=viewport_size["height"],
            scroll_y=scroll_y,
            scroll_x=scroll_x,
        )

    async def scroll_to(self, y: float) -> None:
        """Scroll to a specific Y position."""
        await self._page.evaluate(f"window.scrollTo(0, {y})")

    async def smooth_scroll_to(self, y: float, duration: float = 0.5) -> None:
        """Smooth scroll to a Y position."""
        await self._page.evaluate(
            f"""
            (async () => {{
                const start = window.scrollY;
                const target = {y};
                const duration = {duration * 1000};
                const startTime = performance.now();

                function easeInOutCubic(t) {{
                    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
                }}

                return new Promise(resolve => {{
                    function step(currentTime) {{
                        const elapsed = currentTime - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        const eased = easeInOutCubic(progress);

                        window.scrollTo(0, start + (target - start) * eased);

                        if (progress < 1) {{
                            requestAnimationFrame(step);
                        }} else {{
                            resolve();
                        }}
                    }}
                    requestAnimationFrame(step);
                }});
            }})()
        """
        )
        await asyncio.sleep(duration + 0.1)

    async def scroll_to_frame(
        self,
        element_bounds: ElementBounds,
        rule: FramingRule,
        smooth: bool = True,
    ) -> ScrollResult:
        """Scroll to properly frame an element."""
        adjustments = []
        viewport = await self.get_viewport()

        for iteration in range(self.max_iterations):
            if is_element_properly_framed(element_bounds, viewport, rule):
                return ScrollResult(
                    success=True,
                    final_position=viewport.scroll_y,
                    iterations=iteration,
                    adjustments=adjustments,
                )

            optimal = calculate_optimal_scroll(element_bounds, viewport, rule)
            adjustment = optimal - viewport.scroll_y

            if abs(adjustment) < self.min_adjustment:
                return ScrollResult(
                    success=True,
                    final_position=viewport.scroll_y,
                    iterations=iteration,
                    adjustments=adjustments,
                )

            adjustments.append((viewport.scroll_y, adjustment))

            if smooth:
                await self.smooth_scroll_to(optimal)
            else:
                await self.scroll_to(optimal)

            viewport = await self.get_viewport()

        return ScrollResult(
            success=False,
            final_position=viewport.scroll_y,
            iterations=self.max_iterations,
            adjustments=adjustments,
            error=f"Max iterations ({self.max_iterations}) reached",
        )

    async def scroll_to_element(
        self,
        selector: str,
        rule: FramingRule,
        smooth: bool = True,
    ) -> ScrollResult:
        """Scroll to frame a specific element by selector."""
        try:
            element = await self._page.query_selector(selector)
            if element is None:
                return ScrollResult(
                    success=False,
                    final_position=(await self.get_viewport()).scroll_y,
                    iterations=0,
                    adjustments=[],
                    error=f"Element not found: {selector}",
                )

            box = await element.bounding_box()
            if box is None:
                return ScrollResult(
                    success=False,
                    final_position=(await self.get_viewport()).scroll_y,
                    iterations=0,
                    adjustments=[],
                    error=f"Could not get bounding box for: {selector}",
                )

            scroll_y = await self._page.evaluate("window.scrollY")
            bounds = ElementBounds(
                top=box["y"] + scroll_y,
                left=box["x"],
                width=box["width"],
                height=box["height"],
            )

            return await self.scroll_to_frame(bounds, rule, smooth)

        except Exception as e:
            return ScrollResult(
                success=False,
                final_position=(await self.get_viewport()).scroll_y,
                iterations=0,
                adjustments=[],
                error=str(e),
            )
