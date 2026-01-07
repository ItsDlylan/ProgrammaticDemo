"""INT-006: Test NLP action parsing accuracy.

This test verifies that:
1. Various natural language commands parse correctly
2. Correct ActionIntent is returned
3. Edge cases and ambiguous input are handled
4. Confidence scores are set appropriately
"""

import pytest

from programmatic_demo.nlp.parser import (
    ActionIntent,
    parse_action,
    parse_click,
    parse_key,
    parse_navigate,
    parse_scroll,
    parse_type,
    parse_wait,
)


class TestClickParsing:
    """Test click action parsing."""

    @pytest.mark.parametrize(
        "text,expected_target",
        [
            ("click the Submit button", "Submit"),
            ("click on the Login button", "Login"),
            ("click Submit", "Submit"),
            ("tap on Save", "Save"),
            ("tap the Cancel button", "Cancel"),
            ("press the OK button", "OK"),
            ("select the dropdown", "dropdown"),
            ("click on the menu item", "menu item"),
        ],
    )
    def test_click_action_parsing(self, text, expected_target):
        """Test that click actions are parsed correctly."""
        intent = parse_click(text)

        assert intent is not None
        assert intent.action_type == "click"
        assert intent.target_description == expected_target
        assert intent.confidence == 1.0

    def test_click_action_via_parse_action(self):
        """Test click parsing through main parse_action function."""
        intent = parse_action("click the Submit button")

        assert intent is not None
        assert intent.action_type == "click"
        assert intent.target_description == "Submit"


class TestTypeParsing:
    """Test type action parsing."""

    @pytest.mark.parametrize(
        "text,expected_text,expected_target",
        [
            ("type hello world", "hello world", None),
            ("type 'test input'", "test input", None),
            ("enter search query", "search query", None),
            ("type hello in the search field", "hello", "search field"),
            ("enter password into the password input", "password", "password input"),
            ("write test text", "test text", None),
            ("input username", "username", None),
        ],
    )
    def test_type_action_parsing(self, text, expected_text, expected_target):
        """Test that type actions are parsed correctly."""
        intent = parse_type(text)

        assert intent is not None
        assert intent.action_type == "type"
        assert intent.params is not None
        assert intent.params["text"] == expected_text
        assert intent.target_description == expected_target
        assert intent.confidence == 1.0


class TestKeyPressParsing:
    """Test key press action parsing."""

    @pytest.mark.parametrize(
        "text,expected_key",
        [
            ("press Enter", "enter"),
            ("press enter", "enter"),
            ("hit Tab", "tab"),
            ("push Escape", "escape"),
            ("press Esc", "escape"),
            ("press the escape key", "escape"),
            ("press space", "space"),
            ("press spacebar", "space"),
            ("press delete", "delete"),
            ("press backspace", "backspace"),
        ],
    )
    def test_key_press_parsing(self, text, expected_key):
        """Test that key press actions are parsed correctly."""
        intent = parse_key(text)

        assert intent is not None
        assert intent.action_type == "press"
        assert intent.params is not None
        assert intent.params["key"] == expected_key
        assert intent.confidence == 1.0

    def test_press_button_not_key_press(self):
        """Test that 'press the button' is not parsed as key press."""
        intent = parse_key("press the Submit button")
        assert intent is None


class TestScrollParsing:
    """Test scroll action parsing."""

    @pytest.mark.parametrize(
        "text,expected_direction,expected_target",
        [
            ("scroll down", "down", None),
            ("scroll up", "up", None),
            ("scroll left", "left", None),
            ("scroll right", "right", None),
            ("scroll down to the footer", "down", "footer"),
            ("scroll up on the menu", "up", "menu"),
            ("scroll down in the list", "down", "list"),
        ],
    )
    def test_scroll_action_parsing(self, text, expected_direction, expected_target):
        """Test that scroll actions are parsed correctly."""
        intent = parse_scroll(text)

        assert intent is not None
        assert intent.action_type == "scroll"
        assert intent.params is not None
        assert intent.params["direction"] == expected_direction
        assert intent.target_description == expected_target
        assert intent.confidence == 1.0


