"""Framing analyzer using DOM bounds and optional vision model verification.

This module provides functions to analyze screenshots and verify proper framing
of page elements using DOM-based checks and optional Claude vision API.
"""

import base64
import hashlib
from io import BytesIO
from typing import Any

from PIL import Image

from programmatic_demo.visual.base import (
    ElementBounds,
    FramingIssue,
    FramingRule,
    Viewport,
)


class FramingAnalyzer:
    """Analyzes screenshots for proper element framing."""

    def __init__(
        self,
        tolerance: int = 50,
        vision_cache_enabled: bool = True,
    ):
        """Initialize the framing analyzer.

        Args:
            tolerance: Default tolerance in pixels for centered calculations.
            vision_cache_enabled: Whether to cache vision model results.
        """
        self.tolerance = tolerance
        self.vision_cache_enabled = vision_cache_enabled
        self._vision_cache: dict[str, dict[str, Any]] = {}

    def is_element_visible(
        self,
        element_bounds: ElementBounds,
        viewport: Viewport,
    ) -> bool:
        """Check if element is fully visible in viewport.

        Args:
            element_bounds: Bounding box of the element.
            viewport: Current viewport state.

        Returns:
            True if element is fully visible.
        """
        element_top = element_bounds.top
        element_bottom = element_bounds.bottom

        viewport_top = viewport.scroll_y
        viewport_bottom = viewport.scroll_y + viewport.height

        return element_top >= viewport_top and element_bottom <= viewport_bottom

    def is_element_partially_visible(
        self,
        element_bounds: ElementBounds,
        viewport: Viewport,
    ) -> bool:
        """Check if element is at least partially visible.

        Args:
            element_bounds: Bounding box of the element.
            viewport: Current viewport state.

        Returns:
            True if any part of element is visible.
        """
        element_top = element_bounds.top
        element_bottom = element_bounds.bottom

        viewport_top = viewport.scroll_y
        viewport_bottom = viewport.scroll_y + viewport.height

        return element_bottom > viewport_top and element_top < viewport_bottom

    def is_element_centered(
        self,
        element_bounds: ElementBounds,
        viewport: Viewport,
        tolerance: int | None = None,
    ) -> bool:
        """Check if element is centered in viewport.

        Args:
            element_bounds: Bounding box of the element.
            viewport: Current viewport state.
            tolerance: Acceptable deviation from center (pixels).

        Returns:
            True if element is centered within tolerance.
        """
        if tolerance is None:
            tolerance = self.tolerance

        element_center = element_bounds.center_y
        viewport_center = viewport.scroll_y + viewport.height / 2

        return abs(element_center - viewport_center) <= tolerance

    def is_element_cut_off(
        self,
        element_bounds: ElementBounds,
        viewport: Viewport,
    ) -> tuple[bool, str]:
        """Check if element is cut off at viewport edges.

        Args:
            element_bounds: Bounding box of the element.
            viewport: Current viewport state.

        Returns:
            Tuple of (is_cut_off, location) where location is 'top', 'bottom', or 'both'.
        """
        element_top = element_bounds.top
        element_bottom = element_bounds.bottom

        viewport_top = viewport.scroll_y
        viewport_bottom = viewport.scroll_y + viewport.height

        cut_top = element_top < viewport_top and element_bottom > viewport_top
        cut_bottom = element_bottom > viewport_bottom and element_top < viewport_bottom

        if cut_top and cut_bottom:
            return True, "both"
        elif cut_top:
            return True, "top"
        elif cut_bottom:
            return True, "bottom"
        return False, ""

    def get_element_visibility_percentage(
        self,
        element_bounds: ElementBounds,
        viewport: Viewport,
    ) -> float:
        """Calculate what percentage of element is visible.

        Args:
            element_bounds: Bounding box of the element.
            viewport: Current viewport state.

        Returns:
            Percentage visible (0.0 to 1.0).
        """
        if element_bounds.height == 0:
            return 0.0

        viewport_top = viewport.scroll_y
        viewport_bottom = viewport.scroll_y + viewport.height

        visible_top = max(element_bounds.top, viewport_top)
        visible_bottom = min(element_bounds.bottom, viewport_bottom)

        if visible_bottom <= visible_top:
            return 0.0

        visible_height = visible_bottom - visible_top
        return visible_height / element_bounds.height

    def get_framing_issues(
        self,
        elements: dict[str, ElementBounds],
        viewport: Viewport,
        expected_visible: list[str] | None = None,
        expected_centered: list[str] | None = None,
    ) -> list[FramingIssue]:
        """Analyze framing and return list of issues.

        Args:
            elements: Dict mapping element names to their bounds.
            viewport: Current viewport state.
            expected_visible: Element names that should be fully visible.
            expected_centered: Element names that should be centered.

        Returns:
            List of FramingIssue objects describing problems.
        """
        issues = []

        # Check expected visible elements
        if expected_visible:
            for name in expected_visible:
                if name not in elements:
                    issues.append(
                        FramingIssue(
                            issue_type="not_found",
                            description=f"Element '{name}' not found on page",
                            element_name=name,
                            current_position=viewport.scroll_y,
                            suggested_position=viewport.scroll_y,
                            confidence=1.0,
                        )
                    )
                    continue

                bounds = elements[name]

                if not self.is_element_visible(bounds, viewport):
                    is_cut, location = self.is_element_cut_off(bounds, viewport)

                    if is_cut:
                        # Calculate suggested scroll to make element visible
                        if location == "top":
                            suggested = bounds.top - 50  # Add padding
                        else:
                            suggested = bounds.bottom - viewport.height + 50

                        issues.append(
                            FramingIssue(
                                issue_type="cut_off",
                                description=f"Element '{name}' is cut off at {location}",
                                element_name=name,
                                current_position=viewport.scroll_y,
                                suggested_position=suggested,
                                confidence=0.95,
                            )
                        )
                    else:
                        # Element is completely out of view
                        suggested = bounds.center_y - viewport.height / 2

                        issues.append(
                            FramingIssue(
                                issue_type="not_visible",
                                description=f"Element '{name}' is not in viewport",
                                element_name=name,
                                current_position=viewport.scroll_y,
                                suggested_position=suggested,
                                confidence=0.9,
                            )
                        )

        # Check expected centered elements
        if expected_centered:
            for name in expected_centered:
                if name not in elements:
                    continue  # Already reported as not_found

                bounds = elements[name]

                if not self.is_element_centered(bounds, viewport):
                    # Calculate suggested scroll to center element
                    suggested = bounds.center_y - viewport.height / 2

                    issues.append(
                        FramingIssue(
                            issue_type="not_centered",
                            description=f"Element '{name}' is not centered in viewport",
                            element_name=name,
                            current_position=viewport.scroll_y,
                            suggested_position=suggested,
                            confidence=0.85,
                        )
                    )

        return issues

    def _get_image_hash(self, image: Image.Image) -> str:
        """Get hash of image for caching."""
        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=False)
        return hashlib.md5(buffer.getvalue()).hexdigest()

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert image to base64 string."""
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")

    async def vision_verify_framing(
        self,
        screenshot: Image.Image,
        section_description: str,
        anthropic_client: Any | None = None,
    ) -> dict[str, Any]:
        """Verify framing using Claude vision model.

        Args:
            screenshot: Screenshot image to analyze.
            section_description: Description of what section should be shown.
            anthropic_client: Optional Anthropic client (will create one if not provided).

        Returns:
            Dict with 'properly_framed', 'issues', 'suggestions', 'confidence'.
        """
        # Check cache first
        if self.vision_cache_enabled:
            cache_key = f"{self._get_image_hash(screenshot)}:{section_description}"
            if cache_key in self._vision_cache:
                return self._vision_cache[cache_key]

        # Create client if needed
        if anthropic_client is None:
            try:
                import anthropic
                anthropic_client = anthropic.Anthropic()
            except ImportError:
                return {
                    "properly_framed": None,
                    "issues": ["Anthropic SDK not installed"],
                    "suggestions": [],
                    "confidence": 0.0,
                    "error": "anthropic package not installed",
                }

        # Prepare image for API
        image_data = self._image_to_base64(screenshot)

        # Build prompt
        prompt = f"""Analyze this screenshot and determine if the following section is properly framed:

