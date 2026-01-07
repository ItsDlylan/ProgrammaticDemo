"""Demo execution runner.

The Runner orchestrates the execution of demo scenes by:
- Managing the core execution loop
- Dispatching actions to actuators
- Capturing observations from sensors
- Coordinating with the Director agent
"""

import time
from dataclasses import dataclass, field
from typing import Any

from programmatic_demo.orchestrator.dispatcher import get_dispatcher


@dataclass
class RunnerConfig:
    """Configuration for the Runner.

    Attributes:
        max_retries: Maximum retries for failed actions
        step_timeout: Timeout for individual steps in seconds
        scene_timeout: Timeout for entire scenes in seconds
        verify_after_action: Whether to verify state after each action
        action_timeout: Timeout for actions in seconds
        observation_interval: Interval between observations in seconds
        recording_enabled: Whether to record the demo
    """

    max_retries: int = 3
    step_timeout: float = 30.0
    scene_timeout: float = 300.0
    verify_after_action: bool = True
    action_timeout: float = 30.0
    observation_interval: float = 0.5
    recording_enabled: bool = True


@dataclass
class StepResult:
    """Result of executing a step.

    Attributes:
        success: Whether the step succeeded
        observation: Observation captured after step
        error: Error information if step failed
        duration: Time taken to execute step in seconds
        retries: Number of retries needed
    """

    success: bool
    observation: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    duration: float = 0.0
    retries: int = 0


@dataclass
class SceneResult:
    """Result of executing a scene.

    Attributes:
        success: Whether the scene succeeded
        steps_completed: Number of steps completed
        steps_total: Total number of steps in scene
        error: Error information if scene failed
        duration: Time taken to execute scene in seconds
    """

    success: bool
    steps_completed: int = 0
    steps_total: int = 0
    error: dict[str, Any] | None = None
    duration: float = 0.0


@dataclass
class DemoResult:
    """Result of executing a complete demo.

    Attributes:
        success: Whether the demo succeeded
        scenes_completed: Number of scenes completed
        scenes_total: Total number of scenes in demo
        video_path: Path to the recorded video (if any)
        duration: Total time taken in seconds
    """

    success: bool
    scenes_completed: int = 0
    scenes_total: int = 0
    video_path: str | None = None
    duration: float = 0.0


@dataclass
class RunnerState:
    """Current state of the Runner.

    Attributes:
        current_scene: Index of current scene
        current_step: Index of current step within scene
        total_actions: Total actions executed
        failed_actions: Number of failed actions
        is_running: Whether the runner is active
    """

    current_scene: int = 0
    current_step: int = 0
    total_actions: int = 0
    failed_actions: int = 0
    is_running: bool = False


class Runner:
    """Orchestrator that executes demo scenes.

    The Runner coordinates actuators and sensors to execute actions
    while maintaining state and handling errors/retries.
    """

    def __init__(self, config: RunnerConfig | None = None) -> None:
        """Initialize the Runner.

        Args:
            config: Runner configuration, uses defaults if None.
        """
        self._config = config or RunnerConfig()
        self._state = RunnerState()

    @property
    def config(self) -> RunnerConfig:
        """Get the runner configuration."""
        return self._config

    @property
    def state(self) -> RunnerState:
        """Get the current runner state."""
        return self._state

    def run_script(self, script: Any) -> dict[str, Any]:
        """Execute a complete demo script.

        Args:
            script: Script model containing scenes and steps.

        Returns:
            Result dict with success status and execution summary.
        """
        raise NotImplementedError("run_script not yet implemented")

    def run_scene(self, scene: Any) -> dict[str, Any]:
        """Execute a single demo scene.

        Args:
            scene: Scene model containing steps and goal.

        Returns:
            Result dict with success status and scene outcome.
        """
        raise NotImplementedError("run_scene not yet implemented")

    def execute_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute a single action.

        Args:
            action: Action dict with type, target, and parameters.

        Returns:
            Result dict with success status and action outcome.
        """
        raise NotImplementedError("execute_action not yet implemented")

    def execute_step(self, step: dict[str, Any]) -> StepResult:
        """Execute a single step and return the result.

        Args:
            step: Step dict containing action type and parameters.

        Returns:
            StepResult with success status, observation, and timing.
        """
        start_time = time.time()
        retries = 0

        dispatcher = get_dispatcher()

        while retries <= self._config.max_retries:
            try:
                # Dispatch the action
                result = dispatcher.dispatch(step)

                # Capture observation after action (if observe is implemented)
                observation = None
                try:
                    observation = self.observe()
                except NotImplementedError:
                    pass

                # Check if action succeeded
                if result.get("success", False):
                    duration = time.time() - start_time
                    self._state.total_actions += 1
                    return StepResult(
                        success=True,
                        observation=observation,
                        error=None,
                        duration=duration,
                        retries=retries,
                    )

                # Action failed, try again if retries remain
                retries += 1
                if retries <= self._config.max_retries:
                    time.sleep(0.5)  # Brief pause before retry

            except Exception as e:
                retries += 1
                if retries > self._config.max_retries:
                    duration = time.time() - start_time
                    self._state.failed_actions += 1
                    return StepResult(
                        success=False,
                        observation=None,
                        error={"type": "exception", "message": str(e)},
                        duration=duration,
                        retries=retries - 1,
                    )

        # All retries exhausted
        duration = time.time() - start_time
        self._state.failed_actions += 1
        return StepResult(
            success=False,
            observation=None,
            error={"type": "max_retries", "message": "Maximum retries exceeded"},
            duration=duration,
            retries=retries,
        )

    def observe(self) -> dict[str, Any]:
        """Capture current observation.

        Returns:
            Observation dict with screenshot, OCR, window info, etc.
        """
        raise NotImplementedError("observe not yet implemented")

    def wait_for(
        self,
        condition: dict[str, Any],
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Wait for a condition to be met.

        Args:
            condition: Condition dict specifying what to wait for.
            timeout: Max wait time, uses config default if None.

        Returns:
            Result dict indicating if condition was met.
        """
        raise NotImplementedError("wait_for not yet implemented")

    def stop(self) -> None:
        """Stop the runner gracefully."""
        self._state.is_running = False

    def reset(self) -> None:
        """Reset the runner state for a new run."""
        self._state = RunnerState()
