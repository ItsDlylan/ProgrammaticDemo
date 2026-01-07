"""Screen recorder using ffmpeg."""

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from programmatic_demo.utils.output import error_response, success_response


class Recorder:
    """Screen recorder using ffmpeg with AVFoundation capture."""

    def __init__(self) -> None:
        """Initialize the recorder."""
        self._process: subprocess.Popen | None = None
        self._output_path: Path | None = None
        self._start_time: float | None = None

    def start(self, output_path: str, fps: int = 60) -> dict[str, Any]:
        """Start screen recording.

        Args:
            output_path: Path to save the recording.
            fps: Frames per second (default 60).

        Returns:
            Success dict with pid and output_path, or error dict.
        """
        if self._process is not None and self._process.poll() is None:
            return error_response(
                "already_recording",
                "Recording is already in progress",
                recoverable=True,
                suggestion="Stop the current recording first with 'pdemo record stop'",
            )

        self._output_path = Path(output_path).resolve()

        # Create parent directories if needed
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build ffmpeg command for macOS AVFoundation capture
        # Device "1" is typically the main screen, "none" for no audio
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file
            "-f", "avfoundation",
            "-framerate", str(fps),
            "-i", "1:none",  # Screen capture, no audio
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            str(self._output_path),
        ]

        try:
            # Start ffmpeg as background process
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._start_time = time.time()

            # Give ffmpeg a moment to start
            time.sleep(0.5)

            # Check if it started successfully
            if self._process.poll() is not None:
                _, stderr = self._process.communicate()
                return error_response(
                    "ffmpeg_failed",
                    f"FFmpeg failed to start: {stderr.decode()}",
                    recoverable=True,
                    suggestion="Check that ffmpeg is installed and screen recording permission is granted",
                )

            return success_response(
                "record_start",
                {
                    "pid": self._process.pid,
                    "output_path": str(self._output_path),
                    "fps": fps,
                },
            )
        except FileNotFoundError:
            return error_response(
                "ffmpeg_not_found",
                "FFmpeg is not installed or not in PATH",
                recoverable=False,
                suggestion="Install ffmpeg with: brew install ffmpeg",
            )
        except Exception as e:
            return error_response(
                "start_failed",
                f"Failed to start recording: {str(e)}",
                recoverable=True,
            )

    def stop(self) -> dict[str, Any]:
        """Stop screen recording.

        Returns:
            Success dict with file_path and duration, or error dict.
        """
        if self._process is None or self._process.poll() is not None:
            return error_response(
                "not_recording",
                "No recording in progress",
                recoverable=True,
                suggestion="Start a recording first with 'pdemo record start'",
            )

        try:
            # Send SIGINT (Ctrl+C) to ffmpeg for graceful shutdown
            self._process.send_signal(signal.SIGINT)

            # Wait for process to finish (up to 10 seconds)
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't respond
                self._process.kill()
                self._process.wait()

            # Calculate duration
            duration = time.time() - self._start_time if self._start_time else 0

            # Get file size
            file_size = self._output_path.stat().st_size if self._output_path.exists() else 0

            result = {
                "file_path": str(self._output_path),
                "duration": round(duration, 2),
                "file_size": file_size,
            }

            # Clear state
            self._process = None
            self._start_time = None

            return success_response("record_stop", result)

        except Exception as e:
            return error_response(
                "stop_failed",
                f"Failed to stop recording: {str(e)}",
                recoverable=False,
            )

    def get_status(self) -> dict[str, Any]:
        """Get current recording status.

        Returns:
            Dict with active, duration, output_path, and pid.
        """
        if self._process is None or self._process.poll() is not None:
            return success_response(
                "record_status",
                {
                    "active": False,
                    "duration": None,
                    "output_path": None,
                    "pid": None,
                },
            )

        duration = time.time() - self._start_time if self._start_time else 0

        return success_response(
            "record_status",
            {
                "active": True,
                "duration": round(duration, 2),
                "output_path": str(self._output_path) if self._output_path else None,
                "pid": self._process.pid,
            },
        )


# Singleton instance for CLI usage
_recorder_instance: Recorder | None = None


def get_recorder() -> Recorder:
    """Get or create the singleton Recorder instance."""
    global _recorder_instance
    if _recorder_instance is None:
        _recorder_instance = Recorder()
    return _recorder_instance