Section: {section_description}

Please evaluate:
1. Is the section header visible at a good position (not cut off)?
2. Is the main content of this section properly visible?
3. Are there any important elements cut off at the edges?
4. Is there appropriate whitespace/padding around the section?

Respond in this exact JSON format:
{{
    "properly_framed": true/false,
    "issues": ["list of specific issues if any"],
    "suggestions": ["list of suggestions to improve framing"],
    "header_visible": true/false,
    "content_visible_percentage": 0-100,
    "elements_cut_off": ["list of elements that appear cut off"]
}}"""

        try:
            response = anthropic_client.messages.create(
                model="claude-3-haiku-20240307",  # Use fast model for verification
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )

            # Parse response
            response_text = response.content[0].text

            # Try to extract JSON from response
            import json
            import re

            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                result["confidence"] = 0.8  # Vision model confidence
            else:
                result = {
                    "properly_framed": None,
                    "issues": ["Could not parse vision model response"],
                    "suggestions": [],
                    "confidence": 0.0,
                    "raw_response": response_text,
                }

            # Cache result
            if self.vision_cache_enabled:
                self._vision_cache[cache_key] = result

            return result

        except Exception as e:
            return {
                "properly_framed": None,
                "issues": [f"Vision API error: {str(e)}"],
                "suggestions": [],
                "confidence": 0.0,
                "error": str(e),
            }

    def clear_vision_cache(self) -> None:
        """Clear the vision model result cache."""
        self._vision_cache.clear()

    def combine_dom_and_vision_results(
        self,
        dom_issues: list[FramingIssue],
        vision_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Combine DOM-based and vision model results.

        Args:
            dom_issues: Issues from DOM analysis.
            vision_result: Result from vision model.

        Returns:
            Combined analysis result.
        """
        # Start with DOM issues
        all_issues = [
            {
                "type": issue.issue_type,
                "description": issue.description,
                "element": issue.element_name,
                "source": "dom",
                "confidence": issue.confidence,
            }
            for issue in dom_issues
        ]

        # Add vision issues
        if vision_result.get("issues"):
            for issue in vision_result["issues"]:
                all_issues.append({
                    "type": "vision_detected",
                    "description": issue,
                    "element": None,
                    "source": "vision",
                    "confidence": vision_result.get("confidence", 0.5),
                })

        # Determine overall framing status
        has_dom_issues = len(dom_issues) > 0
        vision_framed = vision_result.get("properly_framed")

        if vision_framed is None:
            # Vision unavailable, use only DOM
            properly_framed = not has_dom_issues
            confidence = 0.7 if not has_dom_issues else 0.9
        elif has_dom_issues and not vision_framed:
            # Both agree there are issues
            properly_framed = False
            confidence = 0.95
        elif not has_dom_issues and vision_framed:
            # Both agree framing is good
            properly_framed = True
            confidence = 0.95
        else:
            # Disagreement - trust DOM more for positioning issues
            properly_framed = not has_dom_issues
            confidence = 0.6

        return {
            "properly_framed": properly_framed,
            "confidence": confidence,
            "issues": all_issues,
            "suggestions": vision_result.get("suggestions", []),
            "dom_issue_count": len(dom_issues),
            "vision_issue_count": len(vision_result.get("issues", [])),
        }
