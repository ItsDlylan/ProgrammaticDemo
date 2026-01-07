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


# Placeholder for future implementations
# Classes will be added in subsequent features:
# - NLP-003: IntentParser class
