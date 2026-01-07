#!/bin/bash
set -e

echo "=== ProgrammaticDemo macOS Setup ==="
echo ""

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "Error: Homebrew is not installed."
    echo "Install from: https://brew.sh"
    exit 1
fi

echo "Installing system dependencies via Homebrew..."

# Install core dependencies
brew install ffmpeg
brew install tesseract
brew install tmux

# Install Ghostty terminal emulator
if ! brew list --cask ghostty &> /dev/null; then
    echo "Installing Ghostty..."
    brew install --cask ghostty
else
    echo "Ghostty already installed."
fi

# Install yabai window manager
if ! brew list yabai &> /dev/null; then
    echo "Installing yabai..."
    brew install koekeishiya/formulae/yabai
else
    echo "yabai already installed."
fi

echo ""
echo "Setting up Python virtual environment..."

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install package in editable mode
pip install --upgrade pip
pip install -e ".[dev]"

# Install Playwright browsers
echo ""
echo "Installing Playwright browsers..."
playwright install chromium

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To verify installation:"
echo "  python scripts/verify_dependencies.py"
echo ""
echo "IMPORTANT: Grant the following macOS permissions:"
echo "  - System Preferences > Security & Privacy > Privacy > Screen Recording"
echo "  - System Preferences > Security & Privacy > Privacy > Accessibility"
