"""Integration tests for full smart demo recording workflow.

Tests the SmartDemoRecorder, preview mode, and visual CLI commands.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from PIL import Image
import numpy as np

from programmatic_demo.visual.smart_recorder import (
    SmartDemoRecorder,
    AsyncSmartDemoRecorder,
    RecordingConfig,
    RecordingProgress,
    RecordingResult,
    WaypointOverride,
)
from programmatic_demo.visual.preview_mode import (
    WaypointPreviewer,
    AsyncWaypointPreviewer,
    PreviewConfig,
    PreviewReport,
    WaypointPreview,
    preview_waypoints,
    approve_all_waypoints,
    generate_preview_report,
)
from programmatic_demo.visual.base import (
    ElementBounds,
    FramingAlignment,
    FramingRule,
    Section,
    Viewport,
    Waypoint,
)


# Fixtures


@pytest.fixture
def mock_page():
    """Create a mock Playwright page."""
    page = MagicMock()
    page.viewport_size = {"width": 1280, "height": 800}

    # Mock evaluate for scroll position
    page.evaluate = MagicMock(return_value=0)

    # Mock screenshot
    img = Image.new("RGB", (1280, 800), color="white")
    img_bytes = b""
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    page.screenshot = MagicMock(return_value=img_bytes)

    return page


@pytest.fixture
def mock_sections():
    """Create mock detected sections."""
    return [
        Section(
            name="hero",
            section_type="hero",
            bounds=ElementBounds(top=0, left=0, width=1280, height=600),
            scroll_position=0,
        ),
        Section(
            name="features",
            section_type="features",
            bounds=ElementBounds(top=600, left=0, width=1280, height=800),
            scroll_position=550,
        ),
        Section(
            name="pricing",
            section_type="pricing",
            bounds=ElementBounds(top=1400, left=0, width=1280, height=600),
            scroll_position=1350,
        ),
        Section(
            name="footer",
            section_type="footer",
            bounds=ElementBounds(top=2000, left=0, width=1280, height=200),
            scroll_position=1950,
        ),
    ]


@pytest.fixture
def mock_waypoints():
    """Create mock waypoints."""
    return [
        Waypoint(name="hero", position=0, pause=3.0, scroll_duration=0.5),
        Waypoint(name="features", position=550, pause=3.0, scroll_duration=1.5),
        Waypoint(name="pricing", position=1350, pause=3.5, scroll_duration=1.5),
        Waypoint(name="footer", position=1950, pause=1.5, scroll_duration=1.0),
        Waypoint(name="return_to_top", position=0, pause=2.0, scroll_duration=2.0),
    ]


# Test RecordingConfig


class TestRecordingConfig:
    """Tests for RecordingConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RecordingConfig()
        assert config.output_path == "demo.mp4"
        assert config.fps == 30
        assert config.animation_threshold == 0.03
        assert config.animation_timeout == 5.0
        assert config.min_section_height == 200
        assert config.include_return_to_top is True
        assert config.pause_multiplier == 1.0
        assert config.scroll_duration_multiplier == 1.0
        assert config.verify_framing is True
        assert config.max_framing_retries == 3

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RecordingConfig(
            output_path="custom.mp4",
            fps=60,
            animation_threshold=0.05,
            pause_multiplier=1.5,
        )
        assert config.output_path == "custom.mp4"
        assert config.fps == 60
        assert config.animation_threshold == 0.05
        assert config.pause_multiplier == 1.5


# Test WaypointOverride


class TestWaypointOverride:
    """Tests for WaypointOverride dataclass."""

    def test_basic_override(self):
        """Test basic override properties."""
        override = WaypointOverride(
            name="features",
            position=600,
            pause=4.0,
        )
        assert override.name == "features"
        assert override.position == 600
        assert override.pause == 4.0
        assert override.skip is False

    def test_skip_override(self):
        """Test skip override."""
        override = WaypointOverride(name="footer", skip=True)
        assert override.name == "footer"
        assert override.skip is True

    def test_insertion_override(self):
        """Test insertion override."""
        override = WaypointOverride(
            name="custom_section",
            position=1000,
            insert_after="features",
        )
        assert override.insert_after == "features"
        assert override.insert_before is None


