#!/usr/bin/env python3
"""
Post-Processing Script - Apply Zoom Effects

Uses scale/crop approach which is more reliable than zoompan.
Creates multiple versions with different zoom intensities.
Now with smooth animated zoom transitions (ZOOM-002).
"""

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ZoomKeyframe:
    """Represents a keyframe in the zoom animation."""
    time: float
    zoom: float  # 1.0 = no zoom, 2.0 = 2x zoom
    center_x: float  # 0-1 normalized
    center_y: float  # 0-1 normalized


@dataclass
class ZoomTriggerConfig:
    """Configuration for intelligent zoom trigger detection."""
    velocity_threshold: float = 50.0  # pixels/second below which to trigger zoom
    min_stop_duration: float = 0.1  # minimum time at low velocity to trigger
    skip_during_scroll: bool = True  # skip zoom during scroll events
    triggers: List[str] = None  # 'click', 'hover', 'slow_down'

    def __post_init__(self):
        if self.triggers is None:
            self.triggers = ['click', 'slow_down']


def calculate_mouse_velocity(mouse_path: List[dict], time: float, window: float = 0.1) -> float:
    """Calculate mouse velocity at a specific time.

    Args:
        mouse_path: List of {t, x, y} position records
        time: Time to calculate velocity at
        window: Time window for velocity calculation (seconds)

    Returns:
        Velocity in pixels per second
    """
    if not mouse_path or len(mouse_path) < 2:
        return 0.0

    # Find positions within the time window
    positions = []
    for p in mouse_path:
        if abs(p["t"] - time) <= window:
            positions.append(p)

    if len(positions) < 2:
        # Find nearest two positions
        sorted_by_dist = sorted(mouse_path, key=lambda p: abs(p["t"] - time))
        positions = sorted_by_dist[:2]

    if len(positions) < 2:
        return 0.0

    # Calculate velocity from first to last position in window
    p1, p2 = positions[0], positions[-1]
    dt = abs(p2["t"] - p1["t"])
    if dt < 0.001:
        return 0.0

    dx = p2["x"] - p1["x"]
    dy = p2["y"] - p1["y"]
    distance = math.sqrt(dx * dx + dy * dy)

    return distance / dt


def analyze_mouse_velocity(
    mouse_path: List[dict],
    sample_interval: float = 0.033,  # ~30fps
) -> List[dict]:
    """Analyze mouse velocity over time.

    Args:
        mouse_path: List of {t, x, y} position records
        sample_interval: Time between velocity samples

    Returns:
        List of {t, velocity, x, y} records
    """
    if not mouse_path:
        return []

    velocities = []
    start_time = mouse_path[0]["t"]
    end_time = mouse_path[-1]["t"]

    current_time = start_time
    while current_time <= end_time:
        velocity = calculate_mouse_velocity(mouse_path, current_time)

        # Find nearest position for coordinates
        nearest = min(mouse_path, key=lambda p: abs(p["t"] - current_time))

        velocities.append({
            "t": current_time,
            "velocity": velocity,
            "x": nearest["x"],
            "y": nearest["y"]
        })
        current_time += sample_interval

    return velocities


def is_during_scroll(events: List[dict], time: float) -> bool:
    """Check if time falls within a scroll event."""
    for i, event in enumerate(events):
        if event["type"] == "scroll_start":
            # Find matching scroll_end
            for j in range(i + 1, len(events)):
                if events[j]["type"] == "scroll_end":
                    if event["timestamp"] <= time <= events[j]["timestamp"]:
                        return True
                    break
    return False


def should_trigger_zoom(
    click: dict,
    mouse_path: List[dict],
    events: List[dict],
    config: ZoomTriggerConfig,
) -> bool:
    """Determine if zoom should be triggered for a click event.

    Uses mouse velocity analysis to make intelligent zoom decisions.

    Args:
        click: Click event {type, timestamp, x, y, label}
        mouse_path: List of mouse positions from recording
        events: All events from recording
        config: Trigger configuration

    Returns:
        True if zoom should be triggered
    """
    click_time = click["timestamp"]

    # Always trigger for explicit click triggers
    if 'click' in config.triggers and click["type"] == "click":
        # Check if we should skip during scroll
        if config.skip_during_scroll and is_during_scroll(events, click_time):
            return False

        # Check mouse velocity if slow_down trigger is enabled
        if 'slow_down' in config.triggers and mouse_path:
            velocity = calculate_mouse_velocity(mouse_path, click_time)
            if velocity > config.velocity_threshold * 3:  # Very fast = skip zoom
                return False

        return True

    # Trigger based on slow-down (hover detection)
    if 'slow_down' in config.triggers and mouse_path:
        velocity = calculate_mouse_velocity(mouse_path, click_time)
        if velocity < config.velocity_threshold:
            return True

    return False


