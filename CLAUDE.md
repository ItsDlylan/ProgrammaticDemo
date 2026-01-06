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
