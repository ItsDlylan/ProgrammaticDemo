"""JSON response formatting utilities."""

import time
from typing import Any


def success_response(action: str, result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a success response dict.

    Args:
        action: The action that was performed.
        result: Optional result data to include.

    Returns:
        A dict with success=True, action, timestamp, and optional result.
    """
    response: dict[str, Any] = {
        "success": True,
        "action": action,
        "timestamp": time.time(),
    }
    if result is not None:
        response["result"] = result
    return response


def error_response(
    error_type: str,
    message: str,
    recoverable: bool = True,
    suggestion: str | None = None,
) -> dict[str, Any]:
    """Create an error response dict.

    Args:
        error_type: Category of error (e.g., 'timeout', 'not_found', 'permission').
        message: Human-readable error message.
        recoverable: Whether the error can be retried or recovered from.
        suggestion: Optional suggestion for how to fix/retry.

    Returns:
        A dict with success=False and error details.
    """
    response: dict[str, Any] = {
        "success": False,
        "error": {
            "type": error_type,
            "message": message,
            "recoverable": recoverable,
        },
        "timestamp": time.time(),
    }
    if suggestion is not None:
        response["error"]["suggestion"] = suggestion
    return response
