"""Animation completion detection using frame differencing.

This module provides functions to detect when page animations have completed
by comparing consecutive screenshots and measuring pixel changes.
"""

import asyncio
import time
from typing import Any, Callable

import numpy as np
from PIL import Image


def frame_diff(image1: Image.Image, image2: Image.Image) -> float:
    """Calculate pixel difference between two frames.

    Args:
        image1: First image.
        image2: Second image.

    Returns:
        Percentage of pixels changed (0.0 to 1.0).
    """
    # Ensure same size
    if image1.size != image2.size:
        image2 = image2.resize(image1.size)

    # Convert to numpy arrays
    arr1 = np.array(image1.convert("RGB"), dtype=np.float32)
    arr2 = np.array(image2.convert("RGB"), dtype=np.float32)

    # Calculate absolute difference
    diff = np.abs(arr1 - arr2)

    # A pixel is "changed" if any channel differs by more than threshold
    pixel_threshold = 10  # Allow small variations (compression artifacts, anti-aliasing)
    changed_pixels = np.any(diff > pixel_threshold, axis=2)

    # Calculate percentage of changed pixels
    total_pixels = changed_pixels.size
    changed_count = np.sum(changed_pixels)

    return float(changed_count / total_pixels)


def frame_diff_region(
    image1: Image.Image,
    image2: Image.Image,
    region: tuple[int, int, int, int] | None = None,
    exclude_regions: list[tuple[int, int, int, int]] | None = None,
) -> float:
    """Calculate pixel difference with optional region filtering.

    Args:
        image1: First image.
        image2: Second image.
        region: Optional (x, y, width, height) to limit comparison area.
        exclude_regions: Optional list of (x, y, width, height) regions to ignore.

    Returns:
        Percentage of pixels changed (0.0 to 1.0).
    """
    # Crop to region if specified
    if region:
        x, y, w, h = region
        image1 = image1.crop((x, y, x + w, y + h))
        image2 = image2.crop((x, y, x + w, y + h))

    # Ensure same size
    if image1.size != image2.size:
        image2 = image2.resize(image1.size)

    # Convert to numpy arrays
    arr1 = np.array(image1.convert("RGB"), dtype=np.float32)
    arr2 = np.array(image2.convert("RGB"), dtype=np.float32)

    # Calculate difference
    diff = np.abs(arr1 - arr2)
    pixel_threshold = 10
    changed_mask = np.any(diff > pixel_threshold, axis=2)

    # Create exclusion mask if needed
    if exclude_regions:
        offset_x = region[0] if region else 0
        offset_y = region[1] if region else 0

        for ex, ey, ew, eh in exclude_regions:
            # Adjust for region offset
            ex -= offset_x
            ey -= offset_y

            # Clip to image bounds
            ex = max(0, ex)
            ey = max(0, ey)
            ex2 = min(changed_mask.shape[1], ex + ew)
            ey2 = min(changed_mask.shape[0], ey + eh)

            # Zero out excluded region
            if ex < ex2 and ey < ey2:
                changed_mask[ey:ey2, ex:ex2] = False

    # Calculate percentage
    total_pixels = changed_mask.size
    changed_count = np.sum(changed_mask)

    return float(changed_count / total_pixels)


def wait_for_animation_complete_sync(
    take_screenshot: Callable[[], Image.Image],
    threshold: float = 0.03,
    timeout: float = 5.0,
    interval: float = 0.1,
    stable_frames_required: int = 3,
    exclude_regions: list[tuple[int, int, int, int]] | None = None,
) -> bool:
    """Wait for animations to complete (synchronous version).

    Args:
        take_screenshot: Function that returns current screenshot as PIL Image.
        threshold: Pixel change threshold (0.0 to 1.0). Default 0.03 (3%).
        timeout: Maximum wait time in seconds.
        interval: Time between frame captures in seconds.
        stable_frames_required: Number of consecutive stable frames needed.
        exclude_regions: Optional regions to ignore (cursor area, etc.).

    Returns:
        True if animations completed, False if timeout.
    """
    start_time = time.time()
    stable_count = 0
    prev_frame = take_screenshot()

    while time.time() - start_time < timeout:
        time.sleep(interval)
        current_frame = take_screenshot()

        diff = frame_diff_region(prev_frame, current_frame, exclude_regions=exclude_regions)

        if diff < threshold:
            stable_count += 1
            if stable_count >= stable_frames_required:
                return True
        else:
            stable_count = 0

        prev_frame = current_frame

    return False


