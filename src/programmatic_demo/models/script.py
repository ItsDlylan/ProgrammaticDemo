"""Script data models for defining demo structure.

This module defines the core data structures used to represent demo scripts:
- ActionType: Types of actions (click, type, press, etc.)
- TargetType: Types of targets (screen, selector, coordinates, etc.)
- WaitCondition: Conditions to wait for after actions
- Target: Action target specification
- Step: Individual action step
- Scene: Collection of steps with narrative goal
- Script: Full demo script with metadata
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

class ActionType(Enum):
    """Types of actions that can be performed in a demo step."""

    CLICK = "click"
    TYPE = "type"
    PRESS = "press"
    SCROLL = "scroll"
    WAIT = "wait"
    NAVIGATE = "navigate"
    TERMINAL = "terminal"
    HOTKEY = "hotkey"
    DRAG = "drag"


class TargetType(Enum):
    """Types of targets for actions."""

    SCREEN = "screen"
    SELECTOR = "selector"
    COORDINATES = "coordinates"
    TEXT = "text"
    WINDOW = "window"


class WaitType(Enum):
    """Types of wait conditions."""

    TEXT = "text"
    ELEMENT = "element"
    TIMEOUT = "timeout"


@dataclass
class WaitCondition:
    """Condition to wait for after an action."""

    type: WaitType
    value: str | None = None
    timeout_seconds: float = 30.0


@dataclass
class Target:
    """Target specification for an action."""

    type: TargetType
    description: str | None = None
    selector: str | None = None
    coords: tuple[int, int] | None = None


@dataclass
class Step:
    """Individual action step in a scene."""

    action: ActionType
    target: Target | None = None
    wait_for: WaitCondition | None = None
    narration: str | None = None
    params: dict[str, Any] | None = None


class FailureStrategy(Enum):
    """Strategy for handling step failures in a scene."""

    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"


@dataclass
class Scene:
    """Collection of steps with a narrative goal."""

    name: str
    goal: str | None = None
    steps: list[Step] | None = None
    on_failure: FailureStrategy = FailureStrategy.ABORT


@dataclass
class Script:
    """Full demo script with metadata."""

    name: str
    description: str | None = None
    scenes: list[Scene] | None = None
    metadata: dict[str, Any] | None = None