def filter_zoom_triggers(
    events: List[dict],
    mouse_path: List[dict],
    config: Optional[ZoomTriggerConfig] = None,
) -> List[dict]:
    """Filter click events to only include those that should trigger zoom.

    Args:
        events: All events from recording
        mouse_path: Mouse position tracking data
        config: Trigger configuration (uses defaults if None)

    Returns:
        Filtered list of click events that should trigger zoom
    """
    if config is None:
        config = ZoomTriggerConfig()

    clicks = [e for e in events if e["type"] == "click"]
    filtered = []

    for click in clicks:
        if should_trigger_zoom(click, mouse_path, events, config):
            filtered.append(click)
        else:
            print(f"  ⊘ Skipping zoom for '{click['label']}' (velocity too high or during scroll)")

    return filtered


def ease_out_cubic(t: float) -> float:
    """Ease-out cubic for smooth zoom-in (fast start, slow end)."""
    return 1 - pow(1 - t, 3)


def ease_in_cubic(t: float) -> float:
    """Ease-in cubic for smooth zoom-out (slow start, fast end)."""
    return t * t * t


def interpolate_zoom(t: float, start_zoom: float, end_zoom: float, easing_fn) -> float:
    """Interpolate zoom level with easing."""
    eased_t = easing_fn(t)
    return start_zoom + (end_zoom - start_zoom) * eased_t


# =============================================================================
# ZOOM-003: Mouse-following pan during zoom
# =============================================================================

def interpolate_mouse_position(
    mouse_path: List[dict],
    time: float,
) -> tuple:
    """Interpolate mouse position at a specific time.

    Args:
        mouse_path: List of {t, x, y} position records
        time: Time to interpolate position at

    Returns:
        (x, y) tuple of interpolated position
    """
    if not mouse_path:
        return (0, 0)

    # Handle edge cases
    if time <= mouse_path[0]["t"]:
        return (mouse_path[0]["x"], mouse_path[0]["y"])
    if time >= mouse_path[-1]["t"]:
        return (mouse_path[-1]["x"], mouse_path[-1]["y"])

    # Find surrounding positions for interpolation
    for i in range(len(mouse_path) - 1):
        p1 = mouse_path[i]
        p2 = mouse_path[i + 1]
        if p1["t"] <= time <= p2["t"]:
            # Linear interpolation between points
            dt = p2["t"] - p1["t"]
            if dt < 0.001:
                return (p1["x"], p1["y"])
            t = (time - p1["t"]) / dt
            x = p1["x"] + (p2["x"] - p1["x"]) * t
            y = p1["y"] + (p2["y"] - p1["y"]) * t
            return (x, y)

    return (mouse_path[-1]["x"], mouse_path[-1]["y"])


def smooth_mouse_path(
    mouse_path: List[dict],
    window_size: int = 5,
) -> List[dict]:
    """Smooth mouse path using moving average to reduce jitter.

    Args:
        mouse_path: List of {t, x, y} position records
        window_size: Number of samples for moving average

    Returns:
        Smoothed mouse path
    """
    if not mouse_path or len(mouse_path) < window_size:
        return mouse_path

    smoothed = []
    half_window = window_size // 2

    for i in range(len(mouse_path)):
        # Gather samples within window
        start_idx = max(0, i - half_window)
        end_idx = min(len(mouse_path), i + half_window + 1)
        window = mouse_path[start_idx:end_idx]

        # Calculate average position
        avg_x = sum(p["x"] for p in window) / len(window)
        avg_y = sum(p["y"] for p in window) / len(window)

        smoothed.append({
            "t": mouse_path[i]["t"],
            "x": avg_x,
            "y": avg_y
        })

    return smoothed


