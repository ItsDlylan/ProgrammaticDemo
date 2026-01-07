#!/usr/bin/env python3
"""Verify that all dependencies for ProgrammaticDemo are properly installed."""

import shutil
import subprocess
import sys


def check_python_version() -> bool:
    """Check if Python version is 3.11 or higher."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    print(f"✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.11+)")
    return False


def check_system_command(cmd: str, name: str) -> bool:
    """Check if a system command is available."""
    path = shutil.which(cmd)
    if path:
        print(f"✓ {name} ({path})")
        return True
    print(f"✗ {name} not found")
    return False


def check_python_package(package: str) -> bool:
    """Check if a Python package is importable."""
    try:
        __import__(package)
        print(f"✓ {package}")
        return True
    except ImportError:
        print(f"✗ {package}")
        return False


def main() -> int:
    """Run all dependency checks."""
    print("=== ProgrammaticDemo Dependency Check ===\n")

    all_passed = True

    # Python version
    print("Python Version:")
    if not check_python_version():
        all_passed = False
    print()

    # System commands
    print("System Commands:")
    system_commands = [
        ("ffmpeg", "FFmpeg (screen recording)"),
        ("tesseract", "Tesseract (OCR)"),
        ("tmux", "tmux (terminal multiplexing)"),
    ]
    for cmd, name in system_commands:
        if not check_system_command(cmd, name):
            all_passed = False
    print()

    # Optional system commands
    print("Optional System Commands:")
    optional_commands = [
        ("yabai", "yabai (window management)"),
        ("ghostty", "Ghostty (terminal emulator)"),
    ]
    for cmd, name in optional_commands:
        check_system_command(cmd, name)  # Don't fail on optional
    print()

    # Python packages
    print("Python Packages:")
    packages = [
        "typer",
        "pydantic",
        "pyautogui",
        "playwright",
        "PIL",  # pillow
        "mss",
        "pytesseract",
        "cv2",  # opencv-python
    ]
    for package in packages:
        if not check_python_package(package):
            all_passed = False
    print()

    # Summary
    if all_passed:
        print("=== All Required Dependencies OK ===")
        return 0
    else:
        print("=== Some Dependencies Missing ===")
        print("\nRun scripts/setup_macos.sh to install missing dependencies.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
