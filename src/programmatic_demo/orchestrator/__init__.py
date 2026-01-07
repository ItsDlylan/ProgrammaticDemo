"""Orchestrator module for coordinating demo execution.

This package contains the Runner and related components that:
- Execute actions provided by the Director
- Control OS-level interactions (mouse, keyboard, browser)
- Capture screen state for observations
- Manage the execution loop: Observe -> Reason -> Act -> Verify -> Record
"""

from programmatic_demo.orchestrator.dispatcher import ActionDispatcher, get_dispatcher
from programmatic_demo.orchestrator.runner import Runner, RunnerConfig, RunnerState, StepResult, SceneResult, DemoResult

__all__ = ["Runner", "RunnerConfig", "RunnerState", "StepResult", "SceneResult", "DemoResult", "ActionDispatcher", "get_dispatcher"]
