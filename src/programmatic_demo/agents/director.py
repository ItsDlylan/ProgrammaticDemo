"""Director agent for planning and orchestrating demo scenes.

The Director is responsible for:
- Planning scenes based on demo requirements
- Choosing actions based on current state/observations
- Reacting to observations and adjusting plans
- Coordinating with other agents (Observer, Editor)
"""

import base64
import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from PIL import Image


def compress_screenshot(
    image_data: bytes | str,
    max_size: int = 1568,
    quality: int = 85,
) -> str:
    """Compress a screenshot for efficient API transmission.

    Args:
        image_data: Raw image bytes or base64-encoded string.
        max_size: Maximum dimension on the longest side (default 1568px).
        quality: JPEG quality percentage (default 85%).

    Returns:
        Base64-encoded compressed JPEG image.
    """
    # Handle base64 input
    if isinstance(image_data, str):
        image_data = base64.b64decode(image_data)

    # Open image
    img = Image.open(io.BytesIO(image_data))

    # Convert to RGB if necessary (for PNG with alpha, etc.)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Resize if larger than max_size
    width, height = img.size
    if width > max_size or height > max_size:
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Compress to JPEG
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    buffer.seek(0)

    # Return as base64
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def observation_to_prompt(observation: dict[str, Any]) -> str:
    """Convert an observation dict to a human-readable prompt string.

    Args:
        observation: Observation dict containing screenshot, OCR, terminal output, etc.

    Returns:
        Formatted string suitable for inclusion in a prompt.
    """
    parts: list[str] = []

    # Timestamp
    if "timestamp" in observation:
        ts = observation["timestamp"]
        if isinstance(ts, (int, float)):
            ts_str = datetime.fromtimestamp(ts).isoformat()
        else:
            ts_str = str(ts)
        parts.append(f"**Timestamp:** {ts_str}")

    # Window information
    if "window" in observation and observation["window"]:
        window = observation["window"]
        window_info = []
        if "title" in window:
            window_info.append(f"Title: {window['title']}")
        if "app" in window:
            window_info.append(f"App: {window['app']}")
        if "bounds" in window:
            bounds = window["bounds"]
            window_info.append(f"Bounds: {bounds}")
        if window_info:
            parts.append("**Active Window:**\n" + "\n".join(f"  - {info}" for info in window_info))

    # OCR text
    if "ocr_text" in observation and observation["ocr_text"]:
        ocr_text = observation["ocr_text"].strip()
        if ocr_text:
            parts.append(f"**OCR Text:**\n```\n{ocr_text}\n```")

    # Terminal output
    if "terminal_output" in observation and observation["terminal_output"]:
        terminal = observation["terminal_output"].strip()
        if terminal:
            parts.append(f"**Terminal Output:**\n```\n{terminal}\n```")

    # Screenshot indicator (we don't include base64, just note it exists)
    if "screenshot_base64" in observation and observation["screenshot_base64"]:
        parts.append("**Screenshot:** [Image attached]")
    elif "screenshot_path" in observation and observation["screenshot_path"]:
        parts.append(f"**Screenshot:** {observation['screenshot_path']}")

    # Any additional context
    if "context" in observation and observation["context"]:
        parts.append(f"**Additional Context:**\n{observation['context']}")

    if not parts:
        return "No observation data available."

    return "\n\n".join(parts)


@dataclass
class ScenePlan:
    """A plan for executing a demo scene.

    Attributes:
        scene_name: Name/identifier of the scene
        goal: The narrative goal of the scene
        steps: Ordered list of action descriptions
        expected_state: Expected state after scene completion
    """

    scene_name: str
    goal: str
    steps: list[str] = field(default_factory=list)
    expected_state: dict[str, Any] = field(default_factory=dict)


class Director:
    """Director agent that plans and orchestrates demo scenes.

    The Director uses Claude to analyze requirements and observations,
    plan demo scenes, and decide on actions based on current state.
    """

    def __init__(self) -> None:
        """Initialize the Director agent."""
        self._current_plan: ScenePlan | None = None
        self._history: list[dict[str, Any]] = []

    def plan_scene(self, scene_description: str) -> ScenePlan:
        """Plan a scene based on description.

        Args:
            scene_description: Natural language description of the scene.

        Returns:
            ScenePlan with steps to execute the scene.
        """
        raise NotImplementedError("plan_scene not yet implemented")

    def next_action(self, observation: dict[str, Any]) -> dict[str, Any] | None:
        """Determine the next action based on observation.

        Args:
            observation: Current observation containing screenshot, OCR, etc.

        Returns:
            Action dict to execute, or None if scene is complete.
        """
        raise NotImplementedError("next_action not yet implemented")

    def handle_failure(
        self,
        action: dict[str, Any],
        error: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle an action failure and decide recovery strategy.

        Args:
            action: The action that failed.
            error: Error information from the failure.

        Returns:
            Recovery action to try, or None to abort.
        """
        raise NotImplementedError("handle_failure not yet implemented")

    def evaluate_progress(
        self,
        observation: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate progress toward scene goal.

        Args:
            observation: Current observation.

        Returns:
            Progress evaluation with completion status and confidence.
        """
        raise NotImplementedError("evaluate_progress not yet implemented")

    def reset(self) -> None:
        """Reset the Director state for a new demo."""
        self._current_plan = None
        self._history.clear()
