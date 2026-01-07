"""CLI commands for video post-processing."""

import json
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="Video post-processing commands.")


@app.command("trim")
def trim(
    input_file: str = typer.Argument(..., help="Input video file path"),
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    start: float = typer.Option(0.0, "--start", "-s", help="Start time in seconds"),
    end: Optional[float] = typer.Option(None, "--end", "-e", help="End time in seconds"),
    duration: Optional[float] = typer.Option(None, "--duration", "-d", help="Duration in seconds (alternative to end)"),
) -> None:
    """Trim a video to specified time range.

    Examples:
        pdemo video trim input.mp4 -o output.mp4 -s 5 -e 30
        pdemo video trim input.mp4 -o output.mp4 -s 10 -d 60
    """
    from programmatic_demo.postprocess import VideoEditor

    if not Path(input_file).exists():
        typer.echo(json.dumps({"success": False, "error": f"File not found: {input_file}"}))
        raise typer.Exit(1)

    if end is None and duration is None:
        typer.echo(json.dumps({"success": False, "error": "Must specify either --end or --duration"}))
        raise typer.Exit(1)

    if end is None and duration is not None:
        end = start + duration

    editor = VideoEditor()
    result = editor.trim(input_file, start, end, output)
    typer.echo(json.dumps(result, indent=2))

    if not result.get("success"):
        raise typer.Exit(1)


@app.command("concat")
def concat(
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    inputs: list[str] = typer.Argument(..., help="Input video files to concatenate"),
    crossfade: float = typer.Option(0.0, "--crossfade", "-x", help="Crossfade duration in seconds between videos"),
) -> None:
    """Concatenate multiple videos into one.

    Examples:
        pdemo video concat -o output.mp4 video1.mp4 video2.mp4 video3.mp4
        pdemo video concat -o output.mp4 -x 0.5 intro.mp4 main.mp4 outro.mp4
    """
    from programmatic_demo.postprocess import VideoEditor

    if not inputs:
        typer.echo(json.dumps({"success": False, "error": "No input files specified"}))
        raise typer.Exit(1)

    # Validate all input files exist
    for input_file in inputs:
        if not Path(input_file).exists():
            typer.echo(json.dumps({"success": False, "error": f"File not found: {input_file}"}))
            raise typer.Exit(1)

    editor = VideoEditor()
    result = editor.concat(inputs, output, crossfade=crossfade)
    typer.echo(json.dumps(result, indent=2))

    if not result.get("success"):
        raise typer.Exit(1)


@app.command("overlay")
def overlay(
    input_file: str = typer.Argument(..., help="Input video file path"),
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Text to overlay"),
    image: Optional[str] = typer.Option(None, "--image", "-i", help="Image file to overlay"),
    position: str = typer.Option("bottom-left", "--position", "-p", help="Position: top-left, top-right, bottom-left, bottom-right, center"),
    font_size: int = typer.Option(24, "--font-size", help="Font size for text overlay"),
    start_time: float = typer.Option(0.0, "--start", "-s", help="Start time for overlay in seconds"),
    duration: Optional[float] = typer.Option(None, "--duration", "-d", help="Duration of overlay (None = entire video)"),
) -> None:
    """Add a text or image overlay to a video.

    Examples:
        pdemo video overlay input.mp4 -o output.mp4 -t "My Demo" -p bottom-right
        pdemo video overlay input.mp4 -o output.mp4 -i logo.png -p top-left
    """
    from programmatic_demo.postprocess import VideoEditor, FFmpegBuilder
    import subprocess

    if not Path(input_file).exists():
        typer.echo(json.dumps({"success": False, "error": f"File not found: {input_file}"}))
        raise typer.Exit(1)

    if text is None and image is None:
        typer.echo(json.dumps({"success": False, "error": "Must specify either --text or --image"}))
        raise typer.Exit(1)

    # Calculate position coordinates
    position_map = {
        "top-left": ("10", "10"),
        "top-right": ("W-w-10", "10"),
        "bottom-left": ("10", "H-h-10"),
        "bottom-right": ("W-w-10", "H-h-10"),
        "center": ("(W-w)/2", "(H-h)/2"),
    }

    x_pos, y_pos = position_map.get(position, ("10", "H-h-10"))

    try:
        builder = FFmpegBuilder().overwrite().input(input_file)

        if text:
            # Text overlay using drawtext filter
            escaped_text = text.replace("'", "\\'").replace(":", "\\:")
            filter_str = f"drawtext=text='{escaped_text}':fontsize={font_size}:fontcolor=white:x={x_pos}:y={y_pos}"

            if duration is not None:
                end_time = start_time + duration
                filter_str += f":enable='between(t,{start_time},{end_time})'"
            elif start_time > 0:
                filter_str += f":enable='gte(t,{start_time})'"

            builder.filter(filter_str)

        elif image:
            if not Path(image).exists():
                typer.echo(json.dumps({"success": False, "error": f"Image not found: {image}"}))
                raise typer.Exit(1)

            # Image overlay using overlay filter
            builder.input(image)
            filter_str = f"overlay={x_pos}:{y_pos}"

            if duration is not None:
                end_time = start_time + duration
                filter_str += f":enable='between(t,{start_time},{end_time})'"
            elif start_time > 0:
                filter_str += f":enable='gte(t,{start_time})'"

            builder.filter_complex(f"[0:v][1:v]{filter_str}[v]")

        builder.output(output)
        builder.run()

        result = {"success": True, "output": output}
    except subprocess.CalledProcessError as e:
        result = {"success": False, "error": e.stderr.decode() if e.stderr else str(e)}

    typer.echo(json.dumps(result, indent=2))

    if not result.get("success"):
        raise typer.Exit(1)


