"""Terminal control using tmux."""

import re
import subprocess
import time
from typing import Any

from programmatic_demo.utils.output import error_response, success_response

# Regex to strip ANSI escape codes
ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


class Terminal:
    """Terminal controller using tmux for session management."""

    def __init__(self) -> None:
        """Initialize the terminal controller."""
        self._session_name: str | None = None

    def _run_tmux(self, *args: str) -> tuple[int, str, str]:
        """Run a tmux command and return (returncode, stdout, stderr)."""
        cmd = ["tmux"] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    def _session_exists(self) -> bool:
        """Check if the current session exists."""
        if not self._session_name:
            return False
        code, _, _ = self._run_tmux("has-session", "-t", self._session_name)
        return code == 0

    def launch(self, name: str | None = None) -> dict[str, Any]:
        """Launch a new tmux session.

        Args:
            name: Session name. If None, generates one with timestamp.

        Returns:
            Success dict with session_name, or error dict.
        """
        # Generate session name if not provided
        if name is None:
            name = f"pdemo-{int(time.time())}"

        # Check if session already exists
        code, _, _ = self._run_tmux("has-session", "-t", name)
        if code == 0:
            # Session exists, just use it
            self._session_name = name
            return success_response("terminal_launch", {"session_name": name, "reused": True})

        # Create new detached session
        code, stdout, stderr = self._run_tmux("new-session", "-d", "-s", name)
        if code != 0:
            return error_response(
                "tmux_failed",
                f"Failed to create tmux session: {stderr}",
                recoverable=True,
                suggestion="Check that tmux is installed: brew install tmux",
            )

        # Verify session was created
        code, _, _ = self._run_tmux("has-session", "-t", name)
        if code != 0:
            return error_response(
                "session_not_created",
                "Session was not created successfully",
                recoverable=True,
            )

        self._session_name = name
        return success_response("terminal_launch", {"session_name": name, "reused": False})

    def send(self, text: str) -> dict[str, Any]:
        """Send text to the terminal without pressing Enter.

        Args:
            text: Text to send.

        Returns:
            Success dict.
        """
        if not self._session_exists():
            return error_response(
                "no_session",
                "No terminal session active",
                recoverable=True,
                suggestion="Launch a terminal first with 'pdemo terminal launch'",
            )

        # Escape special characters for tmux send-keys
        code, _, stderr = self._run_tmux("send-keys", "-t", self._session_name, text)
        if code != 0:
            return error_response("send_failed", f"Failed to send keys: {stderr}", recoverable=True)

        return success_response("terminal_send", {"text": text})

    def exec(self, command: str, timeout: int = 120) -> dict[str, Any]:
        """Execute a command and wait for completion.

        Args:
            command: Command to execute.
            timeout: Timeout in seconds.

        Returns:
            Success dict with output, or error dict on timeout.
        """
        if not self._session_exists():
            return error_response(
                "no_session",
                "No terminal session active",
                recoverable=True,
                suggestion="Launch a terminal first with 'pdemo terminal launch'",
            )

        # Send command with Enter key
        code, _, stderr = self._run_tmux(
            "send-keys", "-t", self._session_name, command, "Enter"
        )
        if code != 0:
            return error_response("exec_failed", f"Failed to execute: {stderr}", recoverable=True)

        # Wait for shell prompt to return (basic detection)
        # This polls for common prompt patterns like $, %, >, #, or zsh arrow
        start_time = time.time()
        prompt_patterns = ["$ ", "% ", "> ", "# ", "➜", "❯"]
        last_output = ""

        while time.time() - start_time < timeout:
            time.sleep(0.5)
            read_result = self.read(lines=50)
            if not read_result.get("success"):
                continue

            current_output = read_result.get("result", {}).get("output", "")

            # Check if output has stabilized and ends with a prompt
            if current_output == last_output and any(
                current_output.rstrip().endswith(p.strip()) for p in prompt_patterns
            ):
                return success_response("terminal_exec", {"command": command, "output": current_output})

            last_output = current_output

        return error_response(
            "timeout",
            f"Command timed out after {timeout}s",
            recoverable=True,
            suggestion="Increase timeout or check if command is stuck",
        )

    def read(self, lines: int = 50) -> dict[str, Any]:
        """Read terminal output.

        Args:
            lines: Number of lines to read.

        Returns:
            Success dict with output text.
        """
        if not self._session_exists():
            return error_response(
                "no_session",
                "No terminal session active",
                recoverable=True,
                suggestion="Launch a terminal first with 'pdemo terminal launch'",
            )

        # Capture pane contents
        code, stdout, stderr = self._run_tmux("capture-pane", "-t", self._session_name, "-p")
        if code != 0:
            return error_response("read_failed", f"Failed to read: {stderr}", recoverable=True)

        # Strip ANSI escape codes
        output = ANSI_ESCAPE.sub("", stdout)

        # Get last N lines
        output_lines = output.splitlines()
        if len(output_lines) > lines:
            output = "\n".join(output_lines[-lines:])

        return success_response("terminal_read", {"output": output, "lines": len(output_lines)})

    def wait_for(self, text: str, timeout: int = 30) -> dict[str, Any]:
        """Wait for text to appear in terminal.

        Args:
            text: Text to wait for.
            timeout: Timeout in seconds.

        Returns:
            Success dict when found, or error dict on timeout.
        """
        if not self._session_exists():
            return error_response(
                "no_session",
                "No terminal session active",
                recoverable=True,
                suggestion="Launch a terminal first with 'pdemo terminal launch'",
            )

        start_time = time.time()

        while time.time() - start_time < timeout:
            read_result = self.read(lines=100)
            if read_result.get("success"):
                output = read_result.get("result", {}).get("output", "")
                if text in output:
                    return success_response(
                        "terminal_wait_for",
                        {"text": text, "found": True, "elapsed": round(time.time() - start_time, 2)},
                    )
            time.sleep(0.5)

        return error_response(
            "timeout",
            f"Text '{text}' not found after {timeout}s",
            recoverable=True,
            suggestion="Check if the expected text is correct or increase timeout",
        )

    def clear(self) -> dict[str, Any]:
        """Clear the terminal screen.

        Returns:
            Success dict.
        """
        if not self._session_exists():
            return error_response(
                "no_session",
                "No terminal session active",
                recoverable=True,
                suggestion="Launch a terminal first with 'pdemo terminal launch'",
            )

        # Send Ctrl+L to clear screen
        code, _, stderr = self._run_tmux("send-keys", "-t", self._session_name, "C-l")
        if code != 0:
            return error_response("clear_failed", f"Failed to clear: {stderr}", recoverable=True)

        return success_response("terminal_clear", {})


# Singleton instance for CLI usage
_terminal_instance: Terminal | None = None


def get_terminal() -> Terminal:
    """Get or create the singleton Terminal instance."""
    global _terminal_instance
    if _terminal_instance is None:
        _terminal_instance = Terminal()
    return _terminal_instance
