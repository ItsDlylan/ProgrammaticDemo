"""Smart demo recorder with automatic framing and animation detection.

This module provides a high-level recorder that wraps the base recorder with
intelligent features like auto-detection of page sections, optimal framing
calculations, animation waiting, and scroll self-correction.
"""

import asyncio
import io
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from programmatic_demo.recording.recorder import Recorder, get_recorder
from programmatic_demo.visual.animation_detector import (
    AnimationWatcher,
    wait_for_animation_complete,
    wait_for_animation_complete_sync,
)
from programmatic_demo.visual.auto_scroll import AsyncAutoScroller, AutoScroller, ScrollResult
from programmatic_demo.visual.base import FramingRule, Section, Viewport, Waypoint
from programmatic_demo.visual.framing_rules import get_rule_for_section_type
from programmatic_demo.visual.section_detector import AsyncSectionDetector, SectionDetector
from programmatic_demo.visual.waypoint_generator import (
    AsyncWaypointGenerator,
    WaypointGenerator,
    estimate_pause_duration,
    estimate_scroll_duration,
)

logger = logging.getLogger(__name__)


@dataclass
class RecordingConfig:
    """Configuration for smart recording.

    Attributes:
        output_path: Path to save the recording.
        fps: Frames per second for recording.
        animation_threshold: Pixel change threshold for animation detection.
        animation_timeout: Max wait time for animations (seconds).
        min_section_height: Minimum section height to include (pixels).
        include_return_to_top: Whether to return to top at end.
        pause_multiplier: Multiplier for pause durations.
        scroll_duration_multiplier: Multiplier for scroll durations.
        verify_framing: Whether to verify framing after scrolling.
        max_framing_retries: Max attempts to correct framing.
    """

    output_path: str = "demo.mp4"
    fps: int = 30
    animation_threshold: float = 0.03
    animation_timeout: float = 5.0
    min_section_height: float = 200
    include_return_to_top: bool = True
    pause_multiplier: float = 1.0
    scroll_duration_multiplier: float = 1.0
    verify_framing: bool = True
    max_framing_retries: int = 3


@dataclass
class WaypointOverride:
    """Manual override for a specific waypoint.

    Attributes:
        name: Waypoint name to override (or new waypoint name).
        position: Optional override for scroll position.
        pause: Optional override for pause duration.
        scroll_duration: Optional override for scroll duration.
        skip: If True, skip this waypoint entirely.
        insert_before: If set, insert as new waypoint before named waypoint.
        insert_after: If set, insert as new waypoint after named waypoint.
    """

    name: str
    position: float | None = None
    pause: float | None = None
    scroll_duration: float | None = None
    skip: bool = False
    insert_before: str | None = None
    insert_after: str | None = None


@dataclass
class RecordingProgress:
    """Progress information for callbacks.

    Attributes:
        current_waypoint: Index of current waypoint (0-based).
        total_waypoints: Total number of waypoints.
        waypoint_name: Name of current waypoint.
        phase: Current phase (detecting, scrolling, waiting, recording).
        elapsed_time: Time since recording started (seconds).
        message: Human-readable progress message.
    """

    current_waypoint: int
    total_waypoints: int
    waypoint_name: str
    phase: str
    elapsed_time: float
    message: str


@dataclass
class RecordingResult:
    """Result of a smart recording session.

    Attributes:
        success: Whether recording completed successfully.
        output_path: Path to the output file.
        duration: Total recording duration (seconds).
        waypoints_visited: Number of waypoints successfully visited.
        sections_detected: Number of sections auto-detected.
        framing_corrections: Number of framing corrections made.
        animation_waits: Number of animation waits performed.
        errors: List of error messages if any.
    """

    success: bool
    output_path: str | None
    duration: float
    waypoints_visited: int
    sections_detected: int
    framing_corrections: int
    animation_waits: int
    errors: list[str] = field(default_factory=list)


ProgressCallback = Callable[[RecordingProgress], None]


