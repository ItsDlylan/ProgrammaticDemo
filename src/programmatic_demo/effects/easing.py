"""Easing functions for smooth animation effects.

This module provides a comprehensive set of easing functions for use in
zoom effects, transitions, and other animations. All functions take a
progress value t in [0, 1] and return an eased value in [0, 1].

Usage:
    from programmatic_demo.effects.easing import ease_out_expo, get_easing

    # Direct use
    eased = ease_out_expo(0.5)  # Returns ~0.97

    # Registry lookup
    ease_fn = get_easing("ease-out-expo")
    eased = ease_fn(0.5)
"""

import math
from dataclasses import dataclass
from typing import Callable, Dict, Optional

# Type alias for easing functions
EasingFunction = Callable[[float], float]


# =============================================================================
# Linear Easing
# =============================================================================

def linear(t: float) -> float:
    """Linear interpolation (no easing)."""
    return t


# =============================================================================
# Quadratic Easing (power of 2)
# =============================================================================

def ease_in_quad(t: float) -> float:
    """Quadratic ease-in: slow start."""
    return t * t


def ease_out_quad(t: float) -> float:
    """Quadratic ease-out: slow end."""
    return 1 - (1 - t) * (1 - t)


def ease_in_out_quad(t: float) -> float:
    """Quadratic ease-in-out: slow start and end."""
    if t < 0.5:
        return 2 * t * t
    return 1 - pow(-2 * t + 2, 2) / 2


# =============================================================================
# Cubic Easing (power of 3)
# =============================================================================

