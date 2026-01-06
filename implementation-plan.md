# ProgrammaticDemo Implementation Plan

## Overview

Build a Python CLI toolkit (`pdemo`) that Claude Code invokes to execute autonomous screen-recorded demos. Claude Code acts as the Director agent; the toolkit provides actuators (mouse, keyboard, terminal, browser) and sensors (screenshots, OCR, window state).

## Architecture

```
Claude Code (Director)
    ↓ invokes CLI commands
pdemo CLI (Python)
    ↓ calls modules
Actuators & Sensors
    ↓ controls
OS (mouse, keyboard, terminal, browser, screen)
```

## Project Structure

```
programmatic_demo/
├── pyproject.toml
├── src/programmatic_demo/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli/
│   │   ├── main.py          # CLI entry point (typer)
│   │   ├── recording.py     # record start/stop
│   │   ├── mouse.py         # move, click, scroll
│   │   ├── keyboard.py      # type, press, hotkey
│   │   ├── terminal.py      # launch, exec, read, wait-for
│   │   ├── browser.py       # launch, navigate, click, fill
│   │   └── perception.py    # screenshot, ocr, observe
│   ├── actuators/
│   │   ├── mouse.py         # pyautogui + bezier smoothing
│   │   ├── keyboard.py      # typing with human-like delays
│   │   ├── terminal.py      # Ghostty/tmux control
│   │   ├── browser.py       # Playwright headful
│   │   └── window.py        # yabai window management
│   ├── sensors/
│   │   ├── screen.py        # screenshot capture
│   │   ├── ocr.py           # tesseract/easyocr
│   │   └── state.py         # unified observation
│   ├── recording/
│   │   └── recorder.py      # ffmpeg control
│   └── utils/
│       ├── timing.py        # human-like delays
│       └── config.py        # settings
└── scripts/
    ├── setup_macos.sh
    └── verify_dependencies.py
```

## CLI Commands (JSON output)

### Recording
```bash
pdemo record start --output demo.mp4 --fps 60
pdemo record stop
pdemo record status
```

### Terminal
```bash
pdemo terminal launch --name "demo"
pdemo terminal exec --command "npm install" --timeout 120
pdemo terminal send --command "npm run dev"
pdemo terminal read --lines 50
pdemo terminal wait-for --text "Server running" --timeout 30
```

### Keyboard
```bash
pdemo keyboard type --text "hello world" --delay-ms 50
pdemo keyboard press --key enter
pdemo keyboard hotkey --keys "cmd+shift+p"
```

### Mouse
```bash
pdemo mouse move --x 500 --y 300 --duration 0.5
pdemo mouse click --x 500 --y 300 --button left
pdemo mouse scroll --direction down --amount 3
```

### Browser
```bash
pdemo browser launch --url "http://localhost:3000"
pdemo browser click --selector "#submit-btn"
pdemo browser fill --selector "#email" --value "user@example.com"
pdemo browser wait --selector ".dashboard" --timeout 10
```

### Perception
```bash
pdemo observe screenshot --output screen.png
pdemo observe ocr
pdemo observe full   # screenshot + ocr + window + terminal
```

## Observation Protocol (JSON)

```json
{
  "success": true,
  "observation": {
    "timestamp": 1712345678.123,
    "screenshot": {"path": "/tmp/obs.png", "base64": "..."},
    "ocr_text": "extracted text...",
    "active_window": {"title": "App", "app": "Chrome"},
    "terminal_output": "last output lines..."
  }
}
```

## Dependencies

### Python (pyproject.toml)
- typer (CLI)
- pydantic (validation)
- pyautogui (mouse/keyboard)
- playwright (browser)
- pillow, mss (screenshots)
- pytesseract, easyocr (OCR)
- opencv-python (vision)

### System (Homebrew)
- ffmpeg (recording)
- tesseract (OCR)
- tmux (terminal multiplexing)
- ghostty (terminal emulator)
- yabai (window management)

### macOS Permissions
- Screen Recording
- Accessibility (for pyautogui)

---

## Implementation Phases

### Phase 1: Minimal End-to-End Slice

**Goal:** Prove system works with a simple terminal demo.

**Scenario:** Open terminal, run `echo "Hello"`, verify output, record video.

