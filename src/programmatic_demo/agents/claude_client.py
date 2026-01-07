"""Claude API client wrapper for agent communication.

This module provides a wrapper around the Anthropic Claude API
for use by the Director and other agents.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    """A message in a conversation.

    Attributes:
        role: Role of the message sender (user, assistant)
        content: Message content (text or list of content blocks)
    """

    role: str
    content: str | list[dict[str, Any]]


@dataclass
class Response:
    """A response from the Claude API.

    Attributes:
        content: Response content text
        stop_reason: Why the response ended
        usage: Token usage information
    """

    content: str
    stop_reason: str | None = None
    usage: dict[str, int] | None = None


class ClaudeClient:
    """Client for communicating with the Claude API.

    Wraps the Anthropic API with convenience methods for
    sending messages, including images, and managing conversations.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        """Initialize the Claude client.

        Args:
            api_key: Anthropic API key, loaded from env if None.
            model: Model to use for requests.
        """
        self._api_key = api_key
        self._model = model
        self._conversation: list[Message] = []

    @property
    def model(self) -> str:
        """Get the model being used."""
        return self._model

    @property
    def conversation(self) -> list[Message]:
        """Get the current conversation history."""
        return self._conversation

    def send_message(
        self,
        message: str,
        system: str | None = None,
    ) -> Response:
        """Send a text message to Claude.

        Args:
            message: The message text to send.
            system: Optional system prompt.

        Returns:
            Response from Claude.
        """
        raise NotImplementedError("send_message not yet implemented")

    def send_with_image(
        self,
        message: str,
        image_path: str | None = None,
        image_base64: str | None = None,
        system: str | None = None,
    ) -> Response:
        """Send a message with an image to Claude.

        Args:
            message: The message text to send.
            image_path: Path to image file (if providing file).
            image_base64: Base64-encoded image (if providing data).
            system: Optional system prompt.

        Returns:
            Response from Claude.
        """
        raise NotImplementedError("send_with_image not yet implemented")

    def clear_conversation(self) -> None:
        """Clear the conversation history."""
        self._conversation.clear()

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history.

        Args:
            role: Message role (user or assistant).
            content: Message content.
        """
        self._conversation.append(Message(role=role, content=content))