class SmartDemoRecorder:
    """Smart demo recorder with automatic framing and animation detection.

    This recorder wraps the basic ffmpeg recorder and adds intelligent
    features for producing high-quality demo recordings:

    - Auto-detects page sections on navigation
    - Calculates optimal waypoints with proper framing
    - Waits for animations to complete before recording
    - Self-corrects scroll positions using verification loop
    - Supports manual overrides for specific waypoints
    """

    def __init__(
        self,
        page: Any,
        config: RecordingConfig | None = None,
        recorder: Recorder | None = None,
    ) -> None:
        """Initialize the smart recorder.

        Args:
            page: Playwright page object (sync).
            config: Recording configuration.
            recorder: Optional custom recorder instance.
        """
        self._page = page
        self._config = config or RecordingConfig()
        self._recorder = recorder or get_recorder()

        # Components
        self._section_detector = SectionDetector(page)
        self._waypoint_generator = WaypointGenerator(
            page,
            viewport_height=self._get_viewport_height(),
        )
        self._auto_scroller = AutoScroller(page)

        # State
        self._waypoints: list[Waypoint] = []
        self._overrides: list[WaypointOverride] = []
        self._sections: list[Section] = []
        self._progress_callback: ProgressCallback | None = None
        self._start_time: float = 0
        self._framing_corrections = 0
        self._animation_waits = 0
        self._is_recording = False

    def _get_viewport_height(self) -> int:
        """Get current viewport height."""
        viewport_size = self._page.viewport_size
        if viewport_size:
            return viewport_size["height"]
        return 800

    def _take_screenshot(self) -> Image.Image:
        """Take a screenshot of the current page."""
        screenshot_bytes = self._page.screenshot()
        return Image.open(io.BytesIO(screenshot_bytes))

    def _report_progress(
        self,
        waypoint_idx: int,
        waypoint_name: str,
        phase: str,
        message: str,
    ) -> None:
        """Report progress to callback if set."""
        if self._progress_callback is None:
            return

        elapsed = time.time() - self._start_time if self._start_time else 0

        progress = RecordingProgress(
            current_waypoint=waypoint_idx,
            total_waypoints=len(self._waypoints),
            waypoint_name=waypoint_name,
            phase=phase,
            elapsed_time=elapsed,
            message=message,
        )

        self._progress_callback(progress)

    def set_progress_callback(self, callback: ProgressCallback) -> None:
        """Set callback for progress updates.

        Args:
            callback: Function to call with progress updates.
        """
        self._progress_callback = callback

    def add_override(self, override: WaypointOverride) -> None:
        """Add a manual override for a waypoint.

        Args:
            override: Override specification.
        """
        self._overrides.append(override)

    def clear_overrides(self) -> None:
        """Clear all manual overrides."""
        self._overrides.clear()

    def detect_sections(self) -> list[Section]:
        """Detect all sections on the current page.

        Returns:
            List of detected sections.
        """
        self._sections = self._section_detector.find_sections()
        logger.info(f"Detected {len(self._sections)} sections")
        return self._sections

    def generate_waypoints(self) -> list[Waypoint]:
        """Generate waypoints from detected sections.

        Returns:
            List of waypoints with optional overrides applied.
        """
        # Generate base waypoints
        self._waypoints = self._waypoint_generator.generate_waypoints(
            include_return_to_top=self._config.include_return_to_top,
            min_section_height=self._config.min_section_height,
        )

        # Apply multipliers
        for wp in self._waypoints:
            wp.pause *= self._config.pause_multiplier
            wp.scroll_duration *= self._config.scroll_duration_multiplier

        # Apply overrides
        self._apply_overrides()

        logger.info(f"Generated {len(self._waypoints)} waypoints")
        return self._waypoints

    def _apply_overrides(self) -> None:
        """Apply manual overrides to waypoints."""
        if not self._overrides:
            return

        # Build lookup
        waypoint_map = {wp.name: wp for wp in self._waypoints}
        waypoint_indices = {wp.name: i for i, wp in enumerate(self._waypoints)}

        # Track insertions
        insertions: list[tuple[int, Waypoint]] = []

        for override in self._overrides:
            if override.name in waypoint_map:
                # Existing waypoint override
                wp = waypoint_map[override.name]
                idx = waypoint_indices[override.name]

                if override.skip:
                    # Mark for removal
                    self._waypoints[idx] = None  # type: ignore
                    continue

                if override.position is not None:
                    wp.position = override.position
                if override.pause is not None:
                    wp.pause = override.pause
                if override.scroll_duration is not None:
                    wp.scroll_duration = override.scroll_duration

            elif override.insert_before or override.insert_after:
                # New waypoint insertion
                target_name = override.insert_before or override.insert_after
                if target_name not in waypoint_indices:
                    logger.warning(
                        f"Cannot insert waypoint '{override.name}': "
                        f"target '{target_name}' not found"
                    )
                    continue

                target_idx = waypoint_indices[target_name]
                insert_idx = target_idx if override.insert_before else target_idx + 1

                new_wp = Waypoint(
                    name=override.name,
                    position=override.position or 0,
                    pause=override.pause or 2.0,
                    scroll_duration=override.scroll_duration or 1.5,
                    description=f"Manual waypoint: {override.name}",
                )
                insertions.append((insert_idx, new_wp))

        # Remove skipped waypoints
        self._waypoints = [wp for wp in self._waypoints if wp is not None]

        # Apply insertions (in reverse order to maintain indices)
        insertions.sort(key=lambda x: x[0], reverse=True)
        for insert_idx, new_wp in insertions:
            self._waypoints.insert(insert_idx, new_wp)

    def get_waypoints(self) -> list[Waypoint]:
        """Get current waypoints list.

        Returns:
            Current list of waypoints.
        """
        return self._waypoints.copy()

    def set_waypoints(self, waypoints: list[Waypoint]) -> None:
        """Set waypoints directly (for preview/adjustment workflows).

        Args:
            waypoints: List of waypoints to use.
        """
        self._waypoints = waypoints

    def _wait_for_animation(self) -> bool:
        """Wait for page animations to complete.

        Returns:
            True if animations completed, False if timeout.
        """
        self._animation_waits += 1

        result = wait_for_animation_complete_sync(
            take_screenshot=self._take_screenshot,
            threshold=self._config.animation_threshold,
            timeout=self._config.animation_timeout,
        )

        return result

    def _scroll_to_waypoint(self, waypoint: Waypoint) -> ScrollResult:
        """Scroll to a waypoint with verification.

        Args:
            waypoint: Target waypoint.

        Returns:
            ScrollResult with success status.
        """
        if waypoint.framing_rule:
            # Use framing rule for precise positioning
            result = self._auto_scroller.scroll_to_frame(
                element_bounds=waypoint.framing_rule,  # This should be bounds
                rule=waypoint.framing_rule,
                smooth=True,
            )
        else:
            # Direct scroll to position
            self._auto_scroller.smooth_scroll_to(
                waypoint.position,
                duration=waypoint.scroll_duration,
            )
            result = ScrollResult(
                success=True,
                final_position=waypoint.position,
                iterations=0,
                adjustments=[],
            )

        return result

    def _scroll_to_position(self, position: float, duration: float) -> None:
        """Scroll to a specific position.

        Args:
            position: Target scroll Y position.
            duration: Scroll animation duration.
        """
        self._auto_scroller.smooth_scroll_to(position, duration=duration)

    def record(self) -> RecordingResult:
        """Execute a full recording session.

        Auto-detects sections, generates waypoints, and records the demo
        while scrolling through each waypoint.

        Returns:
            RecordingResult with success status and statistics.
        """
        errors: list[str] = []
        self._start_time = time.time()
        self._framing_corrections = 0
        self._animation_waits = 0

        # Phase 1: Detect sections
        self._report_progress(0, "", "detecting", "Detecting page sections...")
        try:
            self.detect_sections()
        except Exception as e:
            errors.append(f"Section detection failed: {e}")
            logger.error(f"Section detection error: {e}")

        # Phase 2: Generate waypoints
        self._report_progress(0, "", "detecting", "Generating waypoints...")
        try:
            self.generate_waypoints()
        except Exception as e:
            errors.append(f"Waypoint generation failed: {e}")
            logger.error(f"Waypoint generation error: {e}")
            return RecordingResult(
                success=False,
                output_path=None,
                duration=0,
                waypoints_visited=0,
                sections_detected=len(self._sections),
                framing_corrections=0,
                animation_waits=0,
                errors=errors,
            )

        if not self._waypoints:
            errors.append("No waypoints generated")
            return RecordingResult(
                success=False,
                output_path=None,
                duration=0,
                waypoints_visited=0,
                sections_detected=len(self._sections),
                framing_corrections=0,
                animation_waits=0,
                errors=errors,
            )

        # Phase 3: Start recording
        self._report_progress(0, "", "recording", "Starting recording...")
        start_result = self._recorder.start(
            output_path=self._config.output_path,
            fps=self._config.fps,
        )

        if start_result.get("status") == "error":
            errors.append(f"Recording start failed: {start_result.get('message')}")
            return RecordingResult(
                success=False,
                output_path=None,
                duration=0,
                waypoints_visited=0,
                sections_detected=len(self._sections),
                framing_corrections=0,
                animation_waits=0,
                errors=errors,
            )

        self._is_recording = True
        waypoints_visited = 0

        try:
            # Phase 4: Visit each waypoint
            for idx, waypoint in enumerate(self._waypoints):
                self._report_progress(
                    idx,
                    waypoint.name,
                    "scrolling",
                    f"Scrolling to {waypoint.name}...",
                )

                # Scroll to waypoint
                self._scroll_to_position(waypoint.position, waypoint.scroll_duration)

                # Wait for scroll animation to complete
                time.sleep(waypoint.scroll_duration + 0.1)

                # Wait for page animations
                self._report_progress(
                    idx,
                    waypoint.name,
                    "waiting",
                    f"Waiting for animations at {waypoint.name}...",
                )
                self._wait_for_animation()

                # Verify framing if enabled
                if self._config.verify_framing and waypoint.framing_rule:
                    self._verify_and_correct_framing(waypoint)

                # Pause at waypoint
                self._report_progress(
                    idx,
                    waypoint.name,
                    "recording",
                    f"Recording {waypoint.name} for {waypoint.pause:.1f}s...",
                )
                time.sleep(waypoint.pause)

                waypoints_visited += 1

        except Exception as e:
            errors.append(f"Recording error: {e}")
            logger.error(f"Recording error: {e}")

        finally:
            # Phase 5: Stop recording
            self._report_progress(
                len(self._waypoints),
                "",
                "recording",
                "Stopping recording...",
            )
            stop_result = self._recorder.stop()
            self._is_recording = False

        duration = time.time() - self._start_time

        success = (
            stop_result.get("status") != "error"
            and waypoints_visited == len(self._waypoints)
            and not errors
        )

        return RecordingResult(
            success=success,
            output_path=self._config.output_path if success else None,
            duration=duration,
            waypoints_visited=waypoints_visited,
            sections_detected=len(self._sections),
            framing_corrections=self._framing_corrections,
            animation_waits=self._animation_waits,
            errors=errors,
        )

    def _verify_and_correct_framing(self, waypoint: Waypoint) -> None:
        """Verify and correct framing for a waypoint.

        Args:
            waypoint: Waypoint to verify.
        """
        if waypoint.framing_rule is None:
            return

        # Get current scroll position
        current_scroll = self._page.evaluate("window.scrollY")

        # Check if we're within tolerance
        position_diff = abs(current_scroll - waypoint.position)
        tolerance = waypoint.framing_rule.tolerance

        if position_diff > tolerance:
            # Attempt correction
            for attempt in range(self._config.max_framing_retries):
                self._framing_corrections += 1
                logger.debug(
                    f"Framing correction attempt {attempt + 1} for {waypoint.name}: "
                    f"current={current_scroll:.0f}, target={waypoint.position:.0f}"
                )

                # Small adjustment scroll
                self._auto_scroller.smooth_scroll_to(waypoint.position, duration=0.3)
                time.sleep(0.4)

                # Re-check
                current_scroll = self._page.evaluate("window.scrollY")
                position_diff = abs(current_scroll - waypoint.position)

                if position_diff <= tolerance:
                    break

    def stop(self) -> dict[str, Any]:
        """Stop recording if in progress.

        Returns:
            Stop result from recorder.
        """
        if self._is_recording:
            self._is_recording = False
            return self._recorder.stop()
        return {"status": "success", "message": "Not recording"}

    def get_status(self) -> dict[str, Any]:
        """Get current recording status.

        Returns:
            Status dict with recording state.
        """
        return self._recorder.get_status()


