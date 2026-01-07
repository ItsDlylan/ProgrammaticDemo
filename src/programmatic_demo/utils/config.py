"""Configuration loading and settings management."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Config:
    """Configuration settings for ProgrammaticDemo."""

    # Recording defaults
    recording_fps: int = 60
    recording_output_dir: str = field(default_factory=lambda: str(Path.home() / ".pdemo" / "recordings"))

    # Terminal settings
    terminal_session_prefix: str = "pdemo"
    terminal_read_lines: int = 50

    # Mouse settings
    mouse_move_duration: float = 0.5
    mouse_bezier_smoothing: bool = True

    # Keyboard settings
    typing_delay_ms: int = 50
    typing_jitter: float = 0.3

    # Perception settings
    ocr_confidence_threshold: int = 50
    screenshot_format: str = "png"

    # Timeout defaults (seconds)
    wait_timeout: int = 30
    command_timeout: int = 120

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create Config from a dictionary, ignoring unknown keys."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


def load_config() -> Config:
    """Load configuration from file and environment.

    Loads settings in order of precedence (later overrides earlier):
    1. Default values
    2. ~/.pdemo/config.json (if exists)
    3. PDEMO_* environment variables

    Returns:
        Config object with merged settings.
    """
    config_data: dict[str, Any] = {}

    # Load from config file if it exists
    config_path = Path.home() / ".pdemo" / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass  # Use defaults if config is invalid

    # Override with environment variables
    env_mapping = {
        "PDEMO_RECORDING_FPS": ("recording_fps", int),
        "PDEMO_RECORDING_OUTPUT_DIR": ("recording_output_dir", str),
        "PDEMO_TERMINAL_SESSION_PREFIX": ("terminal_session_prefix", str),
        "PDEMO_TERMINAL_READ_LINES": ("terminal_read_lines", int),
        "PDEMO_MOUSE_MOVE_DURATION": ("mouse_move_duration", float),
        "PDEMO_TYPING_DELAY_MS": ("typing_delay_ms", int),
        "PDEMO_OCR_CONFIDENCE_THRESHOLD": ("ocr_confidence_threshold", int),
        "PDEMO_WAIT_TIMEOUT": ("wait_timeout", int),
        "PDEMO_COMMAND_TIMEOUT": ("command_timeout", int),
    }

    for env_var, (key, type_fn) in env_mapping.items():
        value = os.environ.get(env_var)
        if value is not None:
            try:
                config_data[key] = type_fn(value)
            except ValueError:
                pass  # Ignore invalid env values

    return Config.from_dict(config_data)