def calculate_pan_offset(
    mouse_x: float,
    mouse_y: float,
    zoom_factor: float,
    viewport_width: int,
    viewport_height: int,
) -> tuple:
    """Calculate pan offset to keep cursor centered during zoom.

    Args:
        mouse_x: Current mouse X position
        mouse_y: Current mouse Y position
        zoom_factor: Current zoom level
        viewport_width: Video width
        viewport_height: Video height

    Returns:
        (pan_x, pan_y) normalized offset (0-1)
    """
    # Calculate crop dimensions at current zoom
    crop_w = viewport_width / zoom_factor
    crop_h = viewport_height / zoom_factor

    # Calculate ideal crop position to center on mouse
    ideal_x = mouse_x - crop_w / 2
    ideal_y = mouse_y - crop_h / 2

    # Clamp to valid range
    ideal_x = max(0, min(ideal_x, viewport_width - crop_w))
    ideal_y = max(0, min(ideal_y, viewport_height - crop_h))

    # Convert to normalized coordinates
    max_offset_x = viewport_width - crop_w
    max_offset_y = viewport_height - crop_h

    pan_x = ideal_x / max_offset_x if max_offset_x > 0 else 0.5
    pan_y = ideal_y / max_offset_y if max_offset_y > 0 else 0.5

    return (pan_x, pan_y)


def generate_zoom_keyframes(
    click_time: float,
    center_x: float,
    center_y: float,
    zoom_factor: float,
    zoom_in_duration: float = 0.3,
    hold_duration: float = 0.5,
    zoom_out_duration: float = 0.3,
    fps: float = 30,
    mouse_path: Optional[List[dict]] = None,
    viewport_width: int = 1280,
    viewport_height: int = 800,
    follow_mouse: bool = False,
) -> List[ZoomKeyframe]:
    """Generate keyframes for smooth zoom animation with optional mouse following.

    Args:
        click_time: Timestamp of click event
        center_x: Initial center X (0-1 normalized)
        center_y: Initial center Y (0-1 normalized)
        zoom_factor: Maximum zoom level
        zoom_in_duration: Duration of zoom-in phase
        hold_duration: Duration at max zoom
        zoom_out_duration: Duration of zoom-out phase
        fps: Frames per second
        mouse_path: Optional mouse tracking data for pan following
        viewport_width: Video width for pan calculations
        viewport_height: Video height for pan calculations
        follow_mouse: Enable mouse-following pan during zoom
    """
    keyframes = []

    # Pre-zoom offset (start zoom slightly before click)
    pre_offset = 0.1
    zoom_start = click_time - pre_offset

    # Smooth the mouse path if available
    smoothed_path = None
    if follow_mouse and mouse_path:
        smoothed_path = smooth_mouse_path(mouse_path, window_size=5)

    def get_pan_center(frame_time: float, zoom: float) -> tuple:
        """Get pan center position, following mouse if enabled."""
        if not follow_mouse or not smoothed_path:
            return (center_x, center_y)

        # Get interpolated mouse position at this time
        mouse_x, mouse_y = interpolate_mouse_position(smoothed_path, frame_time)

        # Calculate pan offset to keep cursor centered
        pan_x, pan_y = calculate_pan_offset(
            mouse_x, mouse_y, zoom, viewport_width, viewport_height
        )
        return (pan_x, pan_y)

    # Phase 1: Zoom in
    zoom_in_frames = int(zoom_in_duration * fps)
    for i in range(zoom_in_frames):
        t = i / zoom_in_frames
        frame_time = zoom_start + t * zoom_in_duration
        zoom = interpolate_zoom(t, 1.0, zoom_factor, ease_out_cubic)
        pan_x, pan_y = get_pan_center(frame_time, zoom)
        keyframes.append(ZoomKeyframe(frame_time, zoom, pan_x, pan_y))

    # Phase 2: Hold at max zoom (follow mouse during hold)
    hold_frames = int(hold_duration * fps)
    hold_start = zoom_start + zoom_in_duration
    for i in range(hold_frames):
        frame_time = hold_start + i / fps
        pan_x, pan_y = get_pan_center(frame_time, zoom_factor)
        keyframes.append(ZoomKeyframe(frame_time, zoom_factor, pan_x, pan_y))

    # Phase 3: Zoom out
    zoom_out_frames = int(zoom_out_duration * fps)
    zoom_out_start = hold_start + hold_duration
    for i in range(zoom_out_frames):
        t = i / zoom_out_frames
        frame_time = zoom_out_start + t * zoom_out_duration
        zoom = interpolate_zoom(t, zoom_factor, 1.0, ease_in_cubic)
        pan_x, pan_y = get_pan_center(frame_time, zoom)
        keyframes.append(ZoomKeyframe(frame_time, zoom, pan_x, pan_y))

    return keyframes


