"""Actuators for controlling OS inputs."""

from programmatic_demo.actuators.browser import Browser
from programmatic_demo.actuators.keyboard import Keyboard
from programmatic_demo.actuators.mouse import Mouse
from programmatic_demo.actuators.terminal import Terminal
from programmatic_demo.actuators.window import Window

__all__ = ["Terminal", "Keyboard", "Mouse", "Window", "Browser"]
