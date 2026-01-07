"""Preview mode for waypoint inspection and adjustment.

This module provides functionality to preview generated waypoints before
recording, allowing for inspection and fine-tuning of scroll positions.
"""

import asyncio
import io
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from programmatic_demo.visual.base import FramingAlignment, Waypoint
from programmatic_demo.visual.auto_scroll import AsyncAutoScroller, AutoScroller

logger = logging.getLogger(__name__)


@dataclass
class WaypointPreview:
    """Preview data for a single waypoint.

    Attributes:
        waypoint: The waypoint being previewed.
        index: Index in the waypoint list.
        screenshot_path: Path to preview screenshot if saved.
        screenshot: In-memory screenshot if captured.
        actual_position: Actual scroll position achieved.
        position_diff: Difference between target and actual position.
        approved: Whether this waypoint has been approved.
        adjustment: Manual adjustment applied (pixels).
    """

    waypoint: Waypoint
    index: int
    screenshot_path: str | None = None
    screenshot: Image.Image | None = None
    actual_position: float = 0
    position_diff: float = 0
    approved: bool = False
    adjustment: float = 0


@dataclass
class PreviewReport:
    """Report generated from preview session.

    Attributes:
        waypoints: List of waypoint previews.
        total_scroll_distance: Total distance scrolled in preview.
        estimated_duration: Estimated recording duration (seconds).
        screenshot_dir: Directory where screenshots were saved.
        adjustments_made: Number of manual adjustments made.
        all_approved: Whether all waypoints were approved.
    """

    waypoints: list[WaypointPreview]
    total_scroll_distance: float
    estimated_duration: float
    screenshot_dir: str | None
    adjustments_made: int
    all_approved: bool


@dataclass
class PreviewConfig:
    """Configuration for preview mode.

    Attributes:
        scroll_duration: Duration for preview scrolls (seconds).
        pause_duration: Pause at each waypoint (seconds).
        capture_screenshots: Whether to capture screenshots.
        screenshot_dir: Directory to save screenshots.
        screenshot_format: Image format (png or jpeg).
        adjustment_step: Pixels to adjust per key press.
        large_adjustment_step: Pixels for large adjustments.
    """

    scroll_duration: float = 0.5
    pause_duration: float = 1.0
    capture_screenshots: bool = True
    screenshot_dir: str = "preview_screenshots"
    screenshot_format: str = "png"
    adjustment_step: float = 10
    large_adjustment_step: float = 50


# Type for interactive adjustment callback
AdjustmentCallback = Callable[[WaypointPreview, str], float | None]