def create_animated_zoom_segment(
    input_video: str,
    output_video: str,
    keyframes: List[ZoomKeyframe],
    width: int,
    height: int,
    fps: float,
) -> bool:
    """Create a segment with animated zoom using multiple micro-segments."""
    if not keyframes:
        return False

    temp_dir = Path(tempfile.mkdtemp())
    segments = []

    # Group keyframes into small chunks (every 3-5 frames) for smoother animation
    chunk_size = 3  # Process 3 frames at a time

    for i in range(0, len(keyframes), chunk_size):
        chunk = keyframes[i:i + chunk_size]
        if not chunk:
            continue

        # Use middle keyframe's parameters for this chunk
        mid_kf = chunk[len(chunk) // 2]
        start_time = chunk[0].time
        end_time = chunk[-1].time + (1 / fps)  # Add one frame duration
        duration = end_time - start_time

        if duration <= 0:
            continue

        # Calculate crop parameters for this chunk's zoom level
        crop_w = int(width / mid_kf.zoom)
        crop_h = int(height / mid_kf.zoom)

        # Center on the click point
        crop_x = int((width - crop_w) * mid_kf.center_x)
        crop_y = int((height - crop_h) * mid_kf.center_y)

        # Clamp to valid range
        crop_x = max(0, min(crop_x, width - crop_w))
        crop_y = max(0, min(crop_y, height - crop_h))

        # Make dimensions even
        crop_w = crop_w - (crop_w % 2)
        crop_h = crop_h - (crop_h % 2)

        seg_file = temp_dir / f"chunk_{i:04d}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", input_video,
            "-t", str(duration),
            "-vf", f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={width}:{height}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            str(seg_file)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if seg_file.exists() and seg_file.stat().st_size > 0:
            segments.append(seg_file)

    if not segments:
        return False

    # Concatenate all chunks
    concat_file = temp_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        output_video
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Cleanup
    for seg in segments:
        seg.unlink()
    concat_file.unlink()
    temp_dir.rmdir()

    return result.returncode == 0


def load_events(events_path: str) -> dict:
    with open(events_path) as f:
        return json.load(f)


# =============================================================================
# ZOOM-006: Frame-by-frame rendering for precise control
# =============================================================================

def extract_frames(
    input_video: str,
    output_dir: Path,
    fps: Optional[float] = None,
) -> int:
    """Extract all frames from video to PNG files.

    Args:
        input_video: Path to input video
        output_dir: Directory to save frames
        fps: Optional frame rate (uses video's native fps if not specified)

    Returns:
        Number of frames extracted
    """
    output_dir.mkdir(exist_ok=True)

    fps_filter = f"fps={fps}" if fps else "copy"
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", fps_filter,
        str(output_dir / "frame_%06d.png")
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Count extracted frames
    frames = list(output_dir.glob("frame_*.png"))
    return len(frames)


def process_single_frame(args: tuple) -> bool:
    """Process a single frame with zoom/crop transformation.

    Args:
        args: Tuple of (frame_path, output_path, crop_x, crop_y, crop_w, crop_h, width, height)

    Returns:
        True if successful
    """
    frame_path, output_path, crop_x, crop_y, crop_w, crop_h, width, height = args

    cmd = [
        "ffmpeg", "-y",
        "-i", str(frame_path),
        "-vf", f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={width}:{height}",
        "-q:v", "2",  # High quality JPEG
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def reassemble_frames(
    frames_dir: Path,
    output_video: str,
    fps: float,
    width: int,
    height: int,
) -> bool:
    """Reassemble processed frames into final video.

    Args:
        frames_dir: Directory containing processed frames
        output_video: Output video path
        fps: Frame rate
        width: Video width
        height: Video height

    Returns:
        True if successful
    """
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "processed_%06d.png"),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-s", f"{width}x{height}",
        output_video
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def calculate_frame_transform(
    frame_num: int,
    fps: float,
    keyframes: List[ZoomKeyframe],
    width: int,
    height: int,
) -> tuple:
    """Calculate crop transformation for a specific frame.

    Args:
        frame_num: Frame number (0-indexed)
        fps: Video frame rate
        keyframes: Zoom keyframes
        width: Video width
        height: Video height

    Returns:
        (crop_x, crop_y, crop_w, crop_h) for this frame
    """
    frame_time = frame_num / fps

    # Find the keyframe or interpolate between keyframes
    zoom = 1.0
    center_x = 0.5
    center_y = 0.5

    if keyframes:
        # Check if before first keyframe
        if frame_time <= keyframes[0].time:
            zoom = keyframes[0].zoom
            center_x = keyframes[0].center_x
            center_y = keyframes[0].center_y
        # Check if after last keyframe
        elif frame_time >= keyframes[-1].time:
            zoom = keyframes[-1].zoom
            center_x = keyframes[-1].center_x
            center_y = keyframes[-1].center_y
        else:
            # Interpolate between keyframes
            for i in range(len(keyframes) - 1):
                kf1 = keyframes[i]
                kf2 = keyframes[i + 1]
                if kf1.time <= frame_time <= kf2.time:
                    dt = kf2.time - kf1.time
                    if dt > 0:
                        t = (frame_time - kf1.time) / dt
                        zoom = kf1.zoom + (kf2.zoom - kf1.zoom) * t
                        center_x = kf1.center_x + (kf2.center_x - kf1.center_x) * t
                        center_y = kf1.center_y + (kf2.center_y - kf1.center_y) * t
                    else:
                        zoom = kf1.zoom
                        center_x = kf1.center_x
                        center_y = kf1.center_y
                    break

    # Calculate crop dimensions
    crop_w = int(width / zoom)
    crop_h = int(height / zoom)

    # Calculate crop position centered on the click point
    crop_x = int((width - crop_w) * center_x)
    crop_y = int((height - crop_h) * center_y)

    # Clamp to valid range
    crop_x = max(0, min(crop_x, width - crop_w))
    crop_y = max(0, min(crop_y, height - crop_h))

    # Make dimensions even
    crop_w = crop_w - (crop_w % 2)
    crop_h = crop_h - (crop_h % 2)

    return (crop_x, crop_y, crop_w, crop_h)


def render_zoom_frame_by_frame(
    input_video: str,
    output_video: str,
    keyframes: List[ZoomKeyframe],
    width: int,
    height: int,
    fps: float,
    parallel: bool = True,
    max_workers: int = 4,
) -> bool:
    """Render zoom effect frame-by-frame for precise control.

    This is a fallback method when FFmpeg filter expressions are insufficient.
    It provides exact per-frame zoom and pan control at the cost of speed.

    Args:
        input_video: Path to input video
        output_video: Path to output video
        keyframes: List of zoom keyframes
        width: Video width
        height: Video height
        fps: Video frame rate
        parallel: Use parallel processing
        max_workers: Number of parallel workers

    Returns:
        True if successful
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    temp_dir = Path(tempfile.mkdtemp())
    frames_dir = temp_dir / "frames"
    processed_dir = temp_dir / "processed"
    frames_dir.mkdir()
    processed_dir.mkdir()

    print(f"  Extracting frames from {input_video}...")
    num_frames = extract_frames(input_video, frames_dir, fps)
    print(f"  Extracted {num_frames} frames")

    if num_frames == 0:
        print("  Error: No frames extracted")
        return False

    # Prepare frame processing arguments
    frame_args = []
    for i in range(1, num_frames + 1):
        frame_path = frames_dir / f"frame_{i:06d}.png"
        output_path = processed_dir / f"processed_{i:06d}.png"

        crop_x, crop_y, crop_w, crop_h = calculate_frame_transform(
            i - 1, fps, keyframes, width, height
        )

        frame_args.append((
            frame_path, output_path,
            crop_x, crop_y, crop_w, crop_h,
            width, height
        ))

    # Process frames
    print(f"  Processing {num_frames} frames...")
    processed = 0

    if parallel:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_single_frame, args): i for i, args in enumerate(frame_args)}
            for future in as_completed(futures):
                if future.result():
                    processed += 1
                if processed % 100 == 0:
                    print(f"    Processed {processed}/{num_frames} frames...")
    else:
        for args in frame_args:
            if process_single_frame(args):
                processed += 1
            if processed % 100 == 0:
                print(f"    Processed {processed}/{num_frames} frames...")

    print(f"  Processed {processed}/{num_frames} frames")

    # Reassemble video
    print(f"  Reassembling video...")
    success = reassemble_frames(processed_dir, output_video, fps, width, height)

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

    if success:
        size_mb = Path(output_video).stat().st_size / (1024 * 1024)
        print(f"  ✓ Frame-by-frame output: {output_video} ({size_mb:.1f} MB)")
        return True
    else:
        print("  ✗ Failed to reassemble video")
        return False


def get_video_info(video_path: str) -> dict:
    """Get video duration and fps."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=duration,r_frame_rate,width,height",
        "-show_entries", "format=duration",
        "-of", "json",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)

    # Parse frame rate
    fps_str = data.get("streams", [{}])[0].get("r_frame_rate", "30/1")
    fps_parts = fps_str.split("/")
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30

    duration = float(data.get("format", {}).get("duration", 10))

    return {"duration": duration, "fps": fps}


