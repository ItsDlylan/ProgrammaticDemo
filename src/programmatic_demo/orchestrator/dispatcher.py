"""Action dispatcher for routing actions to appropriate actuators.

The ActionDispatcher routes actions from script steps to the
appropriate actuator based on action type.
"""

from typing import Any


class ActionDispatcher:
    """Dispatches actions to appropriate actuators.

    Routes script step actions to mouse, keyboard, browser,
    or other actuators based on the action type.
    """

    def __init__(self) -> None:
        """Initialize the ActionDispatcher."""
        self._mouse = None
        self._keyboard = None
        self._browser = None

    def dispatch(self, step: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a step to the appropriate actuator.

        Args:
            step: Step dict containing action type and parameters.

        Returns:
            Result dict from the actuator.
        """
        from programmatic_demo.actuators.keyboard import get_keyboard
        from programmatic_demo.actuators.mouse import get_mouse

        action_type = step.get("action", "").lower()

        if action_type == "click":
            mouse = get_mouse()
            target = step.get("target", {})
            x = target.get("x", 0)
            y = target.get("y", 0)
            return mouse.click_at(x, y)

        elif action_type == "type":
            keyboard = get_keyboard()
            text = step.get("text", "")
            return keyboard.type_text(text)

        elif action_type == "press":
            keyboard = get_keyboard()
            key = step.get("key", "")
            return keyboard.press(key)

        elif action_type == "hotkey":
            keyboard = get_keyboard()
            keys = step.get("keys", "")
            return keyboard.hotkey(keys)

        elif action_type == "move":
            mouse = get_mouse()
            target = step.get("target", {})
            x = target.get("x", 0)
            y = target.get("y", 0)
            return mouse.move_to(x, y)

        elif action_type == "scroll":
            mouse = get_mouse()
            direction = step.get("direction", "down")
            amount = step.get("amount", 3)
            return mouse.scroll(direction, amount)

        elif action_type == "navigate":
            from programmatic_demo.actuators.browser import get_browser
            browser = get_browser()
            url = step.get("url", "")
            return browser.goto(url)

        elif action_type == "wait":
            import time
            from programmatic_demo.utils.output import success_response

            seconds = step.get("seconds", 1)
            time.sleep(seconds)
            return success_response("wait_complete", {"seconds": seconds})

        elif action_type == "terminal":
            from programmatic_demo.actuators.terminal import get_terminal
            terminal = get_terminal()
            command = step.get("command", "")
            return terminal.exec(command)

        return {
            "success": False,
            "error": f"Unknown action type: {action_type}",
        }

    def dispatch_click(self, target: str | dict[str, Any]) -> dict[str, Any]:
        """Dispatch a click action with target resolution.

        Args:
            target: Target description string or dict with x,y coordinates.

        Returns:
            Result dict from the mouse actuator.
        """
        from programmatic_demo.actuators.mouse import get_mouse
        from programmatic_demo.nlp.resolver import get_resolver

        mouse = get_mouse()

        if isinstance(target, str):
            resolver = get_resolver()
            resolved = resolver.resolve(target)
            if resolved is None:
                return {"success": False, "error": f"Could not resolve target: {target}"}
            return mouse.click_at(resolved.coords[0], resolved.coords[1])
        else:
            x = target.get("x", 0)
            y = target.get("y", 0)
            return mouse.click_at(x, y)

    def dispatch_type(self, text: str) -> dict[str, Any]:
        """Dispatch a type action.

        Args:
            text: Text to type.

        Returns:
            Result dict from the keyboard actuator.
        """
        from programmatic_demo.actuators.keyboard import get_keyboard
        keyboard = get_keyboard()
        return keyboard.type_text(text)

    def dispatch_press(self, key: str) -> dict[str, Any]:
        """Dispatch a key press action.

        Args:
            key: Key name to press.

        Returns:
            Result dict from the keyboard actuator.
        """
        from programmatic_demo.actuators.keyboard import get_keyboard
        keyboard = get_keyboard()
        return keyboard.press(key)

    def dispatch_scroll(self, direction: str, amount: int = 3) -> dict[str, Any]:
        """Dispatch a scroll action.

        Args:
            direction: Scroll direction (up, down, left, right).
            amount: Number of scroll clicks.

        Returns:
            Result dict from the mouse actuator.
        """
        from programmatic_demo.actuators.mouse import get_mouse
        mouse = get_mouse()
        return mouse.scroll(direction, amount)

    def dispatch_wait(
        self,
        condition: str | dict[str, Any],
        timeout: float = 30.0,
        interval: float = 0.5,
    ) -> dict[str, Any]:
        """Dispatch a wait action with polling.

        Args:
            condition: Condition to wait for (text to appear or dict).
            timeout: Maximum wait time in seconds.
            interval: Polling interval in seconds.

        Returns:
            Result dict indicating if condition was met.
        """
        import time
        from programmatic_demo.nlp.resolver import get_resolver
        from programmatic_demo.utils.output import error_response, success_response

        resolver = get_resolver()
        start_time = time.time()

        while time.time() - start_time < timeout:
            if isinstance(condition, str):
                resolved = resolver.resolve(condition)
                if resolved is not None:
                    return success_response("condition_met", {"found": condition})
            time.sleep(interval)

        return error_response("wait_timeout", f"Condition not met: {condition}")

    def dispatch_navigate(self, url: str) -> dict[str, Any]:
        """Dispatch a navigate action.

        Args:
            url: URL to navigate to.

        Returns:
            Result dict from the browser actuator.
        """
        from programmatic_demo.actuators.browser import get_browser
        browser = get_browser()
        return browser.goto(url)

    def dispatch_terminal(self, command: str) -> dict[str, Any]:
        """Dispatch a terminal command.

        Args:
            command: Command to execute.

        Returns:
            Result dict from the terminal actuator.
        """
        from programmatic_demo.actuators.terminal import get_terminal
        terminal = get_terminal()
        return terminal.exec(command)


# Singleton instance
_dispatcher: ActionDispatcher | None = None


def get_dispatcher() -> ActionDispatcher:
    """Get or create the singleton ActionDispatcher instance."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = ActionDispatcher()
    return _dispatcher
