"""INT-007: Test Director scene planning.

This test verifies that:
1. Director.plan_scene creates and tracks scene plans
2. Director can add steps to a plan
3. Director.decide_next_action returns steps in order
4. Director detects goal achievement
5. Failure analysis and retry strategies work
6. Context summarization and observation handling work
"""

import base64
import io
from datetime import datetime

import pytest
from PIL import Image

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


class TestStepDataclass:
    """Test Step dataclass."""

    def test_step_creation(self):
        """Test creating a Step object."""
        step = Step(
            action="click",
            target={"type": "screen", "description": "Submit button"},
            description="Click the submit button",
            wait_for={"type": "text", "value": "Success"},
            params={"delay": 0.5},
        )

        assert step.action == "click"
        assert step.target["type"] == "screen"
        assert step.description == "Click the submit button"
        assert step.wait_for["value"] == "Success"
        assert step.params["delay"] == 0.5

    def test_step_to_dict(self):
        """Test converting Step to dict."""
        step = Step(
            action="type",
            target={"selector": "#input"},
            description="Type text",
            params={"text": "hello"},
        )

        result = step.to_dict()

        assert result["action"] == "type"
        assert result["target"]["selector"] == "#input"
        assert result["description"] == "Type text"
        assert result["text"] == "hello"  # params are spread into dict

    def test_step_default_values(self):
        """Test Step with default values."""
        step = Step(action="wait")

        assert step.action == "wait"
        assert step.target == {}
        assert step.description == ""
        assert step.wait_for == {}
        assert step.params == {}


class TestRetryStrategy:
    """Test RetryStrategy dataclass."""

    def test_retry_strategy_defaults(self):
        """Test default retry strategy values."""
        strategy = RetryStrategy()

        assert strategy.should_retry is True
        assert strategy.max_attempts == 3
        assert strategy.delay == 1.0
        assert strategy.alternative_action is None
        assert strategy.reason == ""

    def test_retry_strategy_custom(self):
        """Test custom retry strategy."""
        alt_step = Step(action="wait", params={"duration": 2.0})
        strategy = RetryStrategy(
            should_retry=False,
            max_attempts=5,
            delay=2.5,
            alternative_action=alt_step,
            reason="Element not found",
        )

        assert strategy.should_retry is False
        assert strategy.max_attempts == 5
        assert strategy.delay == 2.5
        assert strategy.alternative_action is alt_step
        assert strategy.reason == "Element not found"


class TestScenePlan:
    """Test ScenePlan dataclass."""

    def test_scene_plan_creation(self):
        """Test creating a ScenePlan."""
        plan = ScenePlan(
            scene_name="intro",
            goal="Welcome the user",
            steps=["Open browser", "Navigate to home page"],
            expected_state={"text": "Welcome"},
        )

        assert plan.scene_name == "intro"
        assert plan.goal == "Welcome the user"
        assert len(plan.steps) == 2
        assert plan.expected_state["text"] == "Welcome"

    def test_scene_plan_defaults(self):
        """Test ScenePlan with defaults."""
        plan = ScenePlan(scene_name="test", goal="Test goal")

        assert plan.scene_name == "test"
        assert plan.goal == "Test goal"
        assert plan.steps == []
        assert plan.expected_state == {}


class TestDirectorPlanScene:
    """Test Director.plan_scene method."""

    def test_plan_scene_basic(self):
        """Test basic scene planning."""
        director = Director()

        steps = director.plan_scene("Click the login button")

        assert isinstance(steps, list)
        assert director._current_goal == "Click the login button"
        assert director._current_step_index == 0

    def test_plan_scene_with_context(self):
        """Test scene planning with context."""
        director = Director()
        context = {
            "page": "home",
            "user": "guest",
            "constraints": ["no popups"],
        }

        steps = director.plan_scene("Navigate to settings", context)

        assert isinstance(steps, list)
        assert director._current_goal == "Navigate to settings"

    def test_plan_scene_records_history(self):
        """Test that planning records history."""
        director = Director()

        director.plan_scene("Test goal")

        assert len(director._history) >= 1
        assert director._history[-1]["event"] == "plan_scene"
        assert director._history[-1]["goal"] == "Test goal"

    def test_plan_scene_resets_index(self):
        """Test that new plan resets step index."""
        director = Director()

        # Create a plan and advance
        director.plan_scene("First goal")
        director.add_step(Step(action="click"))
        director.add_step(Step(action="wait"))
        director.decide_next_action({}, "First goal")

        # New plan should reset index
        director.plan_scene("Second goal")

        assert director._current_step_index == 0
        assert director._current_steps == []


