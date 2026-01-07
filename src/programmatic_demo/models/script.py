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

# Placeholder for future implementations
# Classes will be added in subsequent features:
# - SCRIPT-001: ActionType enum
# - SCRIPT-002: TargetType enum
# - SCRIPT-003: WaitCondition dataclass
# - SCRIPT-004: Target dataclass
# - SCRIPT-005: Step dataclass
# - SCRIPT-006: Scene dataclass
# - SCRIPT-007: Script dataclass
