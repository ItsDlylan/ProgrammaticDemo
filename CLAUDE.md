# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ProgrammaticDemo is an agent-driven system that autonomously generates screen-recorded product demos from natural-language prompts. It operates through four coordinated roles: Director (plans scenes), Operator (executes actions), Observer (monitors state), and Editor (handles retries/corrections).

## Architecture

```
┌────────────────────────────┐
│ Director Agent (Claude)    │  ← Plans scenes, chooses actions, reacts to observations
└───────────────┬────────────┘
                ↓
┌────────────────────────────┐
│ Orchestrator (Python)      │  ← Executes actions, controls OS, captures state
└───────────────┬────────────┘
                ↓
┌────────────────────────────┐
│ Actuators & Sensors        │  ← Mouse/keyboard, browser, terminal, screen capture
└────────────────────────────┘
```

## Tech Stack

- **Core**: Python 3.11+, Claude API, JSON-based action protocol
- **Terminal**: Ghostty, tmux
- **Browser**: Playwright (headful mode)
- **Mouse/Keyboard**: pyautogui, native OS APIs
- **Screen Capture**: ffmpeg (≥60 FPS)
- **OCR**: tesseract or easyocr
- **Image Analysis**: OpenCV
- **Window Management**: yabai (macOS), wmctrl (Linux)

## Core Execution Loop

The system operates in a continuous loop: **Observe → Reason → Act → Verify → Record**

Each demo consists of ordered scenes, where each scene defines:
- Scene name and narrative goal
- Ordered steps with expected final state
- Failure and recovery strategy

## Action/Observation Protocol

Actions use JSON schema with target descriptions and wait conditions:
```json
{
  "action": "click",
  "target": { "type": "screen", "description": "Create Project button" },
  "wait_for": { "type": "text", "value": "Project created" }
}
```

Observations include screenshot (base64), OCR text, terminal output, active window, and timestamp.

## Key Design Principles

- **Never assume success** - always verify via observation
- **Prefer explicit waits** over fixed sleeps
- **UI is asynchronous and unreliable** - treat it accordingly
- **Human-like interactions** - visible mouse movement, realistic typing delays, hover pauses
- **Scene isolation** - scenes must be independently retryable without full demo restart
- **Clarity over speed** - smooth pacing, no rushed transitions

## Development Workflow

### Task Management with features.json

All features are tracked in `features.json`. When working on this project:

1. **One task at a time** - Only work on ONE feature from `features.json` at a time. Complete it fully before moving to the next.

2. **Update passes immediately** - When a feature is complete and tested, update its `passes` field to `true` in `features.json` before moving on.

3. **Check dependencies** - Before starting a feature, verify all features in its `depends_on` array have `passes: true`.

4. **Test before marking complete** - A feature is only complete when it's been tested and works. Don't mark `passes: true` until verified.

### Example workflow:
```bash
# 1. Pick a feature with all dependencies satisfied
# 2. Implement the feature
# 3. Test the feature
# 4. Update features.json: "passes": true
# 5. Move to next feature
```

### Current Progress
Run this to see completion status:
```bash
cat features.json | python3 -c "import json,sys; d=json.load(sys.stdin); t=len(d['features']); p=sum(1 for f in d['features'] if f['passes']); print(f'{p}/{t} features complete ({100*p//t}%)')"
```