class WaypointPreviewer:
    """Preview waypoints on a page with optional adjustments."""

    def __init__(
        self,
        page: Any,
        config: PreviewConfig | None = None,
    ) -> None:
        """Initialize the previewer.

        Args:
            page: Playwright page object (sync).
            config: Preview configuration.
        """
        self._page = page
        self._config = config or PreviewConfig()
        self._scroller = AutoScroller(page)
        self._previews: list[WaypointPreview] = []
        self._current_index = 0
        self._adjustment_callback: AdjustmentCallback | None = None

    def set_adjustment_callback(self, callback: AdjustmentCallback) -> None:
        """Set callback for interactive adjustments.

        The callback receives (preview, action) and returns adjustment in pixels
        or None to stop adjusting this waypoint.

        Args:
            callback: Adjustment callback function.
        """
        self._adjustment_callback = callback

    def _take_screenshot(self) -> Image.Image:
        """Take a screenshot of the current page."""
        screenshot_bytes = self._page.screenshot()
        return Image.open(io.BytesIO(screenshot_bytes))

    def _save_screenshot(
        self,
        screenshot: Image.Image,
        waypoint_name: str,
        index: int,
    ) -> str:
        """Save a screenshot to disk.

        Args:
            screenshot: Image to save.
            waypoint_name: Name of the waypoint.
            index: Waypoint index.

        Returns:
            Path to saved screenshot.
        """
        screenshot_dir = Path(self._config.screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Clean filename
        clean_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in waypoint_name)
        filename = f"{index:02d}_{clean_name}.{self._config.screenshot_format}"
        filepath = screenshot_dir / filename

        screenshot.save(filepath)
        return str(filepath)

    def _scroll_to(self, position: float) -> float:
        """Scroll to a position and return actual position.

        Args:
            position: Target scroll position.

        Returns:
            Actual scroll position achieved.
        """
        self._scroller.smooth_scroll_to(position, duration=self._config.scroll_duration)
        time.sleep(self._config.scroll_duration + 0.1)

        # Get actual position
        return self._page.evaluate("window.scrollY")

    def preview_waypoint(
        self,
        waypoint: Waypoint,
        index: int,
        capture: bool = True,
    ) -> WaypointPreview:
        """Preview a single waypoint.

        Args:
            waypoint: Waypoint to preview.
            index: Waypoint index.
            capture: Whether to capture screenshot.

        Returns:
            WaypointPreview with results.
        """
        # Scroll to waypoint
        actual_position = self._scroll_to(waypoint.position)
        position_diff = actual_position - waypoint.position

        # Create preview
        preview = WaypointPreview(
            waypoint=waypoint,
            index=index,
            actual_position=actual_position,
            position_diff=position_diff,
        )

        # Capture screenshot if requested
        if capture and self._config.capture_screenshots:
            screenshot = self._take_screenshot()
            preview.screenshot = screenshot
            preview.screenshot_path = self._save_screenshot(
                screenshot, waypoint.name, index
            )

        # Pause for viewing
        time.sleep(self._config.pause_duration)

        return preview

    def preview_all(
        self,
        waypoints: list[Waypoint],
        interactive: bool = False,
    ) -> list[WaypointPreview]:
        """Preview all waypoints.

        Args:
            waypoints: List of waypoints to preview.
            interactive: Whether to allow interactive adjustments.

        Returns:
            List of WaypointPreview objects.
        """
        self._previews = []
        prev_position = 0

        for index, waypoint in enumerate(waypoints):
            preview = self.preview_waypoint(waypoint, index)
            self._previews.append(preview)

            # Interactive adjustment
            if interactive and self._adjustment_callback:
                self._interactive_adjust(preview)

            prev_position = waypoint.position

        return self._previews

    def _interactive_adjust(self, preview: WaypointPreview) -> None:
        """Handle interactive adjustment for a waypoint.

        Args:
            preview: WaypointPreview to adjust.
        """
        if self._adjustment_callback is None:
            return

        total_adjustment = 0

        while True:
            # Get adjustment from callback
            adjustment = self._adjustment_callback(preview, "adjust")

            if adjustment is None:
                # Done adjusting this waypoint
                preview.approved = True
                break

            total_adjustment += adjustment
            preview.adjustment = total_adjustment

            # Apply adjustment
            new_position = preview.waypoint.position + total_adjustment
            actual = self._scroll_to(new_position)

            # Update preview
            preview.actual_position = actual
            preview.position_diff = actual - new_position

            # Recapture screenshot if enabled
            if self._config.capture_screenshots:
                screenshot = self._take_screenshot()
                preview.screenshot = screenshot
                if preview.screenshot_path:
                    screenshot.save(preview.screenshot_path)

    def apply_adjustments(
        self,
        waypoints: list[Waypoint],
    ) -> list[Waypoint]:
        """Apply preview adjustments to waypoints.

        Args:
            waypoints: Original waypoint list.

        Returns:
            New waypoint list with adjustments applied.
        """
        if not self._previews:
            return waypoints

        result = []
        preview_map = {p.index: p for p in self._previews}

        for i, wp in enumerate(waypoints):
            if i in preview_map and preview_map[i].adjustment != 0:
                # Create adjusted waypoint
                new_wp = Waypoint(
                    name=wp.name,
                    position=wp.position + preview_map[i].adjustment,
                    pause=wp.pause,
                    scroll_duration=wp.scroll_duration,
                    description=wp.description,
                    framing_rule=wp.framing_rule,
                )
                result.append(new_wp)
            else:
                result.append(wp)

        return result

    def generate_report(self, waypoints: list[Waypoint]) -> PreviewReport:
        """Generate a preview report.

        Args:
            waypoints: Original waypoints (for reference).

        Returns:
            PreviewReport with summary.
        """
        total_distance = 0
        estimated_duration = 0
        adjustments_made = 0
        all_approved = True

        prev_position = 0
        for preview in self._previews:
            wp = preview.waypoint

            # Calculate scroll distance
            distance = abs(wp.position - prev_position)
            total_distance += distance

            # Estimate duration (scroll + pause)
            estimated_duration += wp.scroll_duration + wp.pause

            # Count adjustments
            if preview.adjustment != 0:
                adjustments_made += 1

            # Check approval
            if not preview.approved:
                all_approved = False

            prev_position = wp.position

        return PreviewReport(
            waypoints=self._previews,
            total_scroll_distance=total_distance,
            estimated_duration=estimated_duration,
            screenshot_dir=self._config.screenshot_dir if self._config.capture_screenshots else None,
            adjustments_made=adjustments_made,
            all_approved=all_approved,
        )

    def export_report_json(
        self,
        report: PreviewReport,
        filepath: str,
    ) -> None:
        """Export preview report to JSON.

        Args:
            report: Report to export.
            filepath: Output file path.
        """
        data = {
            "total_scroll_distance": report.total_scroll_distance,
            "estimated_duration": report.estimated_duration,
            "screenshot_dir": report.screenshot_dir,
            "adjustments_made": report.adjustments_made,
            "all_approved": report.all_approved,
            "waypoints": [
                {
                    "index": p.index,
                    "name": p.waypoint.name,
                    "target_position": p.waypoint.position,
                    "actual_position": p.actual_position,
                    "position_diff": p.position_diff,
                    "pause": p.waypoint.pause,
                    "scroll_duration": p.waypoint.scroll_duration,
                    "description": p.waypoint.description,
                    "framing_rule": (
                        p.waypoint.framing_rule.alignment.value
                        if p.waypoint.framing_rule
                        else None
                    ),
                    "screenshot_path": p.screenshot_path,
                    "approved": p.approved,
                    "adjustment": p.adjustment,
                }
                for p in report.waypoints
            ],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def export_report_html(
        self,
        report: PreviewReport,
        filepath: str,
    ) -> None:
        """Export preview report to HTML.

        Args:
            report: Report to export.
            filepath: Output file path.
        """
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<title>Waypoint Preview Report</title>",
            "<style>",
            "body { font-family: sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }",
            "h1 { color: #333; }",
            ".summary { background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }",
            ".waypoint { border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 5px; }",
            ".waypoint.approved { border-left: 4px solid #4CAF50; }",
            ".waypoint.adjusted { border-left: 4px solid #FF9800; }",
            ".screenshot { max-width: 100%; height: auto; margin-top: 10px; }",
            ".details { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }",
            ".detail { background: #f9f9f9; padding: 8px; border-radius: 3px; }",
            ".label { font-weight: bold; color: #666; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>Waypoint Preview Report</h1>",
            "<div class='summary'>",
            f"<p><strong>Total Scroll Distance:</strong> {report.total_scroll_distance:.0f}px</p>",
            f"<p><strong>Estimated Duration:</strong> {report.estimated_duration:.1f}s</p>",
            f"<p><strong>Adjustments Made:</strong> {report.adjustments_made}</p>",
            f"<p><strong>All Approved:</strong> {'Yes' if report.all_approved else 'No'}</p>",
            "</div>",
        ]

        for preview in report.waypoints:
            wp = preview.waypoint
            classes = ["waypoint"]
            if preview.approved:
                classes.append("approved")
            if preview.adjustment != 0:
                classes.append("adjusted")

            html_parts.extend([
                f"<div class='{' '.join(classes)}'>",
                f"<h3>{preview.index + 1}. {wp.name}</h3>",
                f"<p>{wp.description}</p>",
                "<div class='details'>",
                f"<div class='detail'><span class='label'>Target Position:</span> {wp.position:.0f}px</div>",
                f"<div class='detail'><span class='label'>Actual Position:</span> {preview.actual_position:.0f}px</div>",
                f"<div class='detail'><span class='label'>Pause:</span> {wp.pause:.1f}s</div>",
                f"<div class='detail'><span class='label'>Scroll Duration:</span> {wp.scroll_duration:.1f}s</div>",
            ])

            if wp.framing_rule:
                html_parts.append(
                    f"<div class='detail'><span class='label'>Framing:</span> {wp.framing_rule.alignment.value}</div>"
                )

            if preview.adjustment != 0:
                html_parts.append(
                    f"<div class='detail'><span class='label'>Adjustment:</span> {preview.adjustment:+.0f}px</div>"
                )

            html_parts.append("</div>")

            if preview.screenshot_path:
                html_parts.append(
                    f"<img class='screenshot' src='{preview.screenshot_path}' alt='{wp.name}'/>"
                )

            html_parts.append("</div>")

        html_parts.extend([
            "</body>",
            "</html>",
        ])

        with open(filepath, "w") as f:
            f.write("\n".join(html_parts))