class TestWaitParsing:
    """Test wait action parsing."""

    @pytest.mark.parametrize(
        "text,expected_type,expected_param",
        [
            ("wait 5 seconds", "duration", 5),
            ("wait 10 s", "duration", 10),
            ("wait 2 second", "duration", 2),
            ("pause 3 seconds", "duration", 3),
        ],
    )
    def test_wait_duration_parsing(self, text, expected_type, expected_param):
        """Test that wait duration actions are parsed correctly."""
        intent = parse_wait(text)

        assert intent is not None
        assert intent.action_type == "wait"
        assert intent.params is not None
        assert intent.params["type"] == expected_type
        assert intent.params["seconds"] == expected_param

    @pytest.mark.parametrize(
        "text,expected_condition",
        [
            ("wait for the loading screen", "the loading screen"),
            ("until the button appears", "button"),
            ("wait until the modal appears", "modal"),
        ],
    )
    def test_wait_condition_parsing(self, text, expected_condition):
        """Test that wait condition actions are parsed correctly."""
        intent = parse_wait(text)

        assert intent is not None
        assert intent.action_type == "wait"
        assert intent.params is not None
        assert intent.params["type"] == "text"
        assert expected_condition in intent.params["condition"]


class TestNavigateParsing:
    """Test navigate action parsing."""

    @pytest.mark.parametrize(
        "text,expected_dest,expected_type",
        [
            ("go to https://example.com", "https://example.com", "url"),
            ("navigate to https://google.com", "https://google.com", "url"),
            ("open google.com", "google.com", "url"),
            ("visit example.org", "example.org", "url"),
            ("go to the dashboard", "the dashboard", "app"),
            ("open Settings", "Settings", "app"),
            ("navigate to home page", "home page", "app"),
        ],
    )
    def test_navigate_action_parsing(self, text, expected_dest, expected_type):
        """Test that navigate actions are parsed correctly."""
        intent = parse_navigate(text)

        assert intent is not None
        assert intent.action_type == "navigate"
        assert intent.target_description == expected_dest
        assert intent.params is not None
        assert intent.params["type"] == expected_type


class TestParseActionIntegration:
    """Test the main parse_action function that tries all parsers."""

    def test_parse_action_click(self):
        """Test parse_action returns click for click-like text."""
        intent = parse_action("click the button")
        assert intent is not None
        assert intent.action_type == "click"

    def test_parse_action_type(self):
        """Test parse_action returns type for type-like text."""
        intent = parse_action("type hello world")
        assert intent is not None
        assert intent.action_type == "type"

    def test_parse_action_press(self):
        """Test parse_action returns press for key press text."""
        intent = parse_action("press Enter")
        assert intent is not None
        assert intent.action_type == "press"

    def test_parse_action_scroll(self):
        """Test parse_action returns scroll for scroll text."""
        intent = parse_action("scroll down")
        assert intent is not None
        assert intent.action_type == "scroll"

    def test_parse_action_wait(self):
        """Test parse_action returns wait for wait text."""
        intent = parse_action("wait 5 seconds")
        assert intent is not None
        assert intent.action_type == "wait"

    def test_parse_action_navigate(self):
        """Test parse_action returns navigate for navigate text."""
        intent = parse_action("go to https://example.com")
        assert intent is not None
        assert intent.action_type == "navigate"

    def test_parse_action_returns_none_for_unrecognized(self):
        """Test parse_action returns None for unrecognized text."""
        intent = parse_action("do something random")
        assert intent is None


class TestEdgeCases:
    """Test edge cases and ambiguous input."""

    def test_empty_string(self):
        """Test that empty string returns None."""
        intent = parse_action("")
        assert intent is None

    def test_whitespace_only(self):
        """Test that whitespace-only string returns None."""
        intent = parse_action("   ")
        assert intent is None

    def test_case_insensitivity(self):
        """Test that parsing is case-insensitive."""
        intent_lower = parse_action("click the button")
        intent_upper = parse_action("CLICK THE BUTTON")
        intent_mixed = parse_action("Click The Button")

        assert intent_lower is not None
        assert intent_upper is not None
        assert intent_mixed is not None
        assert intent_lower.action_type == intent_upper.action_type == intent_mixed.action_type

    def test_press_enter_is_key_not_click(self):
        """Test that 'press Enter' is key press, not click."""
        intent = parse_action("press Enter")
        assert intent is not None
        assert intent.action_type == "press"
        assert intent.params["key"] == "enter"


class TestConfidenceScores:
    """Test confidence score handling."""

    def test_confidence_is_float(self):
        """Test that confidence is a float."""
        intent = parse_action("click the button")
        assert intent is not None
        assert isinstance(intent.confidence, float)

    def test_confidence_in_range(self):
        """Test that confidence is between 0 and 1."""
        intent = parse_action("click the button")
        assert intent is not None
        assert 0.0 <= intent.confidence <= 1.0

    def test_high_confidence_for_exact_match(self):
        """Test high confidence for exact pattern matches."""
        intent = parse_action("click the Submit button")
        assert intent is not None
        assert intent.confidence >= 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
