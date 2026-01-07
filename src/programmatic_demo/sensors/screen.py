"""Screen capture using mss."""

import base64
from io import BytesIO
from pathlib import Path
from typing import Any

import mss
from PIL import Image

from programmatic_demo.utils.output import error_response, success_response


class Screen:
    """Screen capture controller."""

    def __init__(self) -> None:
        """Initialize the screen capture."""
        self._sct = mss.mss()

    def capture(self) -> Image.Image:
        """Capture the full screen.

        Returns:
            PIL Image of the screen.
        """
        # Capture primary monitor (index 1, index 0 is all monitors combined)
        monitor = self._sct.monitors[1]
        sct_img = self._sct.grab(monitor)

        # Convert to PIL Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        return img

    def capture_region(
        self, x: int, y: int, width: int, height: int
    ) -> Image.Image:
        """Capture a region of the screen.

        Args:
            x: Left edge X coordinate.
            y: Top edge Y coordinate.
            width: Region width.
            height: Region height.

        Returns:
            PIL Image of the region.
        """
        monitor = {"left": x, "top": y, "width": width, "height": height}
        sct_img = self._sct.grab(monitor)

        # Convert to PIL Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        return img

    def save(self, image: Image.Image, path: str) -> dict[str, Any]:
        """Save image to file.

        Args:
            image: PIL Image to save.
            path: Output file path.

        Returns:
            Success dict with path and file size.
        """
        try:
            file_path = Path(path).resolve()

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Determine format from extension
            ext = file_path.suffix.lower()
            if ext in [".jpg", ".jpeg"]:
                image.save(file_path, "JPEG", quality=95)
            else:
                image.save(file_path, "PNG")

            # Get file size
            file_size = file_path.stat().st_size

            return success_response(
                "screen_save",
                {
                    "path": str(file_path),
                    "size": file_size,
                    "dimensions": {"width": image.width, "height": image.height},
                },
            )
        except Exception as e:
            return error_response(
                "save_failed",
                f"Failed to save screenshot: {str(e)}",
                recoverable=True,
            )

    def to_base64(self, image: Image.Image) -> str:
        """Convert image to base64 string.

        Args:
            image: PIL Image to convert.

        Returns:
            Base64 encoded PNG string.
        """
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")


# Singleton instance for CLI usage
_screen_instance: Screen | None = None


def get_screen() -> Screen:
    """Get or create the singleton Screen instance."""
    global _screen_instance
    if _screen_instance is None:
        _screen_instance = Screen()
    return _screen_instance
