"""INT-008: Test full demo execution with recording.

This test verifies that:
1. Runner configuration works correctly
2. Step, scene, and demo execution workflows work
3. State management tracks progress correctly
4. Graceful interruption works
5. Retry strategies function properly
6. Progress callbacks are invoked
"""

import time
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from programmatic_demo.orchestrator.runner import (
    DemoResult,
    Runner,
    RunnerConfig,
    RunnerState,
    SceneResult,
    StepResult,
)


class TestRunnerConfig:
    """Test RunnerConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RunnerConfig()

        assert config.max_retries == 3
        assert config.step_timeout == 30.0
        assert config.scene_timeout == 300.0
        assert config.verify_after_action is True
        assert config.recording_enabled is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RunnerConfig(
            max_retries=5,
            step_timeout=60.0,
            scene_timeout=600.0,
            verify_after_action=False,
            recording_enabled=False,
        )

        assert config.max_retries == 5
        assert config.step_timeout == 60.0
        assert config.scene_timeout == 600.0
        assert config.verify_after_action is False
        assert config.recording_enabled is False


class TestRunnerState:
    """Test RunnerState dataclass."""

    def test_default_state(self):
        """Test default state values."""
        state = RunnerState()

        assert state.current_scene == 0
        assert state.current_step == 0
        assert state.total_actions == 0
        assert state.failed_actions == 0
        assert state.is_running is False
        assert state.interrupted is False
        assert state.interrupt_reason is None


class TestStepResult:
    """Test StepResult dataclass."""

    def test_successful_result(self):
        """Test successful step result."""
        result = StepResult(
            success=True,
            observation={"ocr_text": "Button clicked"},
            duration=0.5,
            retries=0,
        )

        assert result.success is True
        assert result.observation is not None
        assert result.error is None
        assert result.duration == 0.5
        assert result.retries == 0

    def test_failed_result(self):
        """Test failed step result."""
        result = StepResult(
            success=False,
            error={"type": "timeout", "message": "Element not found"},
            duration=30.0,
            retries=3,
        )

        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "timeout"
        assert result.retries == 3


class TestSceneResult:
    """Test SceneResult dataclass."""

    def test_successful_scene(self):
        """Test successful scene result."""
        result = SceneResult(
            success=True,
            steps_completed=5,
            steps_total=5,
            duration=10.0,
        )

        assert result.success is True
        assert result.steps_completed == 5
        assert result.steps_total == 5
        assert result.error is None

    def test_failed_scene(self):
        """Test failed scene result."""
        result = SceneResult(
            success=False,
            steps_completed=3,
            steps_total=5,
            error={"message": "Step 4 failed"},
            duration=15.0,
        )

        assert result.success is False
        assert result.steps_completed == 3
        assert result.error is not None


class TestDemoResult:
    """Test DemoResult dataclass."""

    def test_successful_demo(self):
        """Test successful demo result."""
        result = DemoResult(
            success=True,
            scenes_completed=3,
            scenes_total=3,
            video_path="/tmp/demo.mp4",
            duration=60.0,
        )

        assert result.success is True
        assert result.scenes_completed == 3
        assert result.video_path == "/tmp/demo.mp4"

    def test_partial_demo(self):
        """Test partially completed demo."""
        result = DemoResult(
            success=False,
            scenes_completed=2,
            scenes_total=5,
            duration=30.0,
        )

        assert result.success is False
        assert result.scenes_completed == 2
        assert result.scenes_total == 5


class TestRunnerInit:
    """Test Runner initialization."""

    def test_default_init(self):
        """Test default initialization."""
        runner = Runner()

        assert runner.config is not None
        assert runner.state.is_running is False
        assert runner.interrupted is False

    def test_custom_config(self):
        """Test initialization with custom config."""
        config = RunnerConfig(max_retries=10)
        runner = Runner(config=config)

        assert runner.config.max_retries == 10

    def test_callbacks(self):
        """Test initialization with callbacks."""
        on_interrupt = MagicMock()
        on_progress = MagicMock()

        runner = Runner(on_interrupt=on_interrupt, on_progress=on_progress)

        assert runner._on_interrupt is on_interrupt
        assert runner._on_progress is on_progress


class TestRunnerExecuteStep:
    """Test Runner.execute_step method."""

    def test_execute_step_success(self):
        """Test successful step execution."""
        runner = Runner()

        # Mock the dispatcher to return success
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"success": True}

        with patch(
            "programmatic_demo.orchestrator.runner.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            step = {"action": "click", "target": {"description": "button"}}
            result = runner.execute_step(step)

            assert result.success is True
            assert result.retries == 0
            mock_dispatcher.dispatch.assert_called_once_with(step)

    def test_execute_step_with_retries(self):
        """Test step execution with retries."""
        config = RunnerConfig(max_retries=3)
        runner = Runner(config=config)

        # Fail twice, then succeed
        call_count = [0]

        def mock_dispatch(step):
            call_count[0] += 1
            if call_count[0] < 3:
                return {"success": False}
            return {"success": True}

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.side_effect = mock_dispatch

        with patch(
            "programmatic_demo.orchestrator.runner.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            step = {"action": "click"}
            result = runner.execute_step(step)

            assert result.success is True
            assert result.retries == 2

    def test_execute_step_max_retries_exceeded(self):
        """Test step fails after max retries."""
        config = RunnerConfig(max_retries=2)
        runner = Runner(config=config)

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"success": False}

        with patch(
            "programmatic_demo.orchestrator.runner.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            step = {"action": "click"}
            result = runner.execute_step(step)

            assert result.success is False
            assert "max_retries" in result.error["type"]
            assert runner.state.failed_actions == 1


class TestRunnerExecuteScene:
    """Test Runner.execute_scene method."""

    def test_execute_scene_with_steps(self):
        """Test executing a scene with multiple steps."""
        runner = Runner()

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"success": True}

        with patch(
            "programmatic_demo.orchestrator.runner.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            scene = {
                "name": "test_scene",
                "steps": [
                    {"action": "click"},
                    {"action": "type"},
                    {"action": "wait"},
                ],
            }

            result = runner.execute_scene(scene)

            assert result.success is True
            assert result.steps_completed == 3
            assert result.steps_total == 3

    def test_execute_scene_step_fails(self):
        """Test scene fails when step fails."""
        config = RunnerConfig(max_retries=0)
        runner = Runner(config=config)

        call_count = [0]

        def mock_dispatch(step):
            call_count[0] += 1
            if call_count[0] == 2:
                return {"success": False}
            return {"success": True}

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.side_effect = mock_dispatch

        with patch(
            "programmatic_demo.orchestrator.runner.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            scene = {
                "steps": [
                    {"action": "click"},
                    {"action": "type"},  # This one fails
                    {"action": "wait"},
                ],
            }

            result = runner.execute_scene(scene)

            assert result.success is False
            assert result.steps_completed == 1
            assert result.steps_total == 3

    def test_execute_scene_empty_steps(self):
        """Test executing scene with no steps."""
        runner = Runner()

        scene = {"name": "empty", "steps": []}
        result = runner.execute_scene(scene)

        assert result.success is True
        assert result.steps_completed == 0
        assert result.steps_total == 0


class TestRunnerExecuteDemo:
    """Test Runner.execute_demo method."""

    def test_execute_demo_with_scenes(self):
        """Test executing a demo with multiple scenes."""
        runner = Runner()

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"success": True}

        with patch(
            "programmatic_demo.orchestrator.runner.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            script = {
                "name": "test_demo",
                "scenes": [
                    {"name": "intro", "steps": [{"action": "wait"}]},
                    {"name": "main", "steps": [{"action": "click"}]},
                    {"name": "outro", "steps": [{"action": "wait"}]},
                ],
            }

            result = runner.execute_demo(script)

            assert result.success is True
            assert result.scenes_completed == 3
            assert result.scenes_total == 3

    def test_execute_demo_scene_fails(self):
        """Test demo fails when a scene fails."""
        config = RunnerConfig(max_retries=0)
        runner = Runner(config=config)

        call_count = [0]

        def mock_dispatch(step):
            call_count[0] += 1
            # Fail on second scene's step
            if call_count[0] == 2:
                return {"success": False}
            return {"success": True}

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.side_effect = mock_dispatch

        with patch(
            "programmatic_demo.orchestrator.runner.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            script = {
                "scenes": [
                    {"steps": [{"action": "click"}]},
                    {"steps": [{"action": "type"}]},  # This fails
                    {"steps": [{"action": "wait"}]},
                ],
            }

            result = runner.execute_demo(script)

            assert result.success is False
            assert result.scenes_completed == 1

    def test_execute_demo_empty_scenes(self):
        """Test executing demo with no scenes."""
        runner = Runner()

        script = {"name": "empty", "scenes": []}
        result = runner.execute_demo(script)

        assert result.success is True
        assert result.scenes_completed == 0


class TestRunnerProgressCallbacks:
    """Test progress callback invocation."""

    def test_progress_callback_demo_events(self):
        """Test progress callbacks for demo events."""
        events = []

        def on_progress(event):
            events.append(event)

        runner = Runner(on_progress=on_progress)

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"success": True}

        with patch(
            "programmatic_demo.orchestrator.runner.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            script = {
                "scenes": [
                    {"name": "test", "steps": [{"action": "click"}]},
                ],
            }

            runner.execute_demo(script)

            event_types = [e["event"] for e in events]
            assert "demo_start" in event_types
            assert "scene_start" in event_types
            assert "step_start" in event_types
            assert "step_complete" in event_types
            assert "scene_complete" in event_types
            assert "demo_complete" in event_types

    def test_progress_callback_step_failed(self):
        """Test step_failed event is emitted."""
        events = []

        def on_progress(event):
            events.append(event)

        config = RunnerConfig(max_retries=0)
        runner = Runner(config=config, on_progress=on_progress)

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"success": False}

        with patch(
            "programmatic_demo.orchestrator.runner.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            scene = {"steps": [{"action": "click"}]}
            runner.execute_scene(scene)

            event_types = [e["event"] for e in events]
            assert "step_failed" in event_types


class TestRunnerGracefulInterrupt:
    """Test graceful interruption."""

    def test_graceful_interrupt(self):
        """Test graceful interrupt method."""
        runner = Runner()
        runner._state.is_running = True
        runner._state.current_scene = 2
        runner._state.current_step = 3

        result = runner.graceful_interrupt(reason="test_interrupt")

        assert result["interrupted"] is True
        assert result["reason"] == "test_interrupt"
        assert result["current_scene"] == 2
        assert result["current_step"] == 3
        assert runner.interrupted is True
        assert runner.interrupt_reason == "test_interrupt"

    def test_graceful_interrupt_callback(self):
        """Test interrupt callback is invoked."""
        callback_data = []

        def on_interrupt(data):
            callback_data.append(data)

        runner = Runner(on_interrupt=on_interrupt)
        runner._state.is_running = True

        runner.graceful_interrupt(reason="callback_test")

        assert len(callback_data) == 1
        assert callback_data[0]["reason"] == "callback_test"

    def test_execution_stops_when_interrupted(self):
        """Test execution stops after interruption."""
        runner = Runner()

        mock_dispatcher = MagicMock()
        call_count = [0]

        def mock_dispatch(step):
            call_count[0] += 1
            # Interrupt during second step
            if call_count[0] == 2:
                runner._state.is_running = False
            return {"success": True}

        mock_dispatcher.dispatch.side_effect = mock_dispatch

        with patch(
            "programmatic_demo.orchestrator.runner.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            scene = {
                "steps": [
                    {"action": "click"},
                    {"action": "type"},
                    {"action": "wait"},  # Should not run
                ],
            }

            result = runner.execute_scene(scene)

            assert result.success is False
            assert result.steps_completed < 3


class TestRunnerStateManagement:
    """Test runner state management."""

    def test_stop_method(self):
        """Test stop method sets is_running to False."""
        runner = Runner()
        runner._state.is_running = True

        runner.stop()

        assert runner.state.is_running is False

    def test_reset_method(self):
        """Test reset method clears state."""
        runner = Runner()
        runner._state.is_running = True
        runner._state.current_scene = 5
        runner._state.total_actions = 100
        runner._state.interrupted = True

        runner.reset()

        assert runner.state.is_running is False
        assert runner.state.current_scene == 0
        assert runner.state.total_actions == 0
        assert runner.state.interrupted is False


class TestRunnerVerifyStep:
    """Test step verification."""

    def test_verify_step_no_criteria(self):
        """Test verification passes when no criteria specified."""
        runner = Runner()

        step = {"action": "click"}
        observation = {"ocr_text": "anything"}

        assert runner.verify_step(step, observation) is True

    def test_verify_step_text_match(self):
        """Test verification with text matching."""
        runner = Runner()

        step = {"action": "click", "wait_for": {"text": "success"}}
        observation = {"ocr_text": "Operation completed with success!"}

        assert runner.verify_step(step, observation) is True

    def test_verify_step_text_no_match(self):
        """Test verification fails when text not found."""
        runner = Runner()

        step = {"action": "click", "wait_for": {"text": "success"}}
        observation = {"ocr_text": "Loading..."}

        assert runner.verify_step(step, observation) is False


class TestRunScriptMethod:
    """Test run_script convenience method."""

    def test_run_script_returns_dict(self):
        """Test run_script returns result dict."""
        runner = Runner()

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"success": True}

        with patch(
            "programmatic_demo.orchestrator.runner.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            script = {"scenes": [{"steps": [{"action": "wait"}]}]}
            result = runner.run_script(script)

            assert isinstance(result, dict)
            assert "success" in result
            assert "scenes_completed" in result
            assert "scenes_total" in result


class TestRunSceneMethod:
    """Test run_scene convenience method."""

    def test_run_scene_returns_dict(self):
        """Test run_scene returns result dict."""
        runner = Runner()

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"success": True}

        with patch(
            "programmatic_demo.orchestrator.runner.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            scene = {"steps": [{"action": "wait"}]}
            result = runner.run_scene(scene)

            assert isinstance(result, dict)
            assert "success" in result
            assert "steps_completed" in result
            assert "steps_total" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
