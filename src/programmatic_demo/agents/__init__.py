"""Agent modules for autonomous demo generation.

This package contains the agent roles that collaborate to create demos:
- Director: Plans scenes, chooses actions, reacts to observations
- Operator: Executes actions (handled by orchestrator)
- Observer: Monitors state (handled by sensors)
- Editor: Handles retries/corrections
"""

from programmatic_demo.agents.claude_client import ClaudeClient
from programmatic_demo.agents.director import (
    Director,
    RetryStrategy,
    ScenePlan,
    Step,
    compress_screenshot,
    detect_success,
    observation_to_prompt,
    summarize_context,
)

__all__ = [
    "ClaudeClient",
    "Director",
    "RetryStrategy",
    "ScenePlan",
    "Step",
    "compress_screenshot",
    "detect_success",
    "observation_to_prompt",
    "summarize_context",
]
