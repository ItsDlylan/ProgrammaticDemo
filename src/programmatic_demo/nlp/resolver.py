"""Target resolution for finding UI elements from descriptions.

This module provides functionality to resolve natural language target
descriptions to screen coordinates using OCR and visual analysis.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from PIL import Image

from programmatic_demo.sensors.ocr import OCR, get_ocr
from programmatic_demo.sensors.screen import Screen, get_screen

# Default similarity threshold for fuzzy matching
DEFAULT_FUZZY_THRESHOLD = 0.7


@dataclass
class ResolvedTarget:
    """A resolved target with coordinates.

    Attributes:
        coords: Screen coordinates (x, y) of the target center
        confidence: Confidence score (0.0 to 1.0) of the resolution
        element_text: Text content of the resolved element (if any)
        bounds: Bounding box (x, y, width, height) of the element
    """

    coords: tuple[int, int]
    confidence: float = 1.0
    element_text: str | None = None
    bounds: tuple[int, int, int, int] | None = None


class TargetResolver:
    """Resolves natural language target descriptions to screen coordinates.

    Uses OCR and visual analysis to find UI elements matching descriptions.
    """

    def __init__(
        self,
        ocr: OCR | None = None,
        screen: Screen | None = None,
    ) -> None:
        """Initialize the TargetResolver.

        Args:
            ocr: OCR instance (uses singleton if None).
            screen: Screen instance (uses singleton if None).
        """
        self._ocr = ocr or get_ocr()
        self._screen = screen or get_screen()

    def resolve_by_text(
        self,
        text: str,
        image: Image.Image,
        partial: bool = True,
    ) -> ResolvedTarget | None:
        """Find text on screen using OCR.

        Args:
            text: Text to search for.
            image: Screenshot image to search in.
            partial: Allow partial text matches (default True).

        Returns:
            ResolvedTarget with center coordinates, or None if not found.
        """
        result = self._ocr.find_text(image, text, partial=partial)

        if result is None:
            return None

        return ResolvedTarget(
            coords=(result["x"], result["y"]),
            confidence=1.0,
            element_text=text,
        )

    def fuzzy_match(
        self,
        text: str,
        image: Image.Image,
        threshold: float = DEFAULT_FUZZY_THRESHOLD,
    ) -> ResolvedTarget | None:
        """Find best fuzzy match for text on screen.

        Args:
            text: Text to search for.
            image: Screenshot image to search in.
            threshold: Minimum similarity ratio (0.0 to 1.0, default 0.7).

        Returns:
            ResolvedTarget with best match above threshold, or None if not found.
        """
        elements = self._ocr.extract_elements(image)

        if not elements:
            return None

        text_lower = text.lower()
        best_match: dict[str, Any] | None = None
        best_ratio = 0.0

        for element in elements:
            element_text = element["text"].lower()
            ratio = SequenceMatcher(None, text_lower, element_text).ratio()

            if ratio > best_ratio:
                best_ratio = ratio
                best_match = element

        # Return best match if above threshold
        if best_match is not None and best_ratio >= threshold:
            center_x = best_match["x"] + best_match["width"] // 2
            center_y = best_match["y"] + best_match["height"] // 2

            return ResolvedTarget(
                coords=(center_x, center_y),
                confidence=best_ratio,
                element_text=best_match["text"],
                bounds=(
                    best_match["x"],
                    best_match["y"],
                    best_match["width"],
                    best_match["height"],
                ),
            )

        return None

    def resolve(
        self,
        description: str,
        observation: dict[str, Any] | None = None,
    ) -> ResolvedTarget | None:
        """Resolve a target description to screen coordinates.

        Args:
            description: Natural language description of the target
            observation: Current observation dict with screenshot and OCR data

        Returns:
            ResolvedTarget with coordinates, or None if not found
        """
        # Get image from observation or capture fresh screenshot
        image: Image.Image | None = None

        if observation is not None:
            # Try to get image from observation result
            result = observation.get("result", {})
            screenshot = result.get("screenshot", {})

            # Try loading from path first
            path = screenshot.get("path")
            if path:
                try:
                    image = Image.open(path)
                except Exception:
                    pass

        # Capture fresh screenshot if no image from observation
        if image is None:
            image = self._screen.capture()

        # Use text-based resolution
        return self.resolve_by_text(description, image, partial=True)


# Singleton instance
_resolver: TargetResolver | None = None


def get_resolver() -> TargetResolver:
    """Get or create the singleton TargetResolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = TargetResolver()
    return _resolver