class AsyncWaypointPreviewer:
    """Async version of WaypointPreviewer."""

    def __init__(
        self,
        page: Any,
        config: PreviewConfig | None = None,
    ) -> None:
        """Initialize the async previewer.

        Args:
            page: Async Playwright page object.
            config: Preview configuration.
        """
        self._page = page
        self._config = config or PreviewConfig()
        self._previews: list[WaypointPreview] = []
        self._current_index = 0
        self._adjustment_callback: AdjustmentCallback | None = None

    def set_adjustment_callback(self, callback: AdjustmentCallback) -> None:
        """Set callback for interactive adjustments."""
        self._adjustment_callback = callback

    async def _take_screenshot(self) -> Image.Image:
        """Take a screenshot of the current page."""
        screenshot_bytes = await self._page.screenshot()
        return Image.open(io.BytesIO(screenshot_bytes))

    def _save_screenshot(
        self,
        screenshot: Image.Image,
        waypoint_name: str,
        index: int,
    ) -> str:
        """Save a screenshot to disk."""
        screenshot_dir = Path(self._config.screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        clean_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in waypoint_name)
        filename = f"{index:02d}_{clean_name}.{self._config.screenshot_format}"
        filepath = screenshot_dir / filename

        screenshot.save(filepath)
        return str(filepath)

    async def _scroll_to(self, position: float) -> float:
        """Scroll to a position and return actual position."""
        scroller = AsyncAutoScroller(self._page)
        await scroller.smooth_scroll_to(position, duration=self._config.scroll_duration)
        await asyncio.sleep(self._config.scroll_duration + 0.1)

        return await self._page.evaluate("window.scrollY")

    async def preview_waypoint(
        self,
        waypoint: Waypoint,
        index: int,
        capture: bool = True,
    ) -> WaypointPreview:
        """Preview a single waypoint."""
        actual_position = await self._scroll_to(waypoint.position)
        position_diff = actual_position - waypoint.position

        preview = WaypointPreview(
            waypoint=waypoint,
            index=index,
            actual_position=actual_position,
            position_diff=position_diff,
        )

        if capture and self._config.capture_screenshots:
            screenshot = await self._take_screenshot()
            preview.screenshot = screenshot
            preview.screenshot_path = self._save_screenshot(
                screenshot, waypoint.name, index
            )

        await asyncio.sleep(self._config.pause_duration)

        return preview

    async def preview_all(
        self,
        waypoints: list[Waypoint],
        interactive: bool = False,
    ) -> list[WaypointPreview]:
        """Preview all waypoints."""
        self._previews = []

        for index, waypoint in enumerate(waypoints):
            preview = await self.preview_waypoint(waypoint, index)
            self._previews.append(preview)

            if interactive and self._adjustment_callback:
                await self._interactive_adjust(preview)

        return self._previews

    async def _interactive_adjust(self, preview: WaypointPreview) -> None:
        """Handle interactive adjustment for a waypoint."""
        if self._adjustment_callback is None:
            return

        total_adjustment = 0

        while True:
            adjustment = self._adjustment_callback(preview, "adjust")

            if adjustment is None:
                preview.approved = True
                break

            total_adjustment += adjustment
            preview.adjustment = total_adjustment

            new_position = preview.waypoint.position + total_adjustment
            actual = await self._scroll_to(new_position)

            preview.actual_position = actual
            preview.position_diff = actual - new_position

            if self._config.capture_screenshots:
                screenshot = await self._take_screenshot()
                preview.screenshot = screenshot
                if preview.screenshot_path:
                    screenshot.save(preview.screenshot_path)

    def apply_adjustments(
        self,
        waypoints: list[Waypoint],
    ) -> list[Waypoint]:
        """Apply preview adjustments to waypoints."""
        if not self._previews:
            return waypoints

        result = []
        preview_map = {p.index: p for p in self._previews}

        for i, wp in enumerate(waypoints):
            if i in preview_map and preview_map[i].adjustment != 0:
                new_wp = Waypoint(
                    name=wp.name,
                    position=wp.position + preview_map[i].adjustment,
                    pause=wp.pause,
                    scroll_duration=wp.scroll_duration,
                    description=wp.description,
                    framing_rule=wp.framing_rule,
                )
                result.append(new_wp)
            else:
                result.append(wp)

        return result

    def generate_report(self, waypoints: list[Waypoint]) -> PreviewReport:
        """Generate a preview report."""
        total_distance = 0
        estimated_duration = 0
        adjustments_made = 0
        all_approved = True

        prev_position = 0
        for preview in self._previews:
            wp = preview.waypoint
            distance = abs(wp.position - prev_position)
            total_distance += distance
            estimated_duration += wp.scroll_duration + wp.pause

            if preview.adjustment != 0:
                adjustments_made += 1
            if not preview.approved:
                all_approved = False

            prev_position = wp.position

        return PreviewReport(
            waypoints=self._previews,
            total_scroll_distance=total_distance,
            estimated_duration=estimated_duration,
            screenshot_dir=self._config.screenshot_dir if self._config.capture_screenshots else None,
            adjustments_made=adjustments_made,
            all_approved=all_approved,
        )

    def export_report_json(
        self,
        report: PreviewReport,
        filepath: str,
    ) -> None:
        """Export preview report to JSON."""
        data = {
            "total_scroll_distance": report.total_scroll_distance,
            "estimated_duration": report.estimated_duration,
            "screenshot_dir": report.screenshot_dir,
            "adjustments_made": report.adjustments_made,
            "all_approved": report.all_approved,
            "waypoints": [
                {
                    "index": p.index,
                    "name": p.waypoint.name,
                    "target_position": p.waypoint.position,
                    "actual_position": p.actual_position,
                    "position_diff": p.position_diff,
                    "pause": p.waypoint.pause,
                    "scroll_duration": p.waypoint.scroll_duration,
                    "description": p.waypoint.description,
                    "framing_rule": (
                        p.waypoint.framing_rule.alignment.value
                        if p.waypoint.framing_rule
                        else None
                    ),
                    "screenshot_path": p.screenshot_path,
                    "approved": p.approved,
                    "adjustment": p.adjustment,
                }
                for p in report.waypoints
            ],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def export_report_html(
        self,
        report: PreviewReport,
        filepath: str,
    ) -> None:
        """Export preview report to HTML."""
        # Use same implementation as sync version
        WaypointPreviewer._export_report_html_impl(report, filepath)


# Standalone convenience functions

def preview_waypoints(
    page: Any,
    waypoints: list[Waypoint],
    config: PreviewConfig | None = None,
    interactive: bool = False,
) -> list[WaypointPreview]:
    """Preview waypoints on a page (convenience function).

    Args:
        page: Playwright page (sync).
        waypoints: List of waypoints to preview.
        config: Optional preview configuration.
        interactive: Whether to allow adjustments.

    Returns:
        List of WaypointPreview objects.
    """
    previewer = WaypointPreviewer(page, config)
    return previewer.preview_all(waypoints, interactive=interactive)


async def preview_waypoints_async(
    page: Any,
    waypoints: list[Waypoint],
    config: PreviewConfig | None = None,
    interactive: bool = False,
) -> list[WaypointPreview]:
    """Preview waypoints on a page (async convenience function).

    Args:
        page: Playwright page (async).
        waypoints: List of waypoints to preview.
        config: Optional preview configuration.
        interactive: Whether to allow adjustments.

    Returns:
        List of WaypointPreview objects.
    """
    previewer = AsyncWaypointPreviewer(page, config)
    return await previewer.preview_all(waypoints, interactive=interactive)


def generate_preview_report(
    page: Any,
    waypoints: list[Waypoint],
    output_path: str,
    format: str = "json",
    config: PreviewConfig | None = None,
) -> PreviewReport:
    """Generate a preview report for waypoints.

    Args:
        page: Playwright page (sync).
        waypoints: List of waypoints.
        output_path: Path to save the report.
        format: Output format ('json' or 'html').
        config: Optional preview configuration.

    Returns:
        PreviewReport with summary data.
    """
    previewer = WaypointPreviewer(page, config)
    previewer.preview_all(waypoints, interactive=False)
    report = previewer.generate_report(waypoints)

    if format == "json":
        previewer.export_report_json(report, output_path)
    elif format == "html":
        previewer.export_report_html(report, output_path)
    else:
        raise ValueError(f"Unsupported format: {format}")

    return report


def approve_all_waypoints(
    waypoints: list[Waypoint],
) -> list[WaypointPreview]:
    """Mark all waypoints as approved without preview.

    Args:
        waypoints: List of waypoints.

    Returns:
        List of approved WaypointPreview objects.
    """
    return [
        WaypointPreview(
            waypoint=wp,
            index=i,
            actual_position=wp.position,
            position_diff=0,
            approved=True,
        )
        for i, wp in enumerate(waypoints)
    ]
