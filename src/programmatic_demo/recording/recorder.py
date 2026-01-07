"""Screen recorder using ffmpeg."""

import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from programmatic_demo.utils.output import error_response, success_response

# State file for persisting recording info across CLI invocations
STATE_FILE = Path.home() / ".pdemo" / "recording.json"


class Recorder:
    """Screen recorder using ffmpeg with AVFoundation capture."""

    def __init__(self) -> None:
        """Initialize the recorder."""
        self._process: subprocess.Popen | None = None
        self._output_path: Path | None = None
        self._start_time: float | None = None
        self._pid: int | None = None
        # Try to restore state from file
        self._load_state()

    def _save_state(self) -> None:
        """Save recording state to file."""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "pid": self._pid,
            "output_path": str(self._output_path) if self._output_path else None,
            "start_time": self._start_time,
        }
        STATE_FILE.write_text(json.dumps(state))

    def _load_state(self) -> None:
        """Load recording state from file."""
        if not STATE_FILE.exists():
            return
        try:
            state = json.loads(STATE_FILE.read_text())
            self._pid = state.get("pid")
            self._output_path = Path(state["output_path"]) if state.get("output_path") else None
            self._start_time = state.get("start_time")
        except (json.JSONDecodeError, KeyError):
            self._clear_state()

    def _clear_state(self) -> None:
        """Clear saved state."""
        self._pid = None
        self._output_path = None
        self._start_time = None
        self._process = None
        if STATE_FILE.exists():
            STATE_FILE.unlink()

    def _is_recording_active(self) -> bool:
        """Check if a recording is currently active."""
        if self._pid is None:
            return False
        # Check if process is still running
        try:
            os.kill(self._pid, 0)  # Signal 0 just checks if process exists
            return True
        except OSError:
            # Process doesn't exist, clean up stale state
            self._clear_state()
            return False

    def start(self, output_path: str, fps: int = 30) -> dict[str, Any]:
        """Start screen recording.

        Args:
            output_path: Path to save the recording.
            fps: Frames per second (default 30, max supported by most screens).

        Returns:
            Success dict with pid and output_path, or error dict.
        """
        if self._is_recording_active():
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
        # Device "2" is typically "Capture screen 0", "none" for no audio
        # Device indices: 0=OBS Virtual Camera, 1=FaceTime, 2=Screen
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file
            "-f", "avfoundation",
            "-framerate", str(fps),
            "-capture_cursor", "1",  # Capture mouse cursor
            "-i", "2:none",  # Screen capture (device 2), no audio
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
                self._clear_state()
                return error_response(
                    "ffmpeg_failed",
                    f"FFmpeg failed to start: {stderr.decode()}",
                    recoverable=True,
                    suggestion="Check that ffmpeg is installed and screen recording permission is granted",
                )

            # Save state for persistence across CLI calls
            self._pid = self._process.pid
            self._save_state()

            return success_response(
                "record_start",
                {
                    "pid": self._pid,
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
        if not self._is_recording_active():
            return error_response(
                "not_recording",
                "No recording in progress",
                recoverable=True,
                suggestion="Start a recording first with 'pdemo record start'",
            )

        try:
            # Send SIGINT (Ctrl+C) to ffmpeg for graceful shutdown
            os.kill(self._pid, signal.SIGINT)

            # Wait for process to finish (poll up to 10 seconds)
            for _ in range(20):
                time.sleep(0.5)
                try:
                    os.kill(self._pid, 0)
                except OSError:
                    break  # Process has exited
            else:
                # Force kill if it doesn't respond
                try:
                    os.kill(self._pid, signal.SIGKILL)
                except OSError:
                    pass

            # Calculate duration
            duration = time.time() - self._start_time if self._start_time else 0

            # Get file size
            file_size = self._output_path.stat().st_size if self._output_path and self._output_path.exists() else 0

            result = {
                "file_path": str(self._output_path),
                "duration": round(duration, 2),
                "file_size": file_size,
            }

            # Clear persisted state
            self._clear_state()

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
        if not self._is_recording_active():
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
                "pid": self._pid,
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
