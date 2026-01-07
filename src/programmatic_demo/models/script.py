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

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WaitCondition":
        """Create WaitCondition from dictionary."""
        wait_type = data.get("type")
        if isinstance(wait_type, str):
            wait_type = WaitType(wait_type)
        return cls(
            type=wait_type,
            value=data.get("value"),
            timeout_seconds=data.get("timeout_seconds", 30.0),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert WaitCondition to dictionary."""
        result: dict[str, Any] = {"type": self.type.value}
        if self.value is not None:
            result["value"] = self.value
        if self.timeout_seconds != 30.0:
            result["timeout_seconds"] = self.timeout_seconds
        return result


@dataclass
class Target:
    """Target specification for an action."""

    type: TargetType
    description: str | None = None
    selector: str | None = None
    coords: tuple[int, int] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Target":
        """Create Target from dictionary."""
        target_type = data.get("type")
        if isinstance(target_type, str):
            target_type = TargetType(target_type)
        coords = data.get("coords")
        if coords is not None and isinstance(coords, (list, tuple)):
            coords = tuple(coords)
        return cls(
            type=target_type,
            description=data.get("description"),
            selector=data.get("selector"),
            coords=coords,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert Target to dictionary."""
        result: dict[str, Any] = {"type": self.type.value}
        if self.description is not None:
            result["description"] = self.description
        if self.selector is not None:
            result["selector"] = self.selector
        if self.coords is not None:
            result["coords"] = list(self.coords)
        return result


@dataclass
class Step:
    """Individual action step in a scene."""

    action: ActionType
    target: Target | None = None
    wait_for: WaitCondition | None = None
    narration: str | None = None
    params: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Step":
        """Create Step from dictionary."""
        action = data.get("action")
        if isinstance(action, str):
            action = ActionType(action)

        target_data = data.get("target")
        target = Target.from_dict(target_data) if target_data else None

        wait_for_data = data.get("wait_for")
        wait_for = WaitCondition.from_dict(wait_for_data) if wait_for_data else None

        return cls(
            action=action,
            target=target,
            wait_for=wait_for,
            narration=data.get("narration"),
            params=data.get("params"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert Step to dictionary."""
        result: dict[str, Any] = {"action": self.action.value}
        if self.target is not None:
            result["target"] = self.target.to_dict()
        if self.wait_for is not None:
            result["wait_for"] = self.wait_for.to_dict()
        if self.narration is not None:
            result["narration"] = self.narration
        if self.params is not None:
            result["params"] = self.params
        return result


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scene":
        """Create Scene from dictionary."""
        on_failure = data.get("on_failure", "abort")
        if isinstance(on_failure, str):
            on_failure = FailureStrategy(on_failure)

        steps_data = data.get("steps")
        steps = [Step.from_dict(s) for s in steps_data] if steps_data else None

        return cls(
            name=data.get("name", ""),
            goal=data.get("goal"),
            steps=steps,
            on_failure=on_failure,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert Scene to dictionary."""
        result: dict[str, Any] = {"name": self.name}
        if self.goal is not None:
            result["goal"] = self.goal
        if self.steps is not None:
            result["steps"] = [step.to_dict() for step in self.steps]
        if self.on_failure != FailureStrategy.ABORT:
            result["on_failure"] = self.on_failure.value
        return result


@dataclass
class Script:
    """Full demo script with metadata."""

    name: str
    description: str | None = None
    scenes: list[Scene] | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Script":
        """Create Script from dictionary.

        Recursively parses nested scenes and steps, converting
        enum strings to enum values.
        """
        scenes_data = data.get("scenes")
        scenes = [Scene.from_dict(s) for s in scenes_data] if scenes_data else None

        return cls(
            name=data.get("name", ""),
            description=data.get("description"),
            scenes=scenes,
            metadata=data.get("metadata"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert Script to dictionary.

        Recursively converts dataclasses to dicts and enums to string values.
        """
        result: dict[str, Any] = {"name": self.name}
        if self.description is not None:
            result["description"] = self.description
        if self.scenes is not None:
            result["scenes"] = [scene.to_dict() for scene in self.scenes]
        if self.metadata is not None:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def from_yaml(cls, source: str | Path) -> "Script":
        """Create Script from YAML file or string.

        Args:
            source: Either a path to a YAML file or a YAML string.

        Returns:
            Script instance parsed from the YAML data.
        """
        if isinstance(source, Path) or (
            isinstance(source, str) and Path(source).exists()
        ):
            path = Path(source)
            with open(path) as f:
                data = yaml.safe_load(f)
        else:
            data = yaml.safe_load(source)

        return cls.from_dict(data)

    @classmethod
    def from_json(cls, source: str | Path) -> "Script":
        """Create Script from JSON file or string.

        Args:
            source: Either a path to a JSON file or a JSON string.

        Returns:
            Script instance parsed from the JSON data.
        """
        if isinstance(source, Path) or (
            isinstance(source, str) and Path(source).exists()
        ):
            path = Path(source)
            with open(path) as f:
                data = json.load(f)
        else:
            data = json.loads(source)

        return cls.from_dict(data)
