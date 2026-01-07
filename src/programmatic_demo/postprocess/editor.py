"""Video editor for post-processing demo recordings.

The VideoEditor provides editing capabilities:
- Trimming and cutting segments
- Joining video clips
- Adding intros, outros, transitions
- Audio processing
- Final export
"""

import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self


class FFmpegBuilder:
    """Builder for constructing FFmpeg commands.

    Provides a fluent interface for building FFmpeg commands
    with inputs, outputs, filters, and options.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        """Initialize the FFmpegBuilder.

        Args:
            ffmpeg_path: Path to ffmpeg binary.
        """
        self._ffmpeg_path = ffmpeg_path
        self._inputs: list[dict[str, Any]] = []
        self._outputs: list[dict[str, Any]] = []
        self._filters: list[str] = []
        self._global_options: list[str] = []

    def input(
        self,
        path: str,
        **options: Any,
    ) -> Self:
        """Add an input file.

        Args:
            path: Path to input file.
            **options: Input options (e.g., ss=5 for -ss 5).

        Returns:
            Self for method chaining.
        """
        self._inputs.append({"path": path, "options": options})
        return self

    def output(
        self,
        path: str,
        **options: Any,
    ) -> Self:
        """Set the output file.

        Args:
            path: Path to output file.
            **options: Output options (e.g., c="copy" for -c copy).

        Returns:
            Self for method chaining.
        """
        self._outputs.append({"path": path, "options": options})
        return self

    def filter(self, filter_str: str) -> Self:
        """Add a filter to the filter chain.

        Args:
            filter_str: Filter string (e.g., "scale=1920:1080").

        Returns:
            Self for method chaining.
        """
        self._filters.append(filter_str)
        return self

    def filter_complex(self, filter_str: str) -> Self:
        """Add a complex filter.

        Args:
            filter_str: Complex filter string.

        Returns:
            Self for method chaining.
        """
        return self.filter(filter_str)

    def option(self, name: str, value: Any = None) -> Self:
        """Add a global option.

        Args:
            name: Option name (without leading dash).
            value: Option value, None for flag options.

        Returns:
            Self for method chaining.
        """
        if value is not None:
            self._global_options.extend([f"-{name}", str(value)])
        else:
            self._global_options.append(f"-{name}")
        return self

    def overwrite(self) -> Self:
        """Enable overwriting output files.

        Returns:
            Self for method chaining.
        """
        return self.option("y")

    def build(self) -> list[str]:
        """Build the FFmpeg command as a list of arguments.

        Returns:
            List of command arguments.
        """
        cmd = [self._ffmpeg_path]

        # Global options
        cmd.extend(self._global_options)

        # Inputs
        for inp in self._inputs:
            for key, value in inp["options"].items():
                cmd.extend([f"-{key}", str(value)])
            cmd.extend(["-i", inp["path"]])

        # Filters
        if self._filters:
            if len(self._inputs) > 1 or any("[" in f for f in self._filters):
                # Complex filtergraph
                cmd.extend(["-filter_complex", ";".join(self._filters)])
            else:
                # Simple filter chain
                cmd.extend(["-vf", ",".join(self._filters)])

        # Outputs
        for out in self._outputs:
            for key, value in out["options"].items():
                if isinstance(value, bool):
                    if value:
                        cmd.append(f"-{key}")
                else:
                    cmd.extend([f"-{key}", str(value)])
            cmd.append(out["path"])

        return cmd

    def build_string(self) -> str:
        """Build the FFmpeg command as a shell string.

        Returns:
            Shell-escaped command string.
        """
        return shlex.join(self.build())

    def run(
        self,
        capture_output: bool = True,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        """Execute the FFmpeg command.

        Args:
            capture_output: Whether to capture stdout/stderr.
            check: Whether to raise on non-zero exit code.

        Returns:
            CompletedProcess with result.
        """
        cmd = self.build()
        return subprocess.run(
            cmd,
            capture_output=capture_output,
            check=check,
        )

    def run_async(self) -> subprocess.Popen[bytes]:
        """Execute the FFmpeg command asynchronously.

        Returns:
            Popen process handle.
        """
        cmd = self.build()
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def reset(self) -> Self:
        """Reset the builder to initial state.

        Returns:
            Self for method chaining.
        """
        self._inputs.clear()
        self._outputs.clear()
        self._filters.clear()
        self._global_options.clear()
        return self


@dataclass
class VideoSegment:
    """A segment of video to include in the final edit.

    Attributes:
        path: Path to source video file
        start_time: Start time in source video (seconds)
        end_time: End time in source video (seconds)
        effects: List of effects to apply to this segment
        label: Optional label for the segment
    """

    path: str
    start_time: float
    end_time: float
    effects: list[Any] = field(default_factory=list)
    label: str | None = None


@dataclass
class EditProject:
    """A video editing project.

    Attributes:
        segments: Ordered list of video segments
        output_path: Path for final output
        resolution: Output resolution as (width, height)
        fps: Output frames per second
        output_format: Output format (mp4, webm, etc.)
    """

    segments: list[VideoSegment] = field(default_factory=list)
    output_path: str = ""
    resolution: tuple[int, int] = (1920, 1080)
    fps: int = 60
    output_format: str = "mp4"


class VideoEditor:
    """Editor for post-processing demo videos.

    The VideoEditor combines video segments, applies transitions,
    and produces the final demo video.
    """

    def __init__(self) -> None:
        """Initialize the VideoEditor."""
        self._project = EditProject()

    @property
    def project(self) -> EditProject:
        """Get the current edit project."""
        return self._project

    def add_segment(self, segment: VideoSegment) -> None:
        """Add a video segment to the project.

        Args:
            segment: Video segment to add.
        """
        self._project.segments.append(segment)

    def clear_segments(self) -> None:
        """Clear all segments from the project."""
        self._project.segments.clear()

    def trim(
        self,
        source_path: str,
        start_time: float,
        end_time: float,
        output_path: str,
    ) -> dict[str, Any]:
        """Trim a video to specified time range.

        Args:
            source_path: Path to source video.
            start_time: Start time in seconds.
            end_time: End time in seconds.
            output_path: Path for trimmed output.

        Returns:
            Result dict with success status.
        """
        raise NotImplementedError("trim not yet implemented")

    def join(
        self,
        segment_paths: list[str],
        output_path: str,
    ) -> dict[str, Any]:
        """Join multiple video files into one.

        Args:
            segment_paths: Paths to video files to join.
            output_path: Path for joined output.

        Returns:
            Result dict with success status.
        """
        raise NotImplementedError("join not yet implemented")

    def add_intro(
        self,
        intro_path: str,
    ) -> None:
        """Add an intro video to the beginning.

        Args:
            intro_path: Path to intro video.
        """
        raise NotImplementedError("add_intro not yet implemented")

    def add_outro(
        self,
        outro_path: str,
    ) -> None:
        """Add an outro video to the end.

        Args:
            outro_path: Path to outro video.
        """
        raise NotImplementedError("add_outro not yet implemented")

    def export(
        self,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """Export the final video.

        Args:
            output_path: Output path, uses project default if None.

        Returns:
            Result dict with success status and output path.
        """
        raise NotImplementedError("export not yet implemented")

    def reset(self) -> None:
        """Reset the editor to a fresh state."""
        self._project = EditProject()
