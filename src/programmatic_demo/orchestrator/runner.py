"""Demo execution runner.

The Runner orchestrates the execution of demo scenes by:
- Managing the core execution loop
- Dispatching actions to actuators
- Capturing observations from sensors
- Coordinating with the Director agent
"""

import signal
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from programmatic_demo.agents.director import detect_success
from programmatic_demo.orchestrator.dispatcher import get_dispatcher


# Type alias for interrupt callback
InterruptCallback = Callable[[dict[str, Any]], None]

# Type alias for progress callback
ProgressCallback = Callable[[dict[str, Any]], None]


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
        interrupted: Whether execution was interrupted
        interrupt_reason: Reason for interruption (if any)
    """

    current_scene: int = 0
    current_step: int = 0
    total_actions: int = 0
    failed_actions: int = 0
    is_running: bool = False
    interrupted: bool = False
    interrupt_reason: str | None = None


class Runner:
    """Orchestrator that executes demo scenes.

    The Runner coordinates actuators and sensors to execute actions
    while maintaining state and handling errors/retries.
    """

    def __init__(
        self,
        config: RunnerConfig | None = None,
        on_interrupt: InterruptCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        """Initialize the Runner.

        Args:
            config: Runner configuration, uses defaults if None.
            on_interrupt: Callback invoked when execution is interrupted.
            on_progress: Callback invoked for progress events.
        """
        self._config = config or RunnerConfig()
        self._state = RunnerState()
        self._on_interrupt = on_interrupt
        self._on_progress = on_progress
        self._original_sigint_handler: Any = None
        self._signal_registered = False

    def _notify_progress(self, event: str, **kwargs: Any) -> None:
        """Notify progress callback of an event.

        Args:
            event: Event type (e.g., "scene_start", "step_complete").
            **kwargs: Additional event data.
        """
        if self._on_progress is not None:
            try:
                self._on_progress({"event": event, **kwargs})
            except Exception:
                # Don't let callback errors propagate
                pass

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
        result = self.execute_demo(script)
        return {
            "success": result.success,
            "scenes_completed": result.scenes_completed,
            "scenes_total": result.scenes_total,
            "video_path": result.video_path,
            "duration": result.duration,
        }

    def execute_demo(self, script: Any) -> DemoResult:
        """Execute a complete demo script.

        Args:
            script: Script model or dict containing scenes.
                   Expected keys: 'scenes' (list), optionally 'name'.

        Returns:
            DemoResult with detailed execution outcome.
        """
        start_time = time.time()
        self._state.is_running = True
        self._state.current_scene = 0

        # Extract scenes from script (handle dict or object)
        if hasattr(script, "scenes"):
            scenes = script.scenes
        elif isinstance(script, dict):
            scenes = script.get("scenes", [])
        else:
            scenes = []

        scenes_total = len(scenes)
        scenes_completed = 0

        # Notify demo started
        self._notify_progress(
            "demo_start",
            scenes_total=scenes_total,
        )

        for i, scene in enumerate(scenes):
            if not self._state.is_running:
                return DemoResult(
                    success=False,
                    scenes_completed=scenes_completed,
                    scenes_total=scenes_total,
                    duration=time.time() - start_time,
                )

            # Get scene name if available
            scene_name = getattr(scene, "name", None) or (
                scene.get("name") if isinstance(scene, dict) else None
            )

            # Notify scene starting
            self._notify_progress(
                "scene_start",
                scene_index=i,
                scene_name=scene_name,
                scenes_total=scenes_total,
            )

            self._state.current_scene = i
            result = self.execute_scene(scene)

            if result.success:
                scenes_completed += 1
                # Notify scene completed
                self._notify_progress(
                    "scene_complete",
                    scene_index=i,
                    scene_name=scene_name,
                    scenes_completed=scenes_completed,
                    scenes_total=scenes_total,
                    duration=result.duration,
                )
                # Clean up after scene for isolation
                self.scene_cleanup()
            else:
                return DemoResult(
                    success=False,
                    scenes_completed=scenes_completed,
                    scenes_total=scenes_total,
                    duration=time.time() - start_time,
                )

        duration = time.time() - start_time
        # Notify demo completed
        self._notify_progress(
            "demo_complete",
            success=True,
            scenes_completed=scenes_completed,
            scenes_total=scenes_total,
            duration=duration,
        )

        return DemoResult(
            success=True,
            scenes_completed=scenes_completed,
            scenes_total=scenes_total,
            duration=duration,
        )

    def scene_cleanup(self) -> None:
        """Clean up after a scene for isolation.

        Resets temporary state and ensures clean slate
        for the next scene execution.
        """
        # Reset step counter for next scene
        self._state.current_step = 0
        # Brief pause between scenes
        time.sleep(0.2)

    def run_scene(self, scene: Any) -> dict[str, Any]:
        """Execute a single demo scene.

        Args:
            scene: Scene model containing steps and goal.

        Returns:
            Result dict with success status and scene outcome.
        """
        result = self.execute_scene(scene)
        return {
            "success": result.success,
            "steps_completed": result.steps_completed,
            "steps_total": result.steps_total,
            "duration": result.duration,
            "error": result.error,
        }

    def execute_scene(self, scene: Any) -> SceneResult:
        """Execute a single demo scene.

        Args:
            scene: Scene model or dict containing steps and goal.
                   Expected keys: 'steps' (list), optionally 'name' and 'goal'.

        Returns:
            SceneResult with detailed execution outcome.
        """
        start_time = time.time()
        self._state.is_running = True

        # Extract steps from scene (handle dict or object)
        if hasattr(scene, "steps"):
            steps = scene.steps
        elif isinstance(scene, dict):
            steps = scene.get("steps", [])
        else:
            steps = []

        steps_total = len(steps)
        steps_completed = 0

        for step_index, step in enumerate(steps):
            if not self._state.is_running:
                # Runner was stopped
                return SceneResult(
                    success=False,
                    steps_completed=steps_completed,
                    steps_total=steps_total,
                    error={"type": "stopped", "message": "Runner was stopped"},
                    duration=time.time() - start_time,
                )

            # Convert step to dict if needed
            step_dict = step.to_dict() if hasattr(step, "to_dict") else step

            # Notify step starting
            self._notify_progress(
                "step_start",
                step_index=step_index,
                steps_total=steps_total,
                action=step_dict.get("action"),
            )

            result = self.execute_step(step_dict)
            self._state.current_step = steps_completed

            if result.success:
                steps_completed += 1
                # Notify step completed
                self._notify_progress(
                    "step_complete",
                    step_index=step_index,
                    steps_completed=steps_completed,
                    steps_total=steps_total,
                    duration=result.duration,
                    retries=result.retries,
                )
            else:
                # Notify step failed
                self._notify_progress(
                    "step_failed",
                    step_index=step_index,
                    steps_completed=steps_completed,
                    steps_total=steps_total,
                    error=result.error,
                    retries=result.retries,
                )
                # Step failed after retries
                return SceneResult(
                    success=False,
                    steps_completed=steps_completed,
                    steps_total=steps_total,
                    error=result.error,
                    duration=time.time() - start_time,
                )

        return SceneResult(
            success=True,
            steps_completed=steps_completed,
            steps_total=steps_total,
            error=None,
            duration=time.time() - start_time,
        )

    def execute_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute a single action.

        Args:
            action: Action dict with type, target, and parameters.

        Returns:
            Result dict with success status and action outcome.
        """
        raise NotImplementedError("execute_action not yet implemented")

    def verify_step(self, step: dict[str, Any], observation: dict[str, Any]) -> bool:
        """Verify if a step's expected state matches the observation.

        Args:
            step: Step dict containing expected state criteria.
            observation: Current observation dict.

        Returns:
            True if observation matches expected state, False otherwise.
        """
        # Get expected state from step's wait_for or expected fields
        expected = step.get("wait_for") or step.get("expected") or {}
        if not expected:
            # No verification criteria, assume success
            return True
        return detect_success(observation, expected)

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

    def retry_step(
        self,
        step: dict[str, Any],
        max_attempts: int = 3,
        backoff_factor: float = 1.5,
        initial_delay: float = 0.5,
    ) -> StepResult:
        """Execute a step with exponential backoff retry.

        Args:
            step: Step dict to execute.
            max_attempts: Maximum number of attempts (default 3).
            backoff_factor: Multiplier for delay between attempts (default 1.5).
            initial_delay: Initial delay in seconds (default 0.5).

        Returns:
            StepResult with outcome after all attempts.
        """
        start_time = time.time()
        delay = initial_delay
        last_error = None

        dispatcher = get_dispatcher()

        for attempt in range(max_attempts):
            try:
                result = dispatcher.dispatch(step)

                # Try to capture observation
                observation = None
                try:
                    observation = self.observe()
                except NotImplementedError:
                    pass

                if result.get("success", False):
                    self._state.total_actions += 1
                    return StepResult(
                        success=True,
                        observation=observation,
                        error=None,
                        duration=time.time() - start_time,
                        retries=attempt,
                    )

                last_error = result.get("error", {"message": "Unknown failure"})

            except Exception as e:
                last_error = {"type": "exception", "message": str(e)}

            # Wait before retry with exponential backoff
            if attempt < max_attempts - 1:
                time.sleep(delay)
                delay *= backoff_factor

        # All attempts exhausted
        self._state.failed_actions += 1
        return StepResult(
            success=False,
            observation=None,
            error=last_error,
            duration=time.time() - start_time,
            retries=max_attempts - 1,
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

    def graceful_interrupt(self, reason: str = "user_requested") -> dict[str, Any]:
        """Handle graceful interruption of execution.

        Stops the current execution, cleans up resources, and saves
        partial progress. This method is safe to call from signal handlers.

        Args:
            reason: Reason for the interruption (e.g., "user_requested", "sigint").

        Returns:
            Dict containing interrupt status and partial progress info.
        """
        # Mark as interrupted
        self._state.is_running = False
        self._state.interrupted = True
        self._state.interrupt_reason = reason

        # Build progress info
        progress_info = {
            "interrupted": True,
            "reason": reason,
            "current_scene": self._state.current_scene,
            "current_step": self._state.current_step,
            "total_actions": self._state.total_actions,
            "failed_actions": self._state.failed_actions,
        }

        # Call interrupt callback if registered
        if self._on_interrupt is not None:
            try:
                self._on_interrupt(progress_info)
            except Exception:
                # Don't let callback errors propagate
                pass

        # Restore original signal handler if we registered one
        self._unregister_signal_handler()

        return progress_info

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle SIGINT (Ctrl+C) signal.

        Args:
            signum: Signal number received.
            frame: Current stack frame.
        """
        self.graceful_interrupt(reason="sigint")

    def register_signal_handler(self) -> None:
        """Register SIGINT handler for graceful interruption.

        This should be called before starting execution if you want
        Ctrl+C to trigger graceful interruption instead of raising
        KeyboardInterrupt.
        """
        if not self._signal_registered:
            self._original_sigint_handler = signal.signal(
                signal.SIGINT, self._signal_handler
            )
            self._signal_registered = True

    def _unregister_signal_handler(self) -> None:
        """Restore the original SIGINT handler."""
        if self._signal_registered and self._original_sigint_handler is not None:
            signal.signal(signal.SIGINT, self._original_sigint_handler)
            self._signal_registered = False
            self._original_sigint_handler = None

    @property
    def interrupted(self) -> bool:
        """Check if execution was interrupted."""
        return self._state.interrupted

    @property
    def interrupt_reason(self) -> str | None:
        """Get the reason for interruption, if any."""
        return self._state.interrupt_reason
