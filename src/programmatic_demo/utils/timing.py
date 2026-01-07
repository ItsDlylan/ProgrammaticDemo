"""Human-like timing and delay utilities."""

import random
import time


def random_delay(min_ms: int, max_ms: int) -> None:
    """Sleep for a random duration between min_ms and max_ms milliseconds.

    Args:
        min_ms: Minimum delay in milliseconds.
        max_ms: Maximum delay in milliseconds.
    """
    delay_ms = random.randint(min_ms, max_ms)
    time.sleep(delay_ms / 1000.0)


def typing_delay(base_ms: int = 50) -> float:
    """Get a jittered delay for human-like typing.

    Returns a delay with ±30% jitter around the base value.

    Args:
        base_ms: Base delay in milliseconds (default 50ms).

    Returns:
        Delay in seconds (for use with time.sleep).
    """
    jitter = random.uniform(-0.3, 0.3)
    delay_ms = base_ms * (1 + jitter)
    return delay_ms / 1000.0


def hover_pause() -> float:
    """Get a random pause duration for hovering before clicking.

    Returns a delay between 50-150ms to simulate natural mouse behavior.

    Returns:
        Delay in seconds (for use with time.sleep).
    """
    delay_ms = random.randint(50, 150)
    return delay_ms / 1000.0
