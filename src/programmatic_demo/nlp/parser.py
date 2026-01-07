"""Natural language parser for extracting demo actions from text.

This module provides functionality to parse natural language descriptions
of demo actions and convert them into structured ActionIntent objects
that can be used to generate demo scripts.
"""

import re
from dataclasses import dataclass
from typing import Any

@dataclass
class ActionIntent:
    """Represents a parsed action intent from natural language.

    Attributes:
        action_type: The type of action (click, type, scroll, etc.)
        target_description: Human-readable description of the target
        params: Additional parameters for the action
        confidence: Confidence score (0.0 to 1.0) of the parse
    """

    action_type: str
    target_description: str | None = None
    params: dict[str, Any] | None = None
    confidence: float = 1.0


# Regex patterns for parsing natural language action descriptions
# Each pattern includes capture groups for target and parameters
ACTION_PATTERNS: dict[str, re.Pattern[str]] = {
    # Click actions: "click on X", "click the X button", "tap X"
    "click": re.compile(
        r"(?:click|tap|press|select)\s+(?:on\s+)?(?:the\s+)?(.+?)(?:\s+button)?$",
        re.IGNORECASE,
    ),
    # Type actions: "type X", "enter X in Y", "input X"
    "type": re.compile(
        r"(?:type|enter|input|write)\s+['\"]?(.+?)['\"]?(?:\s+(?:in|into)\s+(?:the\s+)?(.+))?$",
        re.IGNORECASE,
    ),
    # Press actions: "press Enter", "hit Escape", "press Ctrl+C"
    "press": re.compile(
        r"(?:press|hit|push)\s+(?:the\s+)?(.+?)(?:\s+key)?$",
        re.IGNORECASE,
    ),
    # Scroll actions: "scroll down", "scroll to X", "scroll up on Y"
    "scroll": re.compile(
        r"scroll\s+(up|down|left|right)(?:\s+(?:to|on|in)\s+(?:the\s+)?(.+))?$",
        re.IGNORECASE,
    ),
    # Wait actions: "wait for X", "wait 5 seconds", "pause"
    "wait": re.compile(
        r"(?:wait|pause)\s+(?:for\s+)?(?:(\d+)\s*(?:seconds?|s)|(.+))$",
        re.IGNORECASE,
    ),
    # Navigate actions: "go to X", "navigate to X", "open X"
    "navigate": re.compile(
        r"(?:go\s+to|navigate\s+to|open|visit)\s+(.+)$",
        re.IGNORECASE,
    ),
}


def parse_click(text: str) -> ActionIntent | None:
    """Parse a click action from natural language text.

    Handles phrases like:
    - "click X"
    - "click on X"
    - "click the X button"
    - "press X button"
    - "tap on X"

    Args:
        text: Natural language description of a click action.

    Returns:
        ActionIntent with action_type="click" and target_description,
        or None if no click action could be parsed.
    """
    pattern = ACTION_PATTERNS["click"]
    match = pattern.search(text.strip())

    if match:
        target = match.group(1).strip()
        return ActionIntent(
            action_type="click",
            target_description=target,
            confidence=1.0,
        )

    return None


def parse_type(text: str) -> ActionIntent | None:
    """Parse a type action from natural language text.

    Handles phrases like:
    - "type X"
    - "type 'X'"
    - "enter X in Y"
    - "enter X into the Y field"
    - "write X"
    - "input X"

    Args:
        text: Natural language description of a type action.

    Returns:
        ActionIntent with action_type="type", params containing "text" to type
        and optional target_description for the field, or None if not parsed.
    """
    pattern = ACTION_PATTERNS["type"]
    match = pattern.search(text.strip())

    if match:
        type_text = match.group(1).strip()
        target = match.group(2)
        target = target.strip() if target else None

        return ActionIntent(
            action_type="type",
            target_description=target,
            params={"text": type_text},
            confidence=1.0,
        )

    return None