class TestDirectorAddStep:
    """Test Director.add_step method."""

    def test_add_step(self):
        """Test adding a step to the plan."""
        director = Director()
        director.plan_scene("Test goal")

        step = Step(action="click", target={"description": "button"})
        director.add_step(step)

        assert len(director._current_steps) == 1
        assert director._current_steps[0] is step

    def test_add_multiple_steps(self):
        """Test adding multiple steps."""
        director = Director()
        director.plan_scene("Test goal")

        step1 = Step(action="navigate", params={"url": "http://example.com"})
        step2 = Step(action="click", target={"description": "login"})
        step3 = Step(action="type", params={"text": "user"})

        director.add_step(step1)
        director.add_step(step2)
        director.add_step(step3)

        assert len(director._current_steps) == 3
        assert director._current_steps[0].action == "navigate"
        assert director._current_steps[1].action == "click"
        assert director._current_steps[2].action == "type"


class TestDirectorDecideNextAction:
    """Test Director.decide_next_action method."""

    def test_decide_next_action_returns_steps_in_order(self):
        """Test steps are returned in order."""
        director = Director()
        director.plan_scene("Complete form")

        director.add_step(Step(action="click", description="first"))
        director.add_step(Step(action="type", description="second"))
        director.add_step(Step(action="submit", description="third"))

        observation = {}

        step1 = director.decide_next_action(observation, "Complete form")
        step2 = director.decide_next_action(observation, "Complete form")
        step3 = director.decide_next_action(observation, "Complete form")

        assert step1.description == "first"
        assert step2.description == "second"
        assert step3.description == "third"

    def test_decide_next_action_returns_none_when_empty(self):
        """Test returns None when no steps."""
        director = Director()
        director.plan_scene("Test")

        result = director.decide_next_action({}, "Test")

        assert result is None

    def test_decide_next_action_returns_none_when_complete(self):
        """Test returns None when all steps consumed."""
        director = Director()
        director.plan_scene("Test")
        director.add_step(Step(action="wait"))

        # Consume the only step
        director.decide_next_action({}, "Test")

        # No more steps
        result = director.decide_next_action({}, "Test")

        assert result is None

    def test_decide_next_action_detects_goal_achieved(self):
        """Test goal achievement detection."""
        director = Director()
        director.plan_scene("Create file")
        director.add_step(Step(action="type"))

        observation = {"ocr_text": "File created successfully"}

        # Should return None when goal appears achieved
        result = director.decide_next_action(observation, "Create file")

        assert result is None


class TestDirectorAnalyzeFailure:
    """Test Director.analyze_failure method."""

    def test_analyze_timeout_failure(self):
        """Test timeout failure analysis."""
        director = Director()
        observation = {"terminal_output": "Error: timeout waiting for element"}
        step = Step(action="click")

        strategy = director.analyze_failure(observation, step)

        assert strategy.should_retry is True
        assert strategy.delay >= 2.0
        assert "timeout" in strategy.reason.lower()

    def test_analyze_not_found_failure(self):
        """Test element not found failure analysis."""
        director = Director()
        observation = {"ocr_text": "Element not found on page"}
        step = Step(action="click")

        strategy = director.analyze_failure(observation, step)

        assert strategy.should_retry is True
        assert "not found" in strategy.reason.lower()

    def test_analyze_permission_failure(self):
        """Test permission denied failure (no retry)."""
        director = Director()
        observation = {"terminal_output": "Permission denied: cannot write"}
        step = Step(action="terminal")

        strategy = director.analyze_failure(observation, step)

        assert strategy.should_retry is False
        assert "permission" in strategy.reason.lower()

    def test_analyze_network_failure(self):
        """Test network error failure analysis."""
        director = Director()
        observation = {"terminal_output": "network error: connection refused"}
        step = Step(action="navigate")

        strategy = director.analyze_failure(observation, step)

        assert strategy.should_retry is True
        assert strategy.delay >= 3.0

    def test_analyze_unknown_failure(self):
        """Test unknown failure defaults to retry."""
        director = Director()
        observation = {"ocr_text": "Something unexpected happened"}
        step = Step(action="click")

        strategy = director.analyze_failure(observation, step)

        assert strategy.should_retry is True
        assert "unknown" in strategy.reason.lower()