def create_zoom_segment(
    input_video: str,
    output_video: str,
    start_time: float,
    end_time: float,
    zoom_center_x: float,  # 0-1
    zoom_center_y: float,  # 0-1
    zoom_factor: float,
    width: int,
    height: int,
):
    """Create a zoomed segment using crop+scale."""

    # Calculate crop dimensions
    crop_w = int(width / zoom_factor)
    crop_h = int(height / zoom_factor)

    # Calculate crop position centered on the click point
    crop_x = int((width - crop_w) * zoom_center_x)
    crop_y = int((height - crop_h) * zoom_center_y)

    # Clamp to valid range
    crop_x = max(0, min(crop_x, width - crop_w))
    crop_y = max(0, min(crop_y, height - crop_h))

    # Make dimensions even (required by libx264)
    crop_w = crop_w - (crop_w % 2)
    crop_h = crop_h - (crop_h % 2)

    duration = end_time - start_time

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", input_video,
        "-t", str(duration),
        "-vf", f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={width}:{height}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        output_video
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def apply_zoom_at_clicks(
    input_video: str,
    output_video: str,
    events: list,
    viewport: dict,
    zoom_factor: float = 1.5,
    zoom_duration: float = 1.0,
    animated: bool = True,
    smart_triggers: bool = False,
    mouse_path: Optional[List[dict]] = None,
    trigger_config: Optional[ZoomTriggerConfig] = None,
    follow_mouse: bool = False,
    frame_by_frame: bool = False,
):
    """Apply zoom effects with smooth animated transitions.

    Args:
        input_video: Path to input video file
        output_video: Path to output video file
        events: List of events from events.json
        viewport: Viewport dimensions {width, height}
        zoom_factor: Maximum zoom level (1.5 = 50% zoom)
        zoom_duration: Total duration of zoom effect
        animated: Use smooth animated transitions (True) or hard cuts (False)
        smart_triggers: Use intelligent zoom trigger detection (ZOOM-004)
        mouse_path: Mouse position tracking data for smart triggers
        trigger_config: Configuration for smart trigger detection
        follow_mouse: Enable mouse-following pan during zoom (ZOOM-003)
        frame_by_frame: Use frame-by-frame rendering for precise control (ZOOM-006)
    """
    width = viewport["width"]
    height = viewport["height"]

    # Get clicks and optionally filter with smart triggers
    clicks = [e for e in events if e["type"] == "click"]

    if smart_triggers and mouse_path:
        print(f"\nAnalyzing mouse velocity for smart zoom triggers...")
        clicks = filter_zoom_triggers(events, mouse_path, trigger_config)
        if not clicks:
            print("No zoom triggers detected after velocity analysis!")
            return False
    elif not clicks:
        print("No click events found!")
        return False

    mode = "animated" if animated else "hard-cut"
    if frame_by_frame:
        mode = "frame-by-frame"
    trigger_mode = " (smart triggers)" if smart_triggers else ""
    pan_mode = " + mouse-following" if follow_mouse and mouse_path else ""
    print(f"\nApplying {zoom_factor}x {mode} zoom at {len(clicks)} click points{trigger_mode}{pan_mode}...")

    info = get_video_info(input_video)
    total_duration = info["duration"]
    fps = info["fps"]

    # Create temp directory for segments
    temp_dir = Path(tempfile.mkdtemp())
    segments = []
    concat_file = temp_dir / "concat.txt"

    # Calculate zoom timing parameters
    if animated:
        # Animated: zoom_in (30%), hold (40%), zoom_out (30%)
        zoom_in_dur = zoom_duration * 0.3
        hold_dur = zoom_duration * 0.4
        zoom_out_dur = zoom_duration * 0.3
    else:
        # Hard cut: instant zoom for full duration
        zoom_in_dur = 0
        hold_dur = zoom_duration
        zoom_out_dur = 0

    # Build timeline with zoomed segments
    current_time = 0
    segment_idx = 0

    for click in clicks:
        click_time = click["timestamp"]
        pre_offset = 0.1
        zoom_start = click_time - pre_offset
        zoom_end = zoom_start + zoom_in_dur + hold_dur + zoom_out_dur

        # Segment before zoom (normal)
        if current_time < zoom_start:
            seg_file = temp_dir / f"seg_{segment_idx:03d}_normal.mp4"
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(current_time),
                "-i", input_video,
                "-t", str(zoom_start - current_time),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                str(seg_file)
            ]
            subprocess.run(cmd, capture_output=True)
            if seg_file.exists() and seg_file.stat().st_size > 0:
                segments.append(seg_file)
                segment_idx += 1

        # Zoomed segment
        px = click["x"] / width
        py = click["y"] / height
        actual_end = min(zoom_end, total_duration)

        if animated:
            # Generate keyframes for smooth animation with optional mouse following
            keyframes = generate_zoom_keyframes(
                click_time=click_time,
                center_x=px,
                center_y=py,
                zoom_factor=zoom_factor,
                zoom_in_duration=zoom_in_dur,
                hold_duration=hold_dur,
                zoom_out_duration=zoom_out_dur,
                fps=fps,
                mouse_path=mouse_path,
                viewport_width=width,
                viewport_height=height,
                follow_mouse=follow_mouse,
            )

            # Create zoom segment using chosen method
            seg_file = temp_dir / f"seg_{segment_idx:03d}_zoom_animated.mp4"

            if frame_by_frame:
                # ZOOM-006: Frame-by-frame rendering for precise control
                print(f"  → Frame-by-frame rendering: {click['label']}...")
                success = render_zoom_frame_by_frame(
                    input_video, str(seg_file), keyframes, width, height, fps
                )
            else:
                # Default: segment-based animated zoom
                success = create_animated_zoom_segment(
                    input_video, str(seg_file), keyframes, width, height, fps
                )

            if success and seg_file.exists() and seg_file.stat().st_size > 0:
                segments.append(seg_file)
                method = "frame-by-frame" if frame_by_frame else "animated"
                print(f"  ✓ {method.capitalize()} zoom: {click['label']} ({zoom_start:.2f}s - {actual_end:.2f}s)")
                segment_idx += 1
        else:
            # Hard cut zoom (original behavior)
            seg_file = temp_dir / f"seg_{segment_idx:03d}_zoom.mp4"
            crop_w = int(width / zoom_factor)
            crop_h = int(height / zoom_factor)
            crop_x = max(0, min(int((width - crop_w) * px), width - crop_w))
            crop_y = max(0, min(int((height - crop_h) * py), height - crop_h))
            crop_w = crop_w - (crop_w % 2)
            crop_h = crop_h - (crop_h % 2)

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(zoom_start),
                "-i", input_video,
                "-t", str(actual_end - zoom_start),
                "-vf", f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={width}:{height}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                str(seg_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if seg_file.exists() and seg_file.stat().st_size > 0:
                segments.append(seg_file)
                print(f"  ✓ Zoom segment: {click['label']} ({zoom_start:.2f}s - {actual_end:.2f}s)")
                segment_idx += 1

        current_time = actual_end

    # Final segment after last zoom
    if current_time < total_duration:
        seg_file = temp_dir / f"seg_{segment_idx:03d}_normal.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(current_time),
            "-i", input_video,
            "-t", str(total_duration - current_time),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            str(seg_file)
        ]
        subprocess.run(cmd, capture_output=True)
        if seg_file.exists() and seg_file.stat().st_size > 0:
            segments.append(seg_file)

    # Write concat file
    with open(concat_file, "w") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")

    # Concatenate all segments
    print(f"\nConcatenating {len(segments)} segments...")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        output_video
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Cleanup
    for seg in segments:
        seg.unlink()
    concat_file.unlink()
    temp_dir.rmdir()

    if result.returncode == 0:
        size_mb = Path(output_video).stat().st_size / (1024 * 1024)
        print(f"✓ Output: {output_video} ({size_mb:.1f} MB)")
        return True
    else:
        print(f"✗ Error: {result.stderr[-300:]}")
        return False


