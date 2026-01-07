"""OCR using pytesseract."""

from typing import Any

import pytesseract
from PIL import Image

from programmatic_demo.utils.output import error_response, success_response

# Default minimum confidence threshold
DEFAULT_CONFIDENCE_THRESHOLD = 50


class OCR:
    """OCR controller using tesseract."""

    def __init__(self, confidence_threshold: int = DEFAULT_CONFIDENCE_THRESHOLD) -> None:
        """Initialize the OCR controller.

        Args:
            confidence_threshold: Minimum confidence for text extraction (0-100).
        """
        self._confidence_threshold = confidence_threshold

    def extract_text(self, image: Image.Image) -> str:
        """Extract all text from image.

        Args:
            image: PIL Image to process.

        Returns:
            Extracted text as string.
        """
        return pytesseract.image_to_string(image)

    def extract_elements(self, image: Image.Image) -> list[dict[str, Any]]:
        """Extract text elements with bounding boxes.

        Args:
            image: PIL Image to process.

        Returns:
            List of dicts with text, x, y, width, height, confidence.
        """
        # Get detailed OCR data
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        elements = []
        n_boxes = len(data["text"])

        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])

            # Skip empty text and low confidence results
            if not text or conf < self._confidence_threshold:
                continue

            elements.append({
                "text": text,
                "x": data["left"][i],
                "y": data["top"][i],
                "width": data["width"][i],
                "height": data["height"][i],
                "confidence": conf,
            })

        # Sort top-to-bottom, then left-to-right
        elements.sort(key=lambda e: (e["y"], e["x"]))

        return elements

    def find_text(
        self, image: Image.Image, text: str, partial: bool = False
    ) -> dict[str, int] | None:
        """Find text in image and return its center coordinates.

        Args:
            image: PIL Image to search.
            text: Text to find.
            partial: Allow partial matches.

        Returns:
            Dict with x, y center coordinates, or None if not found.
        """
        elements = self.extract_elements(image)

        text_lower = text.lower()

        for element in elements:
            element_text = element["text"].lower()

            if partial:
                # Check if search text is contained in element
                if text_lower in element_text:
                    # Return center of bounding box
                    return {
                        "x": element["x"] + element["width"] // 2,
                        "y": element["y"] + element["height"] // 2,
                    }
            else:
                # Exact match
                if element_text == text_lower:
                    return {
                        "x": element["x"] + element["width"] // 2,
                        "y": element["y"] + element["height"] // 2,
                    }

        return None


# Singleton instance for CLI usage
_ocr_instance: OCR | None = None


def get_ocr() -> OCR:
    """Get or create the singleton OCR instance."""
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = OCR()
    return _ocr_instance