class TestDirectorSuggestRecovery:
    """Test Director.suggest_recovery method."""

    def test_suggest_recovery_for_timeout(self):
        """Test recovery suggestion for timeout."""
        director = Director()
        strategy = RetryStrategy(
            should_retry=True,
            reason="Timeout waiting for element",
        )

        recovery = director.suggest_recovery(strategy)

        assert recovery is not None
        assert recovery.action == "wait"

    def test_suggest_recovery_for_not_found(self):
        """Test recovery suggestion for element not found."""
        director = Director()
        strategy = RetryStrategy(
            should_retry=True,
            reason="Element not found on screen",
        )

        recovery = director.suggest_recovery(strategy)

        assert recovery is not None
        assert recovery.action == "scroll"

    def test_suggest_recovery_uses_alternative(self):
        """Test that alternative action is used when provided."""
        director = Director()
        alt_step = Step(action="keyboard", params={"key": "Tab"})
        strategy = RetryStrategy(
            should_retry=True,
            alternative_action=alt_step,
            reason="Original failed",
        )

        recovery = director.suggest_recovery(strategy)

        assert recovery is alt_step

    def test_suggest_recovery_none_for_no_retry(self):
        """Test None returned when should not retry."""
        director = Director()
        strategy = RetryStrategy(should_retry=False)

        recovery = director.suggest_recovery(strategy)

        assert recovery is None


class TestDirectorEvaluateProgress:
    """Test Director.evaluate_progress method."""

    def test_evaluate_progress_no_goal(self):
        """Test progress with no goal set."""
        director = Director()

        result = director.evaluate_progress({})

        assert result["completed"] is False
        assert result["progress"] == 0.0

    def test_evaluate_progress_with_steps(self):
        """Test progress tracking with steps."""
        director = Director()
        director.plan_scene("Test")
        director.add_step(Step(action="click"))
        director.add_step(Step(action="type"))
        director.add_step(Step(action="submit"))

        # Execute first step
        director.decide_next_action({}, "Test")

        result = director.evaluate_progress({})

        assert result["steps_completed"] == 1
        assert result["steps_total"] == 3
        assert 0 < result["progress"] < 1

    def test_evaluate_progress_completed(self):
        """Test progress when goal achieved."""
        director = Director()
        director.plan_scene("Create file")

        observation = {"terminal_output": "Created file successfully"}

        result = director.evaluate_progress(observation)

        assert result["completed"] is True
        assert result["confidence"] >= 0.8


class TestDirectorReset:
    """Test Director.reset method."""

    def test_reset_clears_state(self):
        """Test reset clears all state."""
        director = Director()
        director.plan_scene("Test")
        director.add_step(Step(action="click"))
        director.decide_next_action({}, "Test")

        director.reset()

        assert director._current_plan is None
        assert director._current_steps == []
        assert director._current_step_index == 0
        assert director._current_goal == ""
        assert director._history == []


class TestDetectSuccess:
    """Test detect_success function."""

    def test_detect_text_match(self):
        """Test text matching."""
        observation = {"ocr_text": "Operation completed successfully"}
        expected = {"text": "completed"}

        assert detect_success(observation, expected) is True

    def test_detect_text_no_match(self):
        """Test text not matching."""
        observation = {"ocr_text": "Loading..."}
        expected = {"text": "completed"}

        assert detect_success(observation, expected) is False

    def test_detect_multiple_texts(self):
        """Test multiple required texts."""
        observation = {"ocr_text": "User created. Email sent."}
        expected = {"texts": ["created", "sent"]}

        assert detect_success(observation, expected) is True

    def test_detect_multiple_texts_missing_one(self):
        """Test multiple texts with one missing."""
        observation = {"ocr_text": "User created."}
        expected = {"texts": ["created", "sent"]}

        assert detect_success(observation, expected) is False

    def test_detect_terminal_text(self):
        """Test terminal output matching."""
        observation = {"terminal_output": "Build succeeded"}
        expected = {"terminal": "succeeded"}

        assert detect_success(observation, expected) is True

    def test_detect_window_title(self):
        """Test window title matching."""
        observation = {"window": {"title": "Settings - App"}}
        expected = {"window_title": "Settings"}

        assert detect_success(observation, expected) is True

    def test_detect_not_text(self):
        """Test text that should NOT appear."""
        observation = {"ocr_text": "Operation completed"}
        expected = {"not_text": "error"}

        assert detect_success(observation, expected) is True

    def test_detect_not_text_fails_when_present(self):
        """Test not_text fails when text is present."""
        observation = {"ocr_text": "Error occurred"}
        expected = {"not_text": "error"}

        assert detect_success(observation, expected) is False

    def test_detect_any_text(self):
        """Test any_text matching (at least one)."""
        observation = {"ocr_text": "Status: Pending"}
        expected = {"any_text": ["Complete", "Pending", "Active"]}

        assert detect_success(observation, expected) is True

    def test_detect_any_text_none_match(self):
        """Test any_text fails when none match."""
        observation = {"ocr_text": "Status: Unknown"}
        expected = {"any_text": ["Complete", "Pending", "Active"]}

        assert detect_success(observation, expected) is False