async def wait_for_animation_complete(
    take_screenshot: Callable[[], Any],  # Can be async or return awaitable
    threshold: float = 0.03,
    timeout: float = 5.0,
    interval: float = 0.1,
    stable_frames_required: int = 3,
    exclude_regions: list[tuple[int, int, int, int]] | None = None,
) -> bool:
    """Wait for animations to complete (async version).

    Args:
        take_screenshot: Async function that returns current screenshot as PIL Image.
        threshold: Pixel change threshold (0.0 to 1.0). Default 0.03 (3%).
        timeout: Maximum wait time in seconds.
        interval: Time between frame captures in seconds.
        stable_frames_required: Number of consecutive stable frames needed.
        exclude_regions: Optional regions to ignore (cursor area, etc.).

    Returns:
        True if animations completed, False if timeout.
    """
    start_time = time.time()
    stable_count = 0

    # Get first frame
    result = take_screenshot()
    if asyncio.iscoroutine(result):
        prev_frame = await result
    else:
        prev_frame = result

    while time.time() - start_time < timeout:
        await asyncio.sleep(interval)

        # Get current frame
        result = take_screenshot()
        if asyncio.iscoroutine(result):
            current_frame = await result
        else:
            current_frame = result

        diff = frame_diff_region(prev_frame, current_frame, exclude_regions=exclude_regions)

        if diff < threshold:
            stable_count += 1
            if stable_count >= stable_frames_required:
                return True
        else:
            stable_count = 0

        prev_frame = current_frame

    return False


class AnimationWatcher:
    """Watches for animation completion with detailed statistics."""

    def __init__(
        self,
        threshold: float = 0.03,
        stable_frames_required: int = 3,
        exclude_regions: list[tuple[int, int, int, int]] | None = None,
    ):
        """Initialize the animation watcher.

        Args:
            threshold: Pixel change threshold (0.0 to 1.0).
            stable_frames_required: Consecutive stable frames needed.
            exclude_regions: Regions to ignore in comparison.
        """
        self.threshold = threshold
        self.stable_frames_required = stable_frames_required
        self.exclude_regions = exclude_regions or []

        self._prev_frame: Image.Image | None = None
        self._stable_count = 0
        self._frame_count = 0
        self._diff_history: list[float] = []

    def reset(self) -> None:
        """Reset the watcher state."""
        self._prev_frame = None
        self._stable_count = 0
        self._frame_count = 0
        self._diff_history = []

    def check_frame(self, frame: Image.Image) -> bool:
        """Check a frame for animation stability.

        Args:
            frame: Current screenshot.

        Returns:
            True if animation is complete (enough stable frames).
        """
        self._frame_count += 1

        if self._prev_frame is None:
            self._prev_frame = frame
            return False

        diff = frame_diff_region(
            self._prev_frame, frame, exclude_regions=self.exclude_regions
        )
        self._diff_history.append(diff)

        if diff < self.threshold:
            self._stable_count += 1
        else:
            self._stable_count = 0

        self._prev_frame = frame

        return self._stable_count >= self.stable_frames_required

    @property
    def is_stable(self) -> bool:
        """Whether animation is currently stable."""
        return self._stable_count >= self.stable_frames_required

    @property
    def frames_checked(self) -> int:
        """Number of frames checked."""
        return self._frame_count

    @property
    def stable_frame_count(self) -> int:
        """Current count of consecutive stable frames."""
        return self._stable_count

    @property
    def average_diff(self) -> float:
        """Average pixel difference across all checked frames."""
        if not self._diff_history:
            return 0.0
        return sum(self._diff_history) / len(self._diff_history)

    @property
    def max_diff(self) -> float:
        """Maximum pixel difference observed."""
        if not self._diff_history:
            return 0.0
        return max(self._diff_history)

    def get_stats(self) -> dict[str, Any]:
        """Get detailed statistics about animation detection.

        Returns:
            Dict with frames_checked, stable_count, average_diff, max_diff, is_stable.
        """
        return {
            "frames_checked": self._frame_count,
            "stable_count": self._stable_count,
            "average_diff": self.average_diff,
            "max_diff": self.max_diff,
            "is_stable": self.is_stable,
            "threshold": self.threshold,
            "required_stable": self.stable_frames_required,
        }