@app.command("export")
def export(
    input_file: str = typer.Argument(..., help="Input video file path"),
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    preset: str = typer.Option("default", "--preset", "-p", help="Export preset: default, web, social, high-quality"),
    width: Optional[int] = typer.Option(None, "--width", "-w", help="Output width (maintains aspect ratio)"),
    height: Optional[int] = typer.Option(None, "--height", "-h", help="Output height (maintains aspect ratio)"),
    fps: Optional[int] = typer.Option(None, "--fps", help="Output frame rate"),
    codec: str = typer.Option("libx264", "--codec", "-c", help="Video codec"),
    audio_codec: str = typer.Option("aac", "--audio-codec", "-a", help="Audio codec"),
    bitrate: Optional[str] = typer.Option(None, "--bitrate", "-b", help="Video bitrate (e.g., 5M, 2500k)"),
) -> None:
    """Export/transcode a video with presets or custom settings.

    Presets:
        default     - Standard quality MP4 (libx264, 1080p)
        web         - Web-optimized MP4 (smaller size, 720p)
        social      - Social media format (1080x1080 square option)
        high-quality - Maximum quality (slower encoding)

    Examples:
        pdemo video export input.mp4 -o output.mp4 -p web
        pdemo video export input.mp4 -o output.mp4 -w 1920 -h 1080 -b 10M
    """
    from programmatic_demo.postprocess import FFmpegBuilder
    import subprocess

    if not Path(input_file).exists():
        typer.echo(json.dumps({"success": False, "error": f"File not found: {input_file}"}))
        raise typer.Exit(1)

    # Define presets
    presets = {
        "default": {
            "vcodec": "libx264",
            "preset": "medium",
            "crf": "23",
        },
        "web": {
            "vcodec": "libx264",
            "preset": "fast",
            "crf": "28",
            "scale": "1280:-2",
        },
        "social": {
            "vcodec": "libx264",
            "preset": "medium",
            "crf": "23",
        },
        "high-quality": {
            "vcodec": "libx264",
            "preset": "slow",
            "crf": "18",
        },
    }

    preset_config = presets.get(preset, presets["default"])

    try:
        builder = FFmpegBuilder().overwrite().input(input_file)

        # Build filter chain for scaling
        filters = []
        if width or height:
            scale_w = width if width else -2
            scale_h = height if height else -2
            filters.append(f"scale={scale_w}:{scale_h}")
        elif "scale" in preset_config:
            filters.append(f"scale={preset_config['scale']}")

        if filters:
            builder.filter(",".join(filters))

        # Apply codec settings
        output_opts = {
            "vcodec": codec or preset_config.get("vcodec", "libx264"),
            "acodec": audio_codec,
        }

        if "preset" in preset_config:
            output_opts["preset"] = preset_config["preset"]
        if "crf" in preset_config:
            output_opts["crf"] = preset_config["crf"]
        if bitrate:
            output_opts["b:v"] = bitrate
        if fps:
            output_opts["r"] = str(fps)

        builder.output(output, **output_opts)
        builder.run()

        result = {"success": True, "output": output, "preset": preset}
    except subprocess.CalledProcessError as e:
        result = {"success": False, "error": e.stderr.decode() if e.stderr else str(e)}

    typer.echo(json.dumps(result, indent=2))

    if not result.get("success"):
        raise typer.Exit(1)


@app.command("info")
def info(
    input_file: str = typer.Argument(..., help="Input video file path"),
) -> None:
    """Get information about a video file.

    Examples:
        pdemo video info video.mp4
    """
    import subprocess

    if not Path(input_file).exists():
        typer.echo(json.dumps({"success": False, "error": f"File not found: {input_file}"}))
        raise typer.Exit(1)

    try:
        # Use ffprobe to get video info
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            input_file,
        ]

        result = subprocess.run(cmd, capture_output=True, check=True)
        info_data = json.loads(result.stdout.decode())

        # Extract key information
        video_stream = None
        audio_stream = None
        for stream in info_data.get("streams", []):
            if stream.get("codec_type") == "video" and not video_stream:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and not audio_stream:
                audio_stream = stream

        output = {
            "success": True,
            "file": input_file,
            "format": info_data.get("format", {}).get("format_name"),
            "duration": float(info_data.get("format", {}).get("duration", 0)),
            "size_bytes": int(info_data.get("format", {}).get("size", 0)),
        }

        if video_stream:
            output["video"] = {
                "codec": video_stream.get("codec_name"),
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "fps": video_stream.get("r_frame_rate"),
            }

        if audio_stream:
            output["audio"] = {
                "codec": audio_stream.get("codec_name"),
                "sample_rate": audio_stream.get("sample_rate"),
                "channels": audio_stream.get("channels"),
            }

        typer.echo(json.dumps(output, indent=2))

    except subprocess.CalledProcessError as e:
        typer.echo(json.dumps({"success": False, "error": str(e)}))
        raise typer.Exit(1)
    except FileNotFoundError:
        typer.echo(json.dumps({"success": False, "error": "ffprobe not found - install ffmpeg"}))
        raise typer.Exit(1)