class TestObservationToPrompt:
    """Test observation_to_prompt function."""

    def test_basic_observation(self):
        """Test converting basic observation."""
        observation = {
            "ocr_text": "Hello World",
            "terminal_output": "$ ls\nfile.txt",
        }

        result = observation_to_prompt(observation)

        assert "Hello World" in result
        assert "file.txt" in result
        assert "OCR Text" in result
        assert "Terminal Output" in result

    def test_empty_observation(self):
        """Test empty observation."""
        observation = {}

        result = observation_to_prompt(observation)

        assert "No observation data available" in result

    def test_observation_with_window(self):
        """Test observation with window info."""
        observation = {
            "window": {"title": "My App", "app": "Firefox"},
        }

        result = observation_to_prompt(observation)

        assert "My App" in result
        assert "Firefox" in result

    def test_observation_with_screenshot_path(self):
        """Test screenshot path is included."""
        observation = {
            "screenshot_path": "/tmp/screenshot.png",
        }

        result = observation_to_prompt(observation)

        assert "screenshot.png" in result


class TestSummarizeContext:
    """Test summarize_context function."""

    def test_truncate_long_ocr(self):
        """Test OCR text is truncated."""
        long_ocr = "x" * 5000
        observation = {"ocr_text": long_ocr}

        result = summarize_context(observation, max_ocr_chars=1000)

        assert len(result["ocr_text"]) < len(long_ocr)
        assert "truncated" in result["ocr_text"]

    def test_truncate_terminal_output(self):
        """Test terminal output is truncated."""
        lines = ["line " + str(i) for i in range(100)]
        observation = {"terminal_output": "\n".join(lines)}

        result = summarize_context(observation, max_terminal_lines=10)

        truncated_lines = result["terminal_output"].split("\n")
        assert len(truncated_lines) <= 10

    def test_screenshot_placeholder(self):
        """Test screenshot base64 is replaced with placeholder."""
        observation = {"screenshot_base64": "abc123verylongbase64data"}

        result = summarize_context(observation)

        assert "compressed image data" in result["screenshot_base64"]


class TestCompressScreenshot:
    """Test compress_screenshot function."""

    def create_test_image(self, width=200, height=200):
        """Create a test image."""
        img = Image.new("RGB", (width, height), color="blue")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_compress_basic(self):
        """Test basic compression."""
        image_data = self.create_test_image()

        result = compress_screenshot(image_data)

        assert isinstance(result, str)
        # Should be valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_compress_base64_input(self):
        """Test compression with base64 input."""
        image_data = self.create_test_image()
        b64_input = base64.b64encode(image_data).decode("utf-8")

        result = compress_screenshot(b64_input)

        assert isinstance(result, str)

    def test_compress_resizes_large_image(self):
        """Test large images are resized."""
        image_data = self.create_test_image(width=3000, height=2000)

        result = compress_screenshot(image_data, max_size=1000)

        # Decode and check size
        decoded = base64.b64decode(result)
        img = Image.open(io.BytesIO(decoded))
        assert img.width <= 1000
        assert img.height <= 1000

    def test_compress_handles_rgba(self):
        """Test RGBA images are converted."""
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_data = buffer.getvalue()

        result = compress_screenshot(image_data)

        # Should succeed without error
        assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