# Test RecordingProgress


class TestRecordingProgress:
    """Tests for RecordingProgress dataclass."""

    def test_progress_properties(self):
        """Test progress properties."""
        progress = RecordingProgress(
            current_waypoint=2,
            total_waypoints=5,
            waypoint_name="pricing",
            phase="recording",
            elapsed_time=15.5,
            message="Recording pricing section...",
        )
        assert progress.current_waypoint == 2
        assert progress.total_waypoints == 5
        assert progress.waypoint_name == "pricing"
        assert progress.phase == "recording"
        assert progress.elapsed_time == 15.5


# Test RecordingResult


class TestRecordingResult:
    """Tests for RecordingResult dataclass."""

    def test_successful_result(self):
        """Test successful recording result."""
        result = RecordingResult(
            success=True,
            output_path="demo.mp4",
            duration=60.5,
            waypoints_visited=5,
            sections_detected=4,
            framing_corrections=2,
            animation_waits=5,
        )
        assert result.success is True
        assert result.output_path == "demo.mp4"
        assert result.duration == 60.5
        assert result.waypoints_visited == 5
        assert result.errors == []

    def test_failed_result(self):
        """Test failed recording result."""
        result = RecordingResult(
            success=False,
            output_path=None,
            duration=10.0,
            waypoints_visited=2,
            sections_detected=4,
            framing_corrections=0,
            animation_waits=2,
            errors=["Recording failed: timeout"],
        )
        assert result.success is False
        assert result.output_path is None
        assert len(result.errors) == 1


# Test SmartDemoRecorder


class TestSmartDemoRecorder:
    """Tests for SmartDemoRecorder class."""

    def test_initialization(self, mock_page):
        """Test recorder initialization."""
        config = RecordingConfig()
        recorder = SmartDemoRecorder(mock_page, config)

        assert recorder._page is mock_page
        assert recorder._config is config
        assert recorder._waypoints == []
        assert recorder._sections == []

    def test_set_progress_callback(self, mock_page):
        """Test setting progress callback."""
        recorder = SmartDemoRecorder(mock_page)
        callback = MagicMock()

        recorder.set_progress_callback(callback)
        assert recorder._progress_callback is callback

    def test_add_override(self, mock_page):
        """Test adding waypoint override."""
        recorder = SmartDemoRecorder(mock_page)

        override1 = WaypointOverride(name="features", position=600)
        override2 = WaypointOverride(name="pricing", skip=True)

        recorder.add_override(override1)
        recorder.add_override(override2)

        assert len(recorder._overrides) == 2

    def test_clear_overrides(self, mock_page):
        """Test clearing overrides."""
        recorder = SmartDemoRecorder(mock_page)
        recorder.add_override(WaypointOverride(name="test"))
        recorder.clear_overrides()

        assert len(recorder._overrides) == 0

    @patch("programmatic_demo.visual.smart_recorder.SectionDetector")
    def test_detect_sections(self, mock_detector_class, mock_page, mock_sections):
        """Test section detection."""
        mock_detector = MagicMock()
        mock_detector.find_sections.return_value = mock_sections
        mock_detector_class.return_value = mock_detector

        recorder = SmartDemoRecorder(mock_page)
        sections = recorder.detect_sections()

        assert len(sections) == 4
        mock_detector.find_sections.assert_called_once()

    @patch("programmatic_demo.visual.smart_recorder.WaypointGenerator")
    def test_generate_waypoints(self, mock_gen_class, mock_page, mock_waypoints):
        """Test waypoint generation."""
        mock_gen = MagicMock()
        mock_gen.generate_waypoints.return_value = mock_waypoints
        mock_gen_class.return_value = mock_gen

        config = RecordingConfig(pause_multiplier=1.5)
        recorder = SmartDemoRecorder(mock_page, config)
        waypoints = recorder.generate_waypoints()

        assert len(waypoints) == 5
        # Check multiplier was applied
        assert waypoints[0].pause == 3.0 * 1.5

    def test_set_waypoints(self, mock_page, mock_waypoints):
        """Test setting waypoints directly."""
        recorder = SmartDemoRecorder(mock_page)
        recorder.set_waypoints(mock_waypoints)

        assert recorder.get_waypoints() == mock_waypoints

    def test_get_waypoints_returns_copy(self, mock_page, mock_waypoints):
        """Test that get_waypoints returns a copy."""
        recorder = SmartDemoRecorder(mock_page)
        recorder.set_waypoints(mock_waypoints)

        waypoints1 = recorder.get_waypoints()
        waypoints2 = recorder.get_waypoints()

        assert waypoints1 is not waypoints2
        assert waypoints1 == waypoints2

    def test_stop_not_recording(self, mock_page):
        """Test stop when not recording."""
        recorder = SmartDemoRecorder(mock_page)
        result = recorder.stop()

        assert result["status"] == "success"

    def test_apply_skip_override(self, mock_page, mock_waypoints):
        """Test applying skip override."""
        recorder = SmartDemoRecorder(mock_page)
        recorder._waypoints = mock_waypoints.copy()
        recorder.add_override(WaypointOverride(name="footer", skip=True))

        recorder._apply_overrides()

        waypoint_names = [w.name for w in recorder._waypoints]
        assert "footer" not in waypoint_names
        assert len(recorder._waypoints) == 4

    def test_apply_position_override(self, mock_page, mock_waypoints):
        """Test applying position override."""
        recorder = SmartDemoRecorder(mock_page)
        recorder._waypoints = mock_waypoints.copy()
        recorder.add_override(WaypointOverride(name="features", position=700))

        recorder._apply_overrides()

        features_wp = next(w for w in recorder._waypoints if w.name == "features")
        assert features_wp.position == 700


