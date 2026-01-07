"""Keyboard control using pyautogui."""

import time
from typing import Any

import pyautogui

from programmatic_demo.utils.output import error_response, success_response
from programmatic_demo.utils.timing import typing_delay

# Key name mapping for pyautogui
KEY_MAPPING = {
    "enter": "return",
    "return": "return",
    "tab": "tab",
    "escape": "escape",
    "esc": "escape",
    "space": "space",
    "backspace": "backspace",
    "delete": "delete",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "home": "home",
    "end": "end",
    "pageup": "pageup",
    "pagedown": "pagedown",
    "f1": "f1",
    "f2": "f2",
    "f3": "f3",
    "f4": "f4",
    "f5": "f5",
    "f6": "f6",
    "f7": "f7",
    "f8": "f8",
    "f9": "f9",
    "f10": "f10",
    "f11": "f11",
    "f12": "f12",
}

# Modifier key mapping
MODIFIER_MAPPING = {
    "cmd": "command",
    "command": "command",
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "option": "alt",
    "shift": "shift",
}


class Keyboard:
    """Keyboard controller with human-like typing."""

    def __init__(self) -> None:
        """Initialize the keyboard controller."""
        # Disable pyautogui failsafe for automated use
        pyautogui.FAILSAFE = False

    def type_text(self, text: str, delay_ms: int = 50) -> dict[str, Any]:
        """Type text with human-like delays.

        Args:
            text: Text to type.
            delay_ms: Base delay between keystrokes in ms.

        Returns:
            Success dict with text and duration.
        """
        try:
            start_time = time.time()

            for char in text:
                pyautogui.press(char) if len(char) == 1 else pyautogui.write(char)
                time.sleep(typing_delay(delay_ms))

            duration = time.time() - start_time

            return success_response(
                "keyboard_type",
                {"text": text, "duration": round(duration, 2), "chars": len(text)},
            )
        except Exception as e:
            return error_response(
                "type_failed",
                f"Failed to type text: {str(e)}",
                recoverable=True,
            )

    def press(self, key: str) -> dict[str, Any]:
        """Press a key.

        Args:
            key: Key name (enter, tab, escape, arrows, f1-f12, etc.).

        Returns:
            Success dict.
        """
        key_lower = key.lower()

        # Map to pyautogui key name
        pyautogui_key = KEY_MAPPING.get(key_lower, key_lower)

        try:
            pyautogui.press(pyautogui_key)
            return success_response("keyboard_press", {"key": key})
        except Exception as e:
            return error_response(
                "press_failed",
                f"Failed to press key '{key}': {str(e)}",
                recoverable=True,
                suggestion=f"Valid keys: {', '.join(KEY_MAPPING.keys())}",
            )

    def hotkey(self, keys_str: str) -> dict[str, Any]:
        """Press a key combination.

        Args:
            keys_str: Key combination like 'cmd+shift+p'.

        Returns:
            Success dict.
        """
        try:
            # Parse keys from string like "cmd+shift+p"
            parts = [k.strip().lower() for k in keys_str.split("+")]

            # Map to pyautogui key names
            mapped_keys = []
            for part in parts:
                if part in MODIFIER_MAPPING:
                    mapped_keys.append(MODIFIER_MAPPING[part])
                elif part in KEY_MAPPING:
                    mapped_keys.append(KEY_MAPPING[part])
                else:
                    mapped_keys.append(part)

            pyautogui.hotkey(*mapped_keys)
            return success_response("keyboard_hotkey", {"keys": keys_str, "parsed": mapped_keys})
        except Exception as e:
            return error_response(
                "hotkey_failed",
                f"Failed to press hotkey '{keys_str}': {str(e)}",
                recoverable=True,
            )


# Singleton instance for CLI usage
_keyboard_instance: Keyboard | None = None


def get_keyboard() -> Keyboard:
    """Get or create the singleton Keyboard instance."""
    global _keyboard_instance
    if _keyboard_instance is None:
        _keyboard_instance = Keyboard()
    return _keyboard_instance