class AsyncSmartDemoRecorder:
    """Async version of SmartDemoRecorder."""

    def __init__(
        self,
        page: Any,
        config: RecordingConfig | None = None,
        recorder: Recorder | None = None,
    ) -> None:
        """Initialize the async smart recorder.

        Args:
            page: Async Playwright page object.
            config: Recording configuration.
            recorder: Optional custom recorder instance.
        """
        self._page = page
        self._config = config or RecordingConfig()
        self._recorder = recorder or get_recorder()

        # State
        self._waypoints: list[Waypoint] = []
        self._overrides: list[WaypointOverride] = []
        self._sections: list[Section] = []
        self._progress_callback: ProgressCallback | None = None
        self._start_time: float = 0
        self._framing_corrections = 0
        self._animation_waits = 0
        self._is_recording = False

    async def _get_viewport_height(self) -> int:
        """Get current viewport height."""
        viewport_size = self._page.viewport_size
        if viewport_size:
            return viewport_size["height"]
        return 800

    async def _take_screenshot(self) -> Image.Image:
        """Take a screenshot of the current page."""
        screenshot_bytes = await self._page.screenshot()
        return Image.open(io.BytesIO(screenshot_bytes))

    def _report_progress(
        self,
        waypoint_idx: int,
        waypoint_name: str,
        phase: str,
        message: str,
    ) -> None:
        """Report progress to callback if set."""
        if self._progress_callback is None:
            return

        elapsed = time.time() - self._start_time if self._start_time else 0

        progress = RecordingProgress(
            current_waypoint=waypoint_idx,
            total_waypoints=len(self._waypoints),
            waypoint_name=waypoint_name,
            phase=phase,
            elapsed_time=elapsed,
            message=message,
        )

        self._progress_callback(progress)

    def set_progress_callback(self, callback: ProgressCallback) -> None:
        """Set callback for progress updates."""
        self._progress_callback = callback

    def add_override(self, override: WaypointOverride) -> None:
        """Add a manual override for a waypoint."""
        self._overrides.append(override)

    def clear_overrides(self) -> None:
        """Clear all manual overrides."""
        self._overrides.clear()

    async def detect_sections(self) -> list[Section]:
        """Detect all sections on the current page."""
        viewport_height = await self._get_viewport_height()
        detector = AsyncSectionDetector(self._page)
        self._sections = await detector.find_sections()
        logger.info(f"Detected {len(self._sections)} sections")
        return self._sections

    async def generate_waypoints(self) -> list[Waypoint]:
        """Generate waypoints from detected sections."""
        viewport_height = await self._get_viewport_height()
        generator = AsyncWaypointGenerator(
            self._page,
            viewport_height=viewport_height,
        )

        self._waypoints = await generator.generate_waypoints(
            include_return_to_top=self._config.include_return_to_top,
            min_section_height=self._config.min_section_height,
        )

        # Apply multipliers
        for wp in self._waypoints:
            wp.pause *= self._config.pause_multiplier
            wp.scroll_duration *= self._config.scroll_duration_multiplier

        # Apply overrides
        self._apply_overrides()

        logger.info(f"Generated {len(self._waypoints)} waypoints")
        return self._waypoints

    def _apply_overrides(self) -> None:
        """Apply manual overrides to waypoints."""
        if not self._overrides:
            return

        waypoint_map = {wp.name: wp for wp in self._waypoints}
        waypoint_indices = {wp.name: i for i, wp in enumerate(self._waypoints)}

        insertions: list[tuple[int, Waypoint]] = []

        for override in self._overrides:
            if override.name in waypoint_map:
                wp = waypoint_map[override.name]
                idx = waypoint_indices[override.name]

                if override.skip:
                    self._waypoints[idx] = None  # type: ignore
                    continue

                if override.position is not None:
                    wp.position = override.position
                if override.pause is not None:
                    wp.pause = override.pause
                if override.scroll_duration is not None:
                    wp.scroll_duration = override.scroll_duration

            elif override.insert_before or override.insert_after:
                target_name = override.insert_before or override.insert_after
                if target_name not in waypoint_indices:
                    logger.warning(
                        f"Cannot insert waypoint '{override.name}': "
                        f"target '{target_name}' not found"
                    )
                    continue

                target_idx = waypoint_indices[target_name]
                insert_idx = target_idx if override.insert_before else target_idx + 1

                new_wp = Waypoint(
                    name=override.name,
                    position=override.position or 0,
                    pause=override.pause or 2.0,
                    scroll_duration=override.scroll_duration or 1.5,
                    description=f"Manual waypoint: {override.name}",
                )
                insertions.append((insert_idx, new_wp))

        self._waypoints = [wp for wp in self._waypoints if wp is not None]

        insertions.sort(key=lambda x: x[0], reverse=True)
        for insert_idx, new_wp in insertions:
            self._waypoints.insert(insert_idx, new_wp)

    def get_waypoints(self) -> list[Waypoint]:
        """Get current waypoints list."""
        return self._waypoints.copy()

    def set_waypoints(self, waypoints: list[Waypoint]) -> None:
        """Set waypoints directly."""
        self._waypoints = waypoints

    async def _wait_for_animation(self) -> bool:
        """Wait for page animations to complete."""
        self._animation_waits += 1

        result = await wait_for_animation_complete(
            take_screenshot=self._take_screenshot,
            threshold=self._config.animation_threshold,
            timeout=self._config.animation_timeout,
        )

        return result

    async def _scroll_to_position(self, position: float, duration: float) -> None:
        """Scroll to a specific position."""
        scroller = AsyncAutoScroller(self._page)
        await scroller.smooth_scroll_to(position, duration=duration)

    async def record(self) -> RecordingResult:
        """Execute a full async recording session."""
        errors: list[str] = []
        self._start_time = time.time()
        self._framing_corrections = 0
        self._animation_waits = 0

        # Phase 1: Detect sections
        self._report_progress(0, "", "detecting", "Detecting page sections...")
        try:
            await self.detect_sections()
        except Exception as e:
            errors.append(f"Section detection failed: {e}")
            logger.error(f"Section detection error: {e}")

        # Phase 2: Generate waypoints
        self._report_progress(0, "", "detecting", "Generating waypoints...")
        try:
            await self.generate_waypoints()
        except Exception as e:
            errors.append(f"Waypoint generation failed: {e}")
            logger.error(f"Waypoint generation error: {e}")
            return RecordingResult(
                success=False,
                output_path=None,
                duration=0,
                waypoints_visited=0,
                sections_detected=len(self._sections),
                framing_corrections=0,
                animation_waits=0,
                errors=errors,
            )

        if not self._waypoints:
            errors.append("No waypoints generated")
            return RecordingResult(
                success=False,
                output_path=None,
                duration=0,
                waypoints_visited=0,
                sections_detected=len(self._sections),
                framing_corrections=0,
                animation_waits=0,
                errors=errors,
            )

        # Phase 3: Start recording
        self._report_progress(0, "", "recording", "Starting recording...")
        start_result = self._recorder.start(
            output_path=self._config.output_path,
            fps=self._config.fps,
        )

        if start_result.get("status") == "error":
            errors.append(f"Recording start failed: {start_result.get('message')}")
            return RecordingResult(
                success=False,
                output_path=None,
                duration=0,
                waypoints_visited=0,
                sections_detected=len(self._sections),
                framing_corrections=0,
                animation_waits=0,
                errors=errors,
            )

        self._is_recording = True
        waypoints_visited = 0

        try:
            # Phase 4: Visit each waypoint
            for idx, waypoint in enumerate(self._waypoints):
                self._report_progress(
                    idx,
                    waypoint.name,
                    "scrolling",
                    f"Scrolling to {waypoint.name}...",
                )

                # Scroll to waypoint
                await self._scroll_to_position(waypoint.position, waypoint.scroll_duration)

                # Wait for scroll animation
                await asyncio.sleep(waypoint.scroll_duration + 0.1)

                # Wait for page animations
                self._report_progress(
                    idx,
                    waypoint.name,
                    "waiting",
                    f"Waiting for animations at {waypoint.name}...",
                )
                await self._wait_for_animation()

                # Verify framing if enabled
                if self._config.verify_framing and waypoint.framing_rule:
                    await self._verify_and_correct_framing(waypoint)

                # Pause at waypoint
                self._report_progress(
                    idx,
                    waypoint.name,
                    "recording",
                    f"Recording {waypoint.name} for {waypoint.pause:.1f}s...",
                )
                await asyncio.sleep(waypoint.pause)

                waypoints_visited += 1

        except Exception as e:
            errors.append(f"Recording error: {e}")
            logger.error(f"Recording error: {e}")

        finally:
            # Phase 5: Stop recording
            self._report_progress(
                len(self._waypoints),
                "",
                "recording",
                "Stopping recording...",
            )
            stop_result = self._recorder.stop()
            self._is_recording = False

        duration = time.time() - self._start_time

        success = (
            stop_result.get("status") != "error"
            and waypoints_visited == len(self._waypoints)
            and not errors
        )

        return RecordingResult(
            success=success,
            output_path=self._config.output_path if success else None,
            duration=duration,
            waypoints_visited=waypoints_visited,
            sections_detected=len(self._sections),
            framing_corrections=self._framing_corrections,
            animation_waits=self._animation_waits,
            errors=errors,
        )

    async def _verify_and_correct_framing(self, waypoint: Waypoint) -> None:
        """Verify and correct framing for a waypoint."""
        if waypoint.framing_rule is None:
            return

        current_scroll = await self._page.evaluate("window.scrollY")
        position_diff = abs(current_scroll - waypoint.position)
        tolerance = waypoint.framing_rule.tolerance

        if position_diff > tolerance:
            scroller = AsyncAutoScroller(self._page)
            for attempt in range(self._config.max_framing_retries):
                self._framing_corrections += 1
                logger.debug(
                    f"Framing correction attempt {attempt + 1} for {waypoint.name}: "
                    f"current={current_scroll:.0f}, target={waypoint.position:.0f}"
                )

                await scroller.smooth_scroll_to(waypoint.position, duration=0.3)
                await asyncio.sleep(0.4)

                current_scroll = await self._page.evaluate("window.scrollY")
                position_diff = abs(current_scroll - waypoint.position)

                if position_diff <= tolerance:
                    break

    def stop(self) -> dict[str, Any]:
        """Stop recording if in progress."""
        if self._is_recording:
            self._is_recording = False
            return self._recorder.stop()
        return {"status": "success", "message": "Not recording"}

    def get_status(self) -> dict[str, Any]:
        """Get current recording status."""
        return self._recorder.get_status()