# Test PreviewConfig


class TestPreviewConfig:
    """Tests for PreviewConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = PreviewConfig()
        assert config.scroll_duration == 0.5
        assert config.pause_duration == 1.0
        assert config.capture_screenshots is True
        assert config.screenshot_dir == "preview_screenshots"
        assert config.screenshot_format == "png"
        assert config.adjustment_step == 10
        assert config.large_adjustment_step == 50


# Test WaypointPreview


class TestWaypointPreview:
    """Tests for WaypointPreview dataclass."""

    def test_basic_preview(self):
        """Test basic preview properties."""
        waypoint = Waypoint(name="test", position=100)
        preview = WaypointPreview(
            waypoint=waypoint,
            index=0,
            actual_position=105,
            position_diff=5,
        )

        assert preview.waypoint is waypoint
        assert preview.index == 0
        assert preview.actual_position == 105
        assert preview.position_diff == 5
        assert preview.approved is False
        assert preview.adjustment == 0


# Test PreviewReport


class TestPreviewReport:
    """Tests for PreviewReport dataclass."""

    def test_report_properties(self):
        """Test report properties."""
        waypoint = Waypoint(name="test", position=100)
        previews = [
            WaypointPreview(waypoint=waypoint, index=0, approved=True)
        ]

        report = PreviewReport(
            waypoints=previews,
            total_scroll_distance=1000,
            estimated_duration=30.0,
            screenshot_dir="screenshots",
            adjustments_made=0,
            all_approved=True,
        )

        assert len(report.waypoints) == 1
        assert report.total_scroll_distance == 1000
        assert report.estimated_duration == 30.0
        assert report.all_approved is True


# Test WaypointPreviewer


class TestWaypointPreviewer:
    """Tests for WaypointPreviewer class."""

    def test_initialization(self, mock_page):
        """Test previewer initialization."""
        config = PreviewConfig()
        previewer = WaypointPreviewer(mock_page, config)

        assert previewer._page is mock_page
        assert previewer._config is config
        assert previewer._previews == []

    def test_set_adjustment_callback(self, mock_page):
        """Test setting adjustment callback."""
        previewer = WaypointPreviewer(mock_page)
        callback = MagicMock()

        previewer.set_adjustment_callback(callback)
        assert previewer._adjustment_callback is callback

    @patch("programmatic_demo.visual.preview_mode.AutoScroller")
    def test_preview_waypoint(self, mock_scroller_class, mock_page):
        """Test previewing a single waypoint."""
        mock_scroller = MagicMock()
        mock_scroller_class.return_value = mock_scroller

        # Configure page to return scroll position
        mock_page.evaluate.return_value = 100

        config = PreviewConfig(capture_screenshots=False)
        previewer = WaypointPreviewer(mock_page, config)

        waypoint = Waypoint(name="test", position=100)
        preview = previewer.preview_waypoint(waypoint, 0, capture=False)

        assert preview.waypoint is waypoint
        assert preview.index == 0
        assert preview.actual_position == 100

    def test_apply_adjustments_no_changes(self, mock_page, mock_waypoints):
        """Test applying adjustments with no changes."""
        previewer = WaypointPreviewer(mock_page)
        result = previewer.apply_adjustments(mock_waypoints)

        assert result == mock_waypoints

    def test_apply_adjustments_with_changes(self, mock_page):
        """Test applying adjustments with changes."""
        previewer = WaypointPreviewer(mock_page)

        waypoint = Waypoint(name="test", position=100)
        preview = WaypointPreview(
            waypoint=waypoint,
            index=0,
            adjustment=50,
        )
        previewer._previews = [preview]

        result = previewer.apply_adjustments([waypoint])

        assert len(result) == 1
        assert result[0].position == 150  # 100 + 50

    def test_generate_report(self, mock_page, mock_waypoints):
        """Test generating preview report."""
        previewer = WaypointPreviewer(mock_page)

        # Create mock previews
        previews = [
            WaypointPreview(
                waypoint=wp,
                index=i,
                approved=True,
            )
            for i, wp in enumerate(mock_waypoints)
        ]
        previewer._previews = previews

        report = previewer.generate_report(mock_waypoints)

        assert len(report.waypoints) == 5
        assert report.all_approved is True
        assert report.adjustments_made == 0

    def test_export_report_json(self, mock_page, mock_waypoints):
        """Test exporting report to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            previewer = WaypointPreviewer(mock_page)

            # Create mock previews
            previews = [
                WaypointPreview(
                    waypoint=wp,
                    index=i,
                    approved=True,
                    actual_position=wp.position,
                )
                for i, wp in enumerate(mock_waypoints)
            ]
            previewer._previews = previews

            report = previewer.generate_report(mock_waypoints)
            output_path = os.path.join(tmpdir, "report.json")

            previewer.export_report_json(report, output_path)

            assert os.path.exists(output_path)
            with open(output_path) as f:
                data = json.load(f)
            assert "waypoints" in data
            assert len(data["waypoints"]) == 5

    def test_export_report_html(self, mock_page, mock_waypoints):
        """Test exporting report to HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            previewer = WaypointPreviewer(mock_page)

            previews = [
                WaypointPreview(
                    waypoint=wp,
                    index=i,
                    approved=True,
                    actual_position=wp.position,
                )
                for i, wp in enumerate(mock_waypoints)
            ]
            previewer._previews = previews

            report = previewer.generate_report(mock_waypoints)
            output_path = os.path.join(tmpdir, "report.html")

            previewer.export_report_html(report, output_path)

            assert os.path.exists(output_path)
            with open(output_path) as f:
                html = f.read()
            assert "<!DOCTYPE html>" in html
            assert "hero" in html


# Test convenience functions


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_approve_all_waypoints(self, mock_waypoints):
        """Test approve_all_waypoints function."""
        previews = approve_all_waypoints(mock_waypoints)

        assert len(previews) == 5
        assert all(p.approved for p in previews)
        assert all(p.position_diff == 0 for p in previews)

    @patch("programmatic_demo.visual.preview_mode.WaypointPreviewer")
    def test_preview_waypoints(self, mock_previewer_class, mock_page, mock_waypoints):
        """Test preview_waypoints function."""
        mock_previewer = MagicMock()
        mock_previewer.preview_all.return_value = [
            WaypointPreview(waypoint=wp, index=i)
            for i, wp in enumerate(mock_waypoints)
        ]
        mock_previewer_class.return_value = mock_previewer

        result = preview_waypoints(mock_page, mock_waypoints)

        assert len(result) == 5
        mock_previewer.preview_all.assert_called_once()


# Test SmartDemoRecorder recording workflow


class TestSmartRecordingWorkflow:
    """Tests for the complete smart recording workflow."""

    @patch("programmatic_demo.visual.smart_recorder.get_recorder")
    @patch("programmatic_demo.visual.smart_recorder.SectionDetector")
    @patch("programmatic_demo.visual.smart_recorder.WaypointGenerator")
    @patch("programmatic_demo.visual.smart_recorder.AutoScroller")
    @patch("programmatic_demo.visual.smart_recorder.wait_for_animation_complete_sync")
    def test_full_recording_workflow(
        self,
        mock_wait_anim,
        mock_scroller_class,
        mock_gen_class,
        mock_detector_class,
        mock_get_recorder,
        mock_page,
        mock_sections,
        mock_waypoints,
    ):
        """Test complete recording workflow."""
        # Setup mocks
        mock_recorder = MagicMock()
        mock_recorder.start.return_value = {"status": "success"}
        mock_recorder.stop.return_value = {"status": "success"}
        mock_get_recorder.return_value = mock_recorder

        mock_detector = MagicMock()
        mock_detector.find_sections.return_value = mock_sections
        mock_detector_class.return_value = mock_detector

        mock_gen = MagicMock()
        mock_gen.generate_waypoints.return_value = mock_waypoints[:3]  # Fewer for faster test
        mock_gen_class.return_value = mock_gen

        mock_scroller = MagicMock()
        mock_scroller_class.return_value = mock_scroller

        mock_wait_anim.return_value = True

        # Run recording
        config = RecordingConfig(output_path="test.mp4")
        recorder = SmartDemoRecorder(mock_page, config)

        result = recorder.record()

        # Verify
        assert result.sections_detected == 4
        assert result.waypoints_visited == 3
        mock_recorder.start.assert_called_once()
        mock_recorder.stop.assert_called_once()

    @patch("programmatic_demo.visual.smart_recorder.get_recorder")
    def test_recording_with_no_waypoints(self, mock_get_recorder, mock_page):
        """Test recording fails gracefully with no waypoints."""
        mock_recorder = MagicMock()
        mock_get_recorder.return_value = mock_recorder

        with patch.object(SmartDemoRecorder, "detect_sections"):
            with patch.object(SmartDemoRecorder, "generate_waypoints") as mock_gen:
                mock_gen.return_value = []  # No waypoints

                recorder = SmartDemoRecorder(mock_page)
                recorder._waypoints = []

                result = recorder.record()

                assert result.success is False
                assert "No waypoints" in result.errors[0]

    def test_progress_callback_called(self, mock_page, mock_waypoints):
        """Test that progress callback is called during recording."""
        progress_calls = []

        def callback(progress):
            progress_calls.append(progress)

        with patch("programmatic_demo.visual.smart_recorder.get_recorder") as mock_get_recorder:
            mock_recorder = MagicMock()
            mock_recorder.start.return_value = {"status": "success"}
            mock_recorder.stop.return_value = {"status": "success"}
            mock_get_recorder.return_value = mock_recorder

            with patch("programmatic_demo.visual.smart_recorder.wait_for_animation_complete_sync"):
                with patch("programmatic_demo.visual.smart_recorder.SectionDetector") as mock_detector_class:
                    with patch("programmatic_demo.visual.smart_recorder.WaypointGenerator") as mock_gen_class:
                        mock_detector = MagicMock()
                        mock_detector.find_sections.return_value = []
                        mock_detector_class.return_value = mock_detector

                        mock_gen = MagicMock()
                        mock_gen.generate_waypoints.return_value = mock_waypoints[:2]
                        mock_gen_class.return_value = mock_gen

                        recorder = SmartDemoRecorder(mock_page)
                        recorder.set_progress_callback(callback)

                        with patch.object(recorder, "_scroll_to_position"):
                            recorder.record()

        # Should have multiple progress calls (detecting x2, scrolling x2, waiting x2, recording x2, final)
        assert len(progress_calls) >= 2  # At minimum: detecting sections and waypoints


# Test AsyncSmartDemoRecorder


class TestAsyncSmartDemoRecorder:
    """Tests for AsyncSmartDemoRecorder class."""

    def test_initialization(self, mock_page):
        """Test async recorder initialization."""
        config = RecordingConfig()
        recorder = AsyncSmartDemoRecorder(mock_page, config)

        assert recorder._page is mock_page
        assert recorder._config is config

    def test_set_waypoints(self, mock_page, mock_waypoints):
        """Test setting waypoints on async recorder."""
        recorder = AsyncSmartDemoRecorder(mock_page)
        recorder.set_waypoints(mock_waypoints)

        assert recorder.get_waypoints() == mock_waypoints

    def test_add_override(self, mock_page):
        """Test adding overrides on async recorder."""
        recorder = AsyncSmartDemoRecorder(mock_page)
        override = WaypointOverride(name="test", position=100)
        recorder.add_override(override)

        assert len(recorder._overrides) == 1

    def test_clear_overrides(self, mock_page):
        """Test clearing overrides on async recorder."""
        recorder = AsyncSmartDemoRecorder(mock_page)
        recorder.add_override(WaypointOverride(name="test"))
        recorder.clear_overrides()

        assert len(recorder._overrides) == 0


# Test CLI integration


class TestVisualCLI:
    """Tests for visual CLI commands."""

    def test_cli_module_imports(self):
        """Test that CLI module imports correctly."""
        from programmatic_demo.cli.visual import app
        assert app is not None

    def test_cli_commands_registered(self):
        """Test that CLI commands are registered."""
        from programmatic_demo.cli.visual import app

        command_names = [c.name for c in app.registered_commands]
        assert "detect-sections" in command_names
        assert "generate-waypoints" in command_names
        assert "preview" in command_names
        assert "verify-framing" in command_names
        assert "smart-record" in command_names
        assert "sections" in command_names


# Test edge cases


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_sections(self, mock_page):
        """Test handling of empty sections."""
        with patch("programmatic_demo.visual.smart_recorder.SectionDetector") as mock_class:
            mock_detector = MagicMock()
            mock_detector.find_sections.return_value = []
            mock_class.return_value = mock_detector

            recorder = SmartDemoRecorder(mock_page)
            sections = recorder.detect_sections()

            assert sections == []

    def test_adjustment_with_invalid_waypoint(self, mock_page, mock_waypoints):
        """Test override for non-existent waypoint."""
        recorder = SmartDemoRecorder(mock_page)
        recorder._waypoints = mock_waypoints.copy()
        recorder.add_override(
            WaypointOverride(
                name="new_section",
                position=500,
                insert_after="nonexistent",
            )
        )

        # Should handle gracefully without crashing
        recorder._apply_overrides()

        # Waypoints should be unchanged
        assert len(recorder._waypoints) == len(mock_waypoints)

    def test_preview_with_no_screenshots(self, mock_page):
        """Test preview without screenshot capture."""
        config = PreviewConfig(capture_screenshots=False)
        previewer = WaypointPreviewer(mock_page, config)

        waypoint = Waypoint(name="test", position=0)

        with patch.object(previewer, "_scroll_to", return_value=0):
            preview = previewer.preview_waypoint(waypoint, 0, capture=False)

        assert preview.screenshot is None
        assert preview.screenshot_path is None

    def test_recording_config_multipliers(self, mock_page, mock_waypoints):
        """Test that multipliers are applied correctly."""
        config = RecordingConfig(
            pause_multiplier=2.0,
            scroll_duration_multiplier=0.5,
        )

        with patch("programmatic_demo.visual.smart_recorder.WaypointGenerator") as mock_class:
            mock_gen = MagicMock()
            mock_gen.generate_waypoints.return_value = [
                Waypoint(name="test", position=0, pause=1.0, scroll_duration=1.0)
            ]
            mock_class.return_value = mock_gen

            recorder = SmartDemoRecorder(mock_page, config)
            waypoints = recorder.generate_waypoints()

            assert waypoints[0].pause == 2.0  # 1.0 * 2.0
            assert waypoints[0].scroll_duration == 0.5  # 1.0 * 0.5