def create_zoom_versions(
    recording_dir: str,
    animated: bool = True,
    smart_triggers: bool = False,
    trigger_config: Optional[ZoomTriggerConfig] = None,
    follow_mouse: bool = False,
    frame_by_frame: bool = False,
):
    """Create multiple versions with different zoom levels.

    Args:
        recording_dir: Path to recording directory containing video and events.json
        animated: Use smooth animated zoom transitions (True) or hard cuts (False)
        smart_triggers: Use intelligent zoom trigger detection (ZOOM-004)
        trigger_config: Configuration for smart trigger detection
        follow_mouse: Enable mouse-following pan during zoom (ZOOM-003)
        frame_by_frame: Use frame-by-frame rendering for precise control (ZOOM-006)
    """
    recording_dir = Path(recording_dir)
    events_file = recording_dir / "events.json"

    video_files = list(recording_dir.glob("*.webm"))
    if not video_files:
        print("No video file found!")
        return

    input_video = str(video_files[0])
    events_data = load_events(str(events_file))

    mode_label = "Frame-by-Frame" if frame_by_frame else ("Smooth Animated" if animated else "Hard Cut")
    trigger_label = " + Smart Triggers" if smart_triggers else ""
    pan_label = " + Mouse Following" if follow_mouse else ""
    print("=" * 60)
    print(f"POST-PROCESSING - {mode_label} Zoom Effects{trigger_label}{pan_label}")
    print("=" * 60)
    print(f"Input: {input_video}")
    print(f"Viewport: {events_data['viewport']}")

    # Check for mouse_path data
    mouse_path = events_data.get("mouse_path", [])
    if mouse_path:
        print(f"Mouse tracking: {len(mouse_path)} positions (~30fps)")
        if smart_triggers:
            # Analyze and show velocity stats
            velocities = analyze_mouse_velocity(mouse_path)
            if velocities:
                avg_vel = sum(v["velocity"] for v in velocities) / len(velocities)
                max_vel = max(v["velocity"] for v in velocities)
                print(f"Velocity analysis: avg={avg_vel:.1f} px/s, max={max_vel:.1f} px/s")
    else:
        print("Mouse tracking: Not available (record with ZOOM-001 for best results)")
        if smart_triggers:
            print("  Warning: Smart triggers require mouse tracking data")
            smart_triggers = False
        if follow_mouse:
            print("  Warning: Mouse following requires mouse tracking data")
            follow_mouse = False

    clicks = [e for e in events_data["events"] if e["type"] == "click"]
    print(f"Click events: {len(clicks)}")
    for c in clicks:
        print(f"  - {c['label']} at ({c['x']}, {c['y']}) @ {c['timestamp']:.2f}s")

    # Version 1: Subtle zoom
    print("\n" + "-" * 40)
    print(f"VERSION 1: Subtle {mode_label} Zoom (1.3x)")
    print("-" * 40)
    apply_zoom_at_clicks(
        input_video,
        str(recording_dir / "v1_subtle_zoom.mp4"),
        events_data["events"],
        events_data["viewport"],
        zoom_factor=1.3,
        zoom_duration=0.8,
        animated=animated,
        smart_triggers=smart_triggers,
        mouse_path=mouse_path,
        trigger_config=trigger_config,
        follow_mouse=follow_mouse,
        frame_by_frame=frame_by_frame,
    )

    # Version 2: Medium zoom
    print("\n" + "-" * 40)
    print(f"VERSION 2: Medium {mode_label} Zoom (1.5x)")
    print("-" * 40)
    apply_zoom_at_clicks(
        input_video,
        str(recording_dir / "v2_medium_zoom.mp4"),
        events_data["events"],
        events_data["viewport"],
        zoom_factor=1.5,
        zoom_duration=1.0,
        animated=animated,
        smart_triggers=smart_triggers,
        mouse_path=mouse_path,
        trigger_config=trigger_config,
        follow_mouse=follow_mouse,
        frame_by_frame=frame_by_frame,
    )

    # Version 3: Dramatic zoom
    print("\n" + "-" * 40)
    print(f"VERSION 3: Dramatic {mode_label} Zoom (2.0x)")
    print("-" * 40)
    apply_zoom_at_clicks(
        input_video,
        str(recording_dir / "v3_dramatic_zoom.mp4"),
        events_data["events"],
        events_data["viewport"],
        zoom_factor=2.0,
        zoom_duration=1.2,
        animated=animated,
        smart_triggers=smart_triggers,
        mouse_path=mouse_path,
        trigger_config=trigger_config,
        follow_mouse=follow_mouse,
        frame_by_frame=frame_by_frame,
    )

    print("\n" + "=" * 60)
    print("POST-PROCESSING COMPLETE")
    print("=" * 60)
    print(f"\nOutput files:")
    for f in sorted(recording_dir.glob("v*.mp4")):
        if f.stat().st_size > 0:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  - {f.name} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    recordings_dir = Path("./recordings")
    recording_dirs = sorted(recordings_dir.glob("stripe_demo_*"), reverse=True)

    if recording_dirs:
        latest = recording_dirs[0]
        print(f"Using latest recording: {latest}")
        create_zoom_versions(str(latest))
    else:
        print("No recordings found!")
