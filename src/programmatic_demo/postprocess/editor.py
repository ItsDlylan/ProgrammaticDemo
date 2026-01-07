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
        duration = end_time - start_time
        builder = (
            FFmpegBuilder()
            .overwrite()
            .input(source_path, ss=start_time)
            .output(output_path, t=duration, c="copy")
        )

        try:
            builder.run()
            return {"success": True, "output": output_path}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr.decode() if e.stderr else str(e)}

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
        return self.concat(segment_paths, output_path)

    def concat(
        self,
        inputs: list[str],
        output_path: str,
        crossfade: float = 0.0,
    ) -> dict[str, Any]:
        """Concatenate video files with optional crossfade.

        Args:
            inputs: List of input video paths.
            output_path: Path for output video.
            crossfade: Crossfade duration in seconds (0 for no crossfade).

        Returns:
            Result dict with success status.
        """
        if not inputs:
            return {"success": False, "error": "No input files provided"}

        if len(inputs) == 1:
            # Single file, just copy
            builder = (
                FFmpegBuilder()
                .overwrite()
                .input(inputs[0])
                .output(output_path, c="copy")
            )
            try:
                builder.run()
                return {"success": True, "output": output_path}
            except subprocess.CalledProcessError as e:
                return {"success": False, "error": e.stderr.decode() if e.stderr else str(e)}

        builder = FFmpegBuilder().overwrite()

        # Add all inputs
        for inp in inputs:
            builder.input(inp)

        if crossfade > 0:
            # Build complex filter for crossfade transitions
            filter_parts = []
            n = len(inputs)
            for i in range(n):
                filter_parts.append(f"[{i}:v]")
            filter_str = (
                "".join(filter_parts)
                + f"concat=n={n}:v=1:a=0[v]"
            )
            builder.filter_complex(filter_str)
            builder.output(output_path, **{"map": "[v]"})
        else:
            # Simple concat using concat demuxer approach via filter
            filter_parts = []
            for i in range(len(inputs)):
                filter_parts.append(f"[{i}:v]")
            filter_str = "".join(filter_parts) + f"concat=n={len(inputs)}:v=1:a=0[v]"
            builder.filter_complex(filter_str)
            builder.output(output_path, **{"map": "[v]"})

        try:
            builder.run()
            return {"success": True, "output": output_path}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr.decode() if e.stderr else str(e)}

    def speed_adjust(
        self,
        input_path: str,
        factor: float,
        output_path: str,
    ) -> dict[str, Any]:
        """Adjust video playback speed.

        Args:
            input_path: Path to source video.
            factor: Speed factor (0.5 = half speed, 2.0 = double speed).
            output_path: Path for output video.

        Returns:
            Result dict with success status.
        """
        if factor <= 0:
            return {"success": False, "error": "Speed factor must be positive"}

        # setpts filter: divide by factor to speed up, multiply to slow down
        pts_factor = 1.0 / factor
        builder = (
            FFmpegBuilder()
            .overwrite()
            .input(input_path)
            .filter(f"setpts={pts_factor}*PTS")
            .output(output_path)
        )

        try:
            builder.run()
            return {"success": True, "output": output_path}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr.decode() if e.stderr else str(e)}

    def resize(
        self,
        input_path: str,
        width: int,
        height: int,
        output_path: str,
    ) -> dict[str, Any]:
        """Resize video to specified dimensions.

        Args:
            input_path: Path to source video.
            width: Target width in pixels.
            height: Target height in pixels.
            output_path: Path for output video.

        Returns:
            Result dict with success status.
        """
        builder = (
            FFmpegBuilder()
            .overwrite()
            .input(input_path)
            .filter(f"scale={width}:{height}")
            .output(output_path)
        )

        try:
            builder.run()
            return {"success": True, "output": output_path}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr.decode() if e.stderr else str(e)}

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

    def create_title_slide(
        self,
        text: str,
        duration: float,
        output_path: str,
        style: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a title slide video.

        Args:
            text: Title text to display.
            duration: Duration of the slide in seconds.
            output_path: Path for output video.
            style: Optional style dict with font, size, color, background.

        Returns:
            Result dict with success status.
        """
        style = style or {}
        font_size = style.get("font_size", 72)
        font_color = style.get("font_color", "white")
        bg_color = style.get("bg_color", "black")
        width = style.get("width", 1920)
        height = style.get("height", 1080)

        # Escape text for FFmpeg
        escaped_text = text.replace("'", "\\'").replace(":", "\\:")

        builder = (
            FFmpegBuilder()
            .overwrite()
            .option("f", "lavfi")
            .input(f"color=c={bg_color}:s={width}x{height}:d={duration}")
            .filter(
                f"drawtext=text='{escaped_text}':"
                f"fontsize={font_size}:fontcolor={font_color}:"
                f"x=(w-text_w)/2:y=(h-text_h)/2"
            )
            .output(output_path)
        )

        try:
            builder.run()
            return {"success": True, "output": output_path}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr.decode() if e.stderr else str(e)}

    def create_outro_slide(
        self,
        text: str,
        duration: float,
        output_path: str,
        style: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create an outro slide video.

        Args:
            text: Outro text to display.
            duration: Duration of the slide in seconds.
            output_path: Path for output video.
            style: Optional style dict with font, size, color, background.

        Returns:
            Result dict with success status.
        """
        # Outro slide uses same logic as title slide
        return self.create_title_slide(text, duration, output_path, style)

    def prepend_intro(
        self,
        video_path: str,
        intro_path: str,
        output_path: str,
        transition: str | None = None,
        transition_duration: float = 0.5,
    ) -> dict[str, Any]:
        """Prepend an intro slide or video to a main video.

        This is a convenience method for the common pattern of adding
        an intro to a demo video. Supports both video and image intros.

        Args:
            video_path: Path to the main video file.
            intro_path: Path to intro video or image file.
            output_path: Path for the combined output video.
            transition: Optional transition type ("fade", "dissolve", None).
            transition_duration: Duration of transition in seconds.

        Returns:
            Result dict with success status and output path.
        """
        import os

        if not os.path.exists(video_path):
            return {"success": False, "error": f"Video file not found: {video_path}"}
        if not os.path.exists(intro_path):
            return {"success": False, "error": f"Intro file not found: {intro_path}"}

        # Detect if intro is an image (needs conversion to video)
        intro_ext = os.path.splitext(intro_path)[1].lower()
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

        if intro_ext in image_extensions:
            # Convert image to video segment
            import tempfile
            temp_intro = tempfile.mktemp(suffix=".mp4")
            intro_duration = 3.0  # Default 3 seconds for image intros

            builder = (
                FFmpegBuilder()
                .overwrite()
                .option("loop", 1)
                .option("t", intro_duration)
                .input(intro_path)
                .output(temp_intro, vcodec="libx264", pix_fmt="yuv420p")
            )

            try:
                builder.run()
            except subprocess.CalledProcessError as e:
                return {"success": False, "error": f"Failed to convert intro image: {e.stderr.decode() if e.stderr else str(e)}"}

            intro_video = temp_intro
        else:
            intro_video = intro_path
            temp_intro = None

        try:
            # Build filter based on transition type
            if transition in ("fade", "dissolve"):
                # Use xfade filter for transitions
                builder = FFmpegBuilder().overwrite()
                builder.input(intro_video)
                builder.input(video_path)

                # Get intro duration for offset calculation
                # Using a simplified approach - assume 3s for images or use probe
                offset = 3.0 - transition_duration if intro_ext in image_extensions else 2.0

                if transition == "fade":
                    filter_str = (
                        f"[0:v][1:v]xfade=transition=fade:"
                        f"duration={transition_duration}:offset={offset}[v]"
                    )
                else:  # dissolve
                    filter_str = (
                        f"[0:v][1:v]xfade=transition=dissolve:"
                        f"duration={transition_duration}:offset={offset}[v]"
                    )

                builder.filter_complex(filter_str)
                builder.output(output_path, **{"map": "[v]"})
            else:
                # Simple concat without transition
                builder = FFmpegBuilder().overwrite()
                builder.input(intro_video)
                builder.input(video_path)
                filter_str = "[0:v][1:v]concat=n=2:v=1:a=0[v]"
                builder.filter_complex(filter_str)
                builder.output(output_path, **{"map": "[v]"})

            builder.run()
            result = {"success": True, "output": output_path}

        except subprocess.CalledProcessError as e:
            result = {"success": False, "error": e.stderr.decode() if e.stderr else str(e)}

        finally:
            # Clean up temp file if created
            if temp_intro and os.path.exists(temp_intro):
                try:
                    os.remove(temp_intro)
                except OSError:
                    pass

        return result

    def reset(self) -> None:
        """Reset the editor to a fresh state."""
        self._project = EditProject()