def ease_in_cubic(t: float) -> float:
    """Cubic ease-in: slow start."""
    return t * t * t


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out: slow end. Good for zoom-in animations."""
    return 1 - pow(1 - t, 3)


def ease_in_out_cubic(t: float) -> float:
    """Cubic ease-in-out: smooth start and end. Best for general animations."""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


# =============================================================================
# Quartic Easing (power of 4)
# =============================================================================

def ease_in_quart(t: float) -> float:
    """Quartic ease-in: very slow start."""
    return t * t * t * t


def ease_out_quart(t: float) -> float:
    """Quartic ease-out: very slow end."""
    return 1 - pow(1 - t, 4)


def ease_in_out_quart(t: float) -> float:
    """Quartic ease-in-out: very smooth start and end."""
    if t < 0.5:
        return 8 * t * t * t * t
    return 1 - pow(-2 * t + 2, 4) / 2


# =============================================================================
# Quintic Easing (power of 5)
# =============================================================================

def ease_in_quint(t: float) -> float:
    """Quintic ease-in: extremely slow start."""
    return t * t * t * t * t


def ease_out_quint(t: float) -> float:
    """Quintic ease-out: extremely slow end."""
    return 1 - pow(1 - t, 5)


def ease_in_out_quint(t: float) -> float:
    """Quintic ease-in-out: extremely smooth."""
    if t < 0.5:
        return 16 * t * t * t * t * t
    return 1 - pow(-2 * t + 2, 5) / 2


# =============================================================================
# Exponential Easing (base 2)
# =============================================================================

def ease_in_expo(t: float) -> float:
    """Exponential ease-in: very slow start, fast acceleration.
    Good for zoom-out animations."""
    if t == 0:
        return 0
    return pow(2, 10 * t - 10)


def ease_out_expo(t: float) -> float:
    """Exponential ease-out: fast start, very slow end.
    Good for zoom-in animations (Screen Studio style)."""
    if t == 1:
        return 1
    return 1 - pow(2, -10 * t)


def ease_in_out_expo(t: float) -> float:
    """Exponential ease-in-out: dramatic start and end."""
    if t == 0:
        return 0
    if t == 1:
        return 1
    if t < 0.5:
        return pow(2, 20 * t - 10) / 2
    return (2 - pow(2, -20 * t + 10)) / 2


# =============================================================================
# Sine Easing
# =============================================================================

def ease_in_sine(t: float) -> float:
    """Sinusoidal ease-in: gentle slow start."""
    return 1 - math.cos((t * math.pi) / 2)


def ease_out_sine(t: float) -> float:
    """Sinusoidal ease-out: gentle slow end."""
    return math.sin((t * math.pi) / 2)


def ease_in_out_sine(t: float) -> float:
    """Sinusoidal ease-in-out: gentle transitions."""
    return -(math.cos(math.pi * t) - 1) / 2


# =============================================================================
# Circular Easing
# =============================================================================

def ease_in_circ(t: float) -> float:
    """Circular ease-in: accelerating from zero."""
    return 1 - math.sqrt(1 - pow(t, 2))


def ease_out_circ(t: float) -> float:
    """Circular ease-out: decelerating to zero."""
    return math.sqrt(1 - pow(t - 1, 2))


def ease_in_out_circ(t: float) -> float:
    """Circular ease-in-out: smooth acceleration and deceleration."""
    if t < 0.5:
        return (1 - math.sqrt(1 - pow(2 * t, 2))) / 2
    return (math.sqrt(1 - pow(-2 * t + 2, 2)) + 1) / 2


# =============================================================================
# Back Easing (slight overshoot)
# =============================================================================

def ease_in_back(t: float) -> float:
    """Back ease-in: slight anticipation before movement."""
    c1 = 1.70158
    c3 = c1 + 1
    return c3 * t * t * t - c1 * t * t


def ease_out_back(t: float) -> float:
    """Back ease-out: slight overshoot at end."""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


def ease_in_out_back(t: float) -> float:
    """Back ease-in-out: anticipation and overshoot."""
    c1 = 1.70158
    c2 = c1 * 1.525
    if t < 0.5:
        return (pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2)) / 2
    return (pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2


# =============================================================================
# Elastic Easing (bounce with overshoot)
# =============================================================================

def ease_in_elastic(t: float) -> float:
    """Elastic ease-in: wind up before movement."""
    if t == 0:
        return 0
    if t == 1:
        return 1
    c4 = (2 * math.pi) / 3
    return -pow(2, 10 * t - 10) * math.sin((t * 10 - 10.75) * c4)


def ease_out_elastic(t: float) -> float:
    """Elastic ease-out: bouncy overshoot at end."""
    if t == 0:
        return 0
    if t == 1:
        return 1
    c4 = (2 * math.pi) / 3
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1


def ease_in_out_elastic(t: float) -> float:
    """Elastic ease-in-out: wind up and bounce."""
    if t == 0:
        return 0
    if t == 1:
        return 1
    c5 = (2 * math.pi) / 4.5
    if t < 0.5:
        return -(pow(2, 20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2
    return (pow(2, -20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1


# =============================================================================
# Bounce Easing
# =============================================================================

def ease_out_bounce(t: float) -> float:
    """Bounce ease-out: bouncing effect at end."""
    n1 = 7.5625
    d1 = 2.75
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375


def ease_in_bounce(t: float) -> float:
    """Bounce ease-in: bouncing effect at start."""
    return 1 - ease_out_bounce(1 - t)


def ease_in_out_bounce(t: float) -> float:
    """Bounce ease-in-out: bouncing at start and end."""
    if t < 0.5:
        return (1 - ease_out_bounce(1 - 2 * t)) / 2
    return (1 + ease_out_bounce(2 * t - 1)) / 2


# =============================================================================
# Smoothstep (Hermite interpolation)
# =============================================================================

def smoothstep(t: float) -> float:
    """Smoothstep: classic smooth interpolation (3t^2 - 2t^3)."""
    return t * t * (3 - 2 * t)


def smootherstep(t: float) -> float:
    """Smootherstep: even smoother (6t^5 - 15t^4 + 10t^3)."""
    return t * t * t * (t * (t * 6 - 15) + 10)


# =============================================================================
# Easing Registry
# =============================================================================

# Registry of all easing functions by name
EASING_REGISTRY: Dict[str, EasingFunction] = {
    # Linear
    "linear": linear,

    # Quadratic
    "ease-in-quad": ease_in_quad,
    "ease-out-quad": ease_out_quad,
    "ease-in-out-quad": ease_in_out_quad,
    "quad-in": ease_in_quad,
    "quad-out": ease_out_quad,
    "quad-in-out": ease_in_out_quad,

    # Cubic
    "ease-in-cubic": ease_in_cubic,
    "ease-out-cubic": ease_out_cubic,
    "ease-in-out-cubic": ease_in_out_cubic,
    "cubic-in": ease_in_cubic,
    "cubic-out": ease_out_cubic,
    "cubic-in-out": ease_in_out_cubic,

    # Quartic
    "ease-in-quart": ease_in_quart,
    "ease-out-quart": ease_out_quart,
    "ease-in-out-quart": ease_in_out_quart,
    "quart-in": ease_in_quart,
    "quart-out": ease_out_quart,
    "quart-in-out": ease_in_out_quart,

    # Quintic
    "ease-in-quint": ease_in_quint,
    "ease-out-quint": ease_out_quint,
    "ease-in-out-quint": ease_in_out_quint,
    "quint-in": ease_in_quint,
    "quint-out": ease_out_quint,
    "quint-in-out": ease_in_out_quint,

    # Exponential
    "ease-in-expo": ease_in_expo,
    "ease-out-expo": ease_out_expo,
    "ease-in-out-expo": ease_in_out_expo,
    "expo-in": ease_in_expo,
    "expo-out": ease_out_expo,
    "expo-in-out": ease_in_out_expo,

    # Sine
    "ease-in-sine": ease_in_sine,
    "ease-out-sine": ease_out_sine,
    "ease-in-out-sine": ease_in_out_sine,
    "sine-in": ease_in_sine,
    "sine-out": ease_out_sine,
    "sine-in-out": ease_in_out_sine,

    # Circular
    "ease-in-circ": ease_in_circ,
    "ease-out-circ": ease_out_circ,
    "ease-in-out-circ": ease_in_out_circ,
    "circ-in": ease_in_circ,
    "circ-out": ease_out_circ,
    "circ-in-out": ease_in_out_circ,

    # Back
    "ease-in-back": ease_in_back,
    "ease-out-back": ease_out_back,
    "ease-in-out-back": ease_in_out_back,
    "back-in": ease_in_back,
    "back-out": ease_out_back,
    "back-in-out": ease_in_out_back,

    # Elastic
    "ease-in-elastic": ease_in_elastic,
    "ease-out-elastic": ease_out_elastic,
    "ease-in-out-elastic": ease_in_out_elastic,
    "elastic-in": ease_in_elastic,
    "elastic-out": ease_out_elastic,
    "elastic-in-out": ease_in_out_elastic,

    # Bounce
    "ease-in-bounce": ease_in_bounce,
    "ease-out-bounce": ease_out_bounce,
    "ease-in-out-bounce": ease_in_out_bounce,
    "bounce-in": ease_in_bounce,
    "bounce-out": ease_out_bounce,
    "bounce-in-out": ease_in_out_bounce,

    # Smoothstep
    "smoothstep": smoothstep,
    "smootherstep": smootherstep,

    # Legacy names (backwards compatibility with zoom_effect.py)
    "ease-in": ease_in_quad,
    "ease-out": ease_out_quad,
    "ease-in-out": ease_in_out_quad,
}


def get_easing(name: str) -> EasingFunction:
    """Get an easing function by name.

    Args:
        name: Name of the easing function (e.g., "ease-out-expo", "cubic-in-out")

    Returns:
        The easing function

    Raises:
        ValueError: If the easing function name is not found
    """
    name_lower = name.lower()
    if name_lower not in EASING_REGISTRY:
        available = ", ".join(sorted(set(EASING_REGISTRY.keys())))
        raise ValueError(f"Unknown easing function '{name}'. Available: {available}")
    return EASING_REGISTRY[name_lower]


def list_easings() -> list:
    """List all available easing function names."""
    return sorted(set(EASING_REGISTRY.keys()))


# =============================================================================
# Presets for common use cases
# =============================================================================

@dataclass
class EasingPreset:
    """Preset easing configuration for common animation types."""
    zoom_in: EasingFunction = ease_out_expo
    zoom_out: EasingFunction = ease_in_expo
    pan: EasingFunction = ease_in_out_cubic
    fade: EasingFunction = ease_in_out_sine
    scale: EasingFunction = ease_out_back


# Default presets
ZOOM_PRESET = EasingPreset(
    zoom_in=ease_out_expo,      # Fast start, slow end (Screen Studio style)
    zoom_out=ease_in_expo,      # Slow start, fast end
    pan=ease_in_out_cubic,      # Smooth pan movement
    fade=ease_in_out_sine,      # Gentle fade
    scale=ease_out_cubic,       # Smooth scale
)

SMOOTH_PRESET = EasingPreset(
    zoom_in=ease_out_cubic,
    zoom_out=ease_in_cubic,
    pan=ease_in_out_quad,
    fade=ease_in_out_sine,
    scale=ease_in_out_cubic,
)

SNAPPY_PRESET = EasingPreset(
    zoom_in=ease_out_quart,
    zoom_out=ease_in_quart,
    pan=ease_out_cubic,
    fade=ease_out_quad,
    scale=ease_out_back,
)
