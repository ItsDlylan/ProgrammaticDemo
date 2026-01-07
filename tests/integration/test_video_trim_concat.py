"""INT-010: Test video trim and concat.

This test verifies that:
1. Videos can be trimmed to specified time ranges
2. Multiple clips can be concatenated
3. Output duration is correct
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from programmatic_demo.postprocess.editor import VideoEditor, FFmpegBuilder


def ffmpeg_available() -> bool:
    """Check if FFmpeg is available on the system."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def ffprobe_available() -> bool:
    """Check if ffprobe is available on the system."""
    try:
        subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_video_duration(path: str) -> float:
    """Get the duration of a video file using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, check=True)
    info = json.loads(result.stdout.decode())
    return float(info.get("format", {}).get("duration", 0))


def create_test_video(duration: float, path: str) -> bool:
    """Create a simple test video of specified duration.

    Creates a video with a solid color background and text showing time.

    Args:
        duration: Duration in seconds.
        path: Output path.

    Returns:
        True if video was created successfully.
    """
    try:
        # Generate a simple color test video
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=blue:s=320x240:d={duration}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),
            path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_video(temp_dir):
    """Create a 10-second test video."""
    video_path = str(temp_dir / "test_video.mp4")
    if create_test_video(10.0, video_path):
        return video_path
    pytest.skip("Could not create test video")


@pytest.fixture
def test_videos(temp_dir):
    """Create multiple test videos for concat testing."""
    videos = []
    durations = [3.0, 4.0, 3.0]  # 3 + 4 + 3 = 10 seconds total

    for i, duration in enumerate(durations):
        video_path = str(temp_dir / f"clip_{i}.mp4")
        if create_test_video(duration, video_path):
            videos.append(video_path)
        else:
            pytest.skip(f"Could not create test video {i}")

    return videos


@pytest.mark.skipif(not ffmpeg_available(), reason="FFmpeg not available")
class TestVideoTrim:
    """Test video trimming functionality."""

    def test_trim_creates_output_file(self, temp_dir, test_video):
        """Test that trim creates an output file."""
        output_path = str(temp_dir / "trimmed.mp4")

        editor = VideoEditor()
        result = editor.trim(test_video, 2.0, 5.0, output_path)

        assert result["success"]
        assert Path(output_path).exists()

    @pytest.mark.skipif(not ffprobe_available(), reason="ffprobe not available")
    def test_trim_duration_correct(self, temp_dir, test_video):
        """Test that trimmed video has correct duration."""
        output_path = str(temp_dir / "trimmed.mp4")

        editor = VideoEditor()
        result = editor.trim(test_video, 2.0, 5.0, output_path)

        assert result["success"]

        # Check output duration (should be approximately 3 seconds)
        duration = get_video_duration(output_path)
        assert abs(duration - 3.0) < 0.5  # Allow 0.5s tolerance

    def test_trim_from_start(self, temp_dir, test_video):
        """Test trimming from the beginning of a video."""
        output_path = str(temp_dir / "trimmed.mp4")

        editor = VideoEditor()
        result = editor.trim(test_video, 0.0, 3.0, output_path)

        assert result["success"]
        assert Path(output_path).exists()

    def test_trim_to_end(self, temp_dir, test_video):
        """Test trimming to the end of a video."""
        output_path = str(temp_dir / "trimmed.mp4")

        editor = VideoEditor()
        result = editor.trim(test_video, 7.0, 10.0, output_path)

        assert result["success"]
        assert Path(output_path).exists()

    def test_trim_middle_section(self, temp_dir, test_video):
        """Test trimming a middle section of a video."""
        output_path = str(temp_dir / "trimmed.mp4")

        editor = VideoEditor()
        result = editor.trim(test_video, 3.0, 7.0, output_path)

        assert result["success"]
        assert Path(output_path).exists()


@pytest.mark.skipif(not ffmpeg_available(), reason="FFmpeg not available")
class TestVideoConcat:
    """Test video concatenation functionality."""

    def test_concat_creates_output_file(self, temp_dir, test_videos):
        """Test that concat creates an output file."""
        output_path = str(temp_dir / "concat.mp4")

        editor = VideoEditor()
        result = editor.concat(test_videos, output_path)

        assert result["success"]
        assert Path(output_path).exists()

    @pytest.mark.skipif(not ffprobe_available(), reason="ffprobe not available")
    def test_concat_duration_correct(self, temp_dir, test_videos):
        """Test that concatenated video has correct total duration."""
        output_path = str(temp_dir / "concat.mp4")

        editor = VideoEditor()
        result = editor.concat(test_videos, output_path)

        assert result["success"]

        # Check output duration (should be approximately 10 seconds: 3+4+3)
        duration = get_video_duration(output_path)
        # Allow some tolerance for encoding differences
        assert 8.0 < duration < 12.0

    def test_concat_two_videos(self, temp_dir):
        """Test concatenating two videos."""
        # Create two short test videos
        video1 = str(temp_dir / "clip1.mp4")
        video2 = str(temp_dir / "clip2.mp4")
        output = str(temp_dir / "concat.mp4")

        if not create_test_video(2.0, video1) or not create_test_video(2.0, video2):
            pytest.skip("Could not create test videos")

        editor = VideoEditor()
        result = editor.concat([video1, video2], output)

        assert result["success"]
        assert Path(output).exists()

    def test_concat_single_video(self, temp_dir, test_video):
        """Test concat with a single video just copies it."""
        output_path = str(temp_dir / "copy.mp4")

        editor = VideoEditor()
        result = editor.concat([test_video], output_path)

        assert result["success"]
        assert Path(output_path).exists()

    def test_concat_empty_list_fails(self, temp_dir):
        """Test that concat with empty list returns error."""
        output_path = str(temp_dir / "empty.mp4")

        editor = VideoEditor()
        result = editor.concat([], output_path)

        assert not result["success"]
        assert "error" in result


@pytest.mark.skipif(not ffmpeg_available(), reason="FFmpeg not available")
class TestFFmpegBuilder:
    """Test FFmpegBuilder utility class."""

    def test_builder_creates_command(self):
        """Test that builder creates a valid command list."""
        builder = (
            FFmpegBuilder()
            .overwrite()
            .input("input.mp4")
            .output("output.mp4", c="copy")
        )

        cmd = builder.build()

        assert "ffmpeg" in cmd
        assert "-y" in cmd
        assert "-i" in cmd
        assert "input.mp4" in cmd
        assert "output.mp4" in cmd

    def test_builder_with_filter(self):
        """Test builder with filter options."""
        builder = (
            FFmpegBuilder()
            .input("input.mp4")
            .filter("scale=1920:1080")
            .output("output.mp4")
        )

        cmd = builder.build()

        assert "-vf" in cmd or "-filter_complex" in cmd

    def test_builder_reset(self):
        """Test builder reset clears state."""
        builder = (
            FFmpegBuilder()
            .input("input.mp4")
            .output("output.mp4")
            .filter("scale=1920:1080")
        )

        builder.reset()

        cmd = builder.build()
        assert "input.mp4" not in cmd
        assert "output.mp4" not in cmd


@pytest.mark.skipif(not ffmpeg_available(), reason="FFmpeg not available")
class TestTrimAndConcat:
    """Test trim and concat workflow together."""

    @pytest.mark.skipif(not ffprobe_available(), reason="ffprobe not available")
    def test_trim_then_concat(self, temp_dir, test_video):
        """Test workflow: trim video into segments, then concat them back."""
        # Trim middle section of video
        trimmed_path = str(temp_dir / "middle.mp4")

        editor = VideoEditor()
        trim_result = editor.trim(test_video, 3.0, 7.0, trimmed_path)
        assert trim_result["success"]

        # Create another clip
        clip2 = str(temp_dir / "clip2.mp4")
        if not create_test_video(2.0, clip2):
            pytest.skip("Could not create second clip")

        # Concat the trimmed segment with new clip
        final_output = str(temp_dir / "final.mp4")
        concat_result = editor.concat([trimmed_path, clip2], final_output)

        assert concat_result["success"]
        assert Path(final_output).exists()

        # Verify final duration (4s trimmed + 2s new = ~6s)
        final_duration = get_video_duration(final_output)
        assert 4.0 < final_duration < 8.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