# Map common key names to pyautogui key names
KEY_ALIASES: dict[str, str] = {
    "enter": "enter",
    "return": "enter",
    "tab": "tab",
    "escape": "escape",
    "esc": "escape",
    "space": "space",
    "spacebar": "space",
    "backspace": "backspace",
    "delete": "delete",
    "del": "delete",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "home": "home",
    "end": "end",
    "pageup": "pageup",
    "pagedown": "pagedown",
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "cmd": "command",
    "command": "command",
    "win": "win",
    "windows": "win",
}


def parse_key(text: str) -> ActionIntent | None:
    """Parse a key press action from natural language text.

    Handles phrases like:
    - "press Enter"
    - "hit Tab"
    - "push Escape key"
    - "press Ctrl+C"

    Args:
        text: Natural language description of a key press action.

    Returns:
        ActionIntent with action_type="press" and params containing "key",
        or None if no key action could be parsed.
    """
    pattern = ACTION_PATTERNS["press"]
    match = pattern.search(text.strip())

    if match:
        key_text = match.group(1).strip().lower()

        # Map to pyautogui key name
        key = KEY_ALIASES.get(key_text, key_text)

        return ActionIntent(
            action_type="press",
            params={"key": key},
            confidence=1.0,
        )

    return None


def parse_wait(text: str) -> ActionIntent | None:
    """Parse a wait action from natural language text.

    Handles phrases like:
    - "wait for X"
    - "wait 5 seconds"
    - "wait 2s"
    - "pause for the loading screen"
    - "until X appears"

    Args:
        text: Natural language description of a wait action.

    Returns:
        ActionIntent with action_type="wait" and params containing either
        "seconds" (for duration) or "condition" (for text/element wait),
        or None if not parsed.
    """
    # Check for "until X appears" pattern
    until_pattern = re.compile(
        r"(?:wait\s+)?until\s+(?:the\s+)?(.+?)(?:\s+appears?)?$",
        re.IGNORECASE,
    )
    until_match = until_pattern.search(text.strip())
    if until_match:
        condition = until_match.group(1).strip()
        return ActionIntent(
            action_type="wait",
            params={"condition": condition, "type": "text"},
            confidence=1.0,
        )

    # Use standard wait pattern
    pattern = ACTION_PATTERNS["wait"]
    match = pattern.search(text.strip())

    if match:
        seconds = match.group(1)
        condition = match.group(2)

        if seconds:
            return ActionIntent(
                action_type="wait",
                params={"seconds": int(seconds), "type": "duration"},
                confidence=1.0,
            )
        elif condition:
            return ActionIntent(
                action_type="wait",
                params={"condition": condition.strip(), "type": "text"},
                confidence=1.0,
            )

    return None


def parse_scroll(text: str) -> ActionIntent | None:
    """Parse a scroll action from natural language text.

    Handles phrases like:
    - "scroll down"
    - "scroll up"
    - "scroll left"
    - "scroll right"
    - "scroll down to the footer"
    - "scroll up on the menu"

    Args:
        text: Natural language description of a scroll action.

    Returns:
        ActionIntent with action_type="scroll" and params containing
        "direction" and optional "target", or None if not parsed.
    """
    pattern = ACTION_PATTERNS["scroll"]
    match = pattern.search(text.strip())

    if match:
        direction = match.group(1).lower()
        target = match.group(2)
        target = target.strip() if target else None

        return ActionIntent(
            action_type="scroll",
            target_description=target,
            params={"direction": direction},
            confidence=1.0,
        )

    return None


def parse_navigate(text: str) -> ActionIntent | None:
    """Parse a navigate action from natural language text.

    Handles phrases like:
    - "go to https://example.com"
    - "navigate to the dashboard"
    - "open Settings"
    - "visit google.com"

    Args:
        text: Natural language description of a navigate action.

    Returns:
        ActionIntent with action_type="navigate" and target_description
        containing URL or destination name, or None if not parsed.
    """
    pattern = ACTION_PATTERNS["navigate"]
    match = pattern.search(text.strip())

    if match:
        destination = match.group(1).strip()

        # Determine if it looks like a URL
        is_url = (
            destination.startswith("http://")
            or destination.startswith("https://")
            or "." in destination
            and " " not in destination
        )

        return ActionIntent(
            action_type="navigate",
            target_description=destination,
            params={"type": "url" if is_url else "app"},
            confidence=1.0,
        )

    return None