**Files to create:**
1. `pyproject.toml` - project config and dependencies
2. `src/programmatic_demo/__init__.py` - package init
3. `src/programmatic_demo/__main__.py` - CLI entry
4. `src/programmatic_demo/cli/main.py` - typer app with subcommands
5. `src/programmatic_demo/cli/recording.py` - record start/stop
6. `src/programmatic_demo/cli/terminal.py` - terminal commands
7. `src/programmatic_demo/cli/keyboard.py` - type/press commands
8. `src/programmatic_demo/cli/perception.py` - observe commands
9. `src/programmatic_demo/actuators/terminal.py` - Ghostty/tmux control
10. `src/programmatic_demo/actuators/keyboard.py` - pyautogui keyboard
11. `src/programmatic_demo/sensors/screen.py` - screenshot capture
12. `src/programmatic_demo/sensors/state.py` - observation collection
13. `src/programmatic_demo/recording/recorder.py` - ffmpeg wrapper
14. `scripts/setup_macos.sh` - dependency installation
15. `scripts/verify_dependencies.py` - verify setup

**Deferred:** Mouse control, browser automation, OCR, vision, scene management

### Phase 2: Mouse Control

**Files:**
- `src/programmatic_demo/cli/mouse.py`
- `src/programmatic_demo/actuators/mouse.py` (bezier curves, jitter)
- `src/programmatic_demo/actuators/window.py` (yabai)

### Phase 3: Perception (OCR)

**Files:**
- `src/programmatic_demo/sensors/ocr.py` (tesseract integration)
- Update `cli/perception.py` with OCR commands
- Add "find element by description" functionality

### Phase 4: Browser Automation

**Files:**
- `src/programmatic_demo/cli/browser.py`
- `src/programmatic_demo/actuators/browser.py` (Playwright)

### Phase 5: Scene Management (Optional)

**Files:**
- `src/programmatic_demo/scene/models.py`
- `src/programmatic_demo/scene/executor.py`
- `src/programmatic_demo/scene/recovery.py`
- `src/programmatic_demo/cli/scene.py`

---

## Setup Script (macOS)

```bash
#!/bin/bash
# Install system deps
brew install ffmpeg tesseract tmux
brew install --cask ghostty
brew install koekeishiya/formulae/yabai

# Python setup
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

---

## Example Claude Code Workflow

```bash
# Claude Code executes:
pdemo record start --output /tmp/demo.mp4
pdemo terminal launch --name demo
pdemo keyboard type --text "echo 'Hello, World!'"
pdemo keyboard press --key enter
pdemo terminal wait-for --text "Hello, World!" --timeout 5
pdemo observe full
pdemo record stop
```

---

## Critical Files (Phase 1)

| File | Purpose |
|------|---------|
| `pyproject.toml` | Dependencies and package config |
| `src/programmatic_demo/cli/main.py` | CLI entry point |
| `src/programmatic_demo/actuators/terminal.py` | Terminal control |
| `src/programmatic_demo/recording/recorder.py` | ffmpeg recording |
| `src/programmatic_demo/sensors/state.py` | Observation protocol |
| `scripts/setup_macos.sh` | Setup script |

---

## Feature Dependency Graph

Features should be implemented in this order based on dependencies:

**Layer 1 (No dependencies):**
- SETUP-001, SETUP-002, SETUP-003, SETUP-004

**Layer 2 (Requires setup):**
- CLI-001, CLI-002, CLI-003
- UTIL-001, UTIL-002
- ERR-001

**Layer 3 (Requires CLI framework):**
- REC-001, REC-002, REC-003, REC-004
- SCREEN-001, SCREEN-002, SCREEN-003, SCREEN-004

**Layer 4 (Requires recording/screen):**
- KEY-001, KEY-002, KEY-003, KEY-004
- TERM-001, TERM-002, TERM-003, TERM-004, TERM-005, TERM-006, TERM-007
- ERR-002, ERR-003

**Layer 5 (Requires keyboard/terminal):**
- OCR-001, OCR-002, OCR-003
- STATE-001, STATE-002, STATE-003

**Layer 6 (Requires perception):**
- MOUSE-001, MOUSE-002, MOUSE-003, MOUSE-004, MOUSE-005, MOUSE-006
- WINDOW-001, WINDOW-002

**Layer 7 (Requires mouse/window):**
- BROWSER-001 through BROWSER-009

**Layer 8 (Integration tests - requires all):**
- INT-001, INT-002, INT-003, INT-004
