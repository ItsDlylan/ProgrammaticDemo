Agentic Directed Video Demo System — Specification
1. Purpose & Scope
Objective

Build an agent-driven system that autonomously generates high-quality screen-recorded product demos from a single natural-language prompt.

The system operates as four coordinated roles:

Director — plans scenes and narrative flow

Operator — executes UI and system actions

Observer — monitors screen state, logs, and output

Editor — retries, corrects, trims, and restarts scenes

Intended Use (Internal Only)

Product demos

Feature walkthroughs

Engineering showcases

Release previews

This is not a public-facing tool. Only basic sandboxing is required.

2. Functional Requirements
2.1 Prompt-Driven Demo Creation

The system MUST:

Accept a single high-level prompt

Decompose the prompt into ordered scenes

Define goals, steps, and success conditions per scene

Execute the demo autonomously end-to-end

Example Prompt

“Create a demo showing how to scaffold the app, start the dev server, log in, and create a new project.”

2.2 Scene-Based Execution Model

Each demo MUST be composed of ordered scenes.

Each scene MUST define:

Scene name

Narrative goal

Ordered steps

Expected final UI/system state

Failure and recovery strategy

Scenes MUST:

Be independently retryable

Be restartable without restarting the full demo

Emit deterministic success signals

2.3 Agentic Control Loop

The system MUST operate in a continuous loop:

Observe → Reason → Act → Verify → Record


The agent MUST:

Observe screen state and program output

Decide the next action

Wait when async actions are pending

Recover from errors automatically

Retry steps or scenes when needed

2.4 UI Interaction (Human-Like)

The system MUST support:

Visible mouse movement (non-teleporting)

Clicks, scrolling, dragging

Keyboard typing with realistic delays

Hover pauses before interaction

The demo MUST visually resemble real human usage.

2.5 Terminal Interaction

The system MUST:

Launch a terminal emulator (Ghostty preferred)

Execute shell commands

Capture stdout and stderr

Detect command completion

Detect crashes or errors

Retry or correct commands when needed

2.6 Browser Interaction

The system MUST:

Launch a real headful browser

Navigate pages

Click buttons and fill forms

Wait for DOM/UI state changes

Detect loading states and failures

Browser automation MUST coexist with visible mouse control.

2.7 Screen Recording

The system MUST:

Record at ≥ 60 FPS

Capture all windows involved

Start recording before the first action

Stop recording after demo completion

Produce uninterrupted, post-processable footage

2.8 Perception & State Awareness

The system MUST observe:

Full-screen screenshots

OCR-extracted text

Terminal output

Active window context

Timestamps

The agent MUST:

Detect lack of progress

Detect errors

Detect successful transitions

Decide when to wait vs act

2.9 Error Handling & Recovery

The system MUST:

Detect command failures

Detect UI failures and unexpected dialogs

Retry steps intelligently

Restart scenes when necessary

Abort gracefully if recovery is impossible

Correctness and clarity take priority over speed.

2.10 Output Artifacts

The system MUST produce:

Final demo video

Raw recording (optional)

Execution log

Scene execution summary

3. Non-Functional Requirements
Reliability

Prefer deterministic behavior

Automatic retries for transient failures

Scene-level isolation

Visual Quality

Smooth mouse movement

Clear pacing

No rushed transitions

No flicker or abrupt jumps

Performance

Real-time execution only

No artificial fast-forwarding during recording

Security (Internal)

Sandboxed OS user

Restricted shell commands

No destructive file operations

Network access limited to required domains

4. Technical Architecture
4.1 High-Level Components
┌────────────────────────────┐
│ Director Agent (Claude)    │
│ - Plans scenes             │
│ - Chooses actions          │
│ - Reacts to observations   │
└───────────────┬────────────┘
                ↓
┌────────────────────────────┐
│ Orchestrator (Python)      │
│ - Executes actions         │
│ - Controls OS              │
│ - Captures state           │
│ - Feeds observations back  │
└───────────────┬────────────┘
                ↓
┌────────────────────────────┐
│ Actuators & Sensors        │
│ - Mouse & keyboard         │
│ - Browser                  │
│ - Terminal                 │
│ - Screen capture           │
└────────────────────────────┘

5. Recommended Tech Stack
Core

Python 3.11+ — Orchestrator

Claude — Director agent

JSON-based action protocol

UI & Automation

Terminal: Ghostty, tmux

Browser: Playwright (headful)

Mouse/Keyboard: pyautogui, native OS APIs

Perception

Screen capture: ffmpeg

OCR: tesseract or easyocr

Image analysis: OpenCV

Window Management

macOS: yabai

Linux: wmctrl

6. Agent ↔ Orchestrator Protocol
Action Schema (Example)
{
  "action": "click",
  "target": {
    "type": "screen",
    "description": "Create Project button"
  },
  "wait_for": {
    "type": "text",
    "value": "Project created"
  }
}

Observation Schema
{
  "screenshot": "base64",
  "ocr_text": "...",
  "terminal_output": "...",
  "active_window": "Browser",
  "timestamp": 1712345678
}


The agent MUST NOT assume success without observation confirmation.

7. Execution Flow

Receive demo prompt

Generate scene plan

Initialize environment

Start screen recording

Execute scenes sequentially

Observe and react continuously

Retry or recover as needed

End recording

Save artifacts

8. Explicit Expectations for the Planning Agent
The agent MUST:

Design for deterministic execution

Prefer explicit waits over fixed sleeps

Treat UI as asynchronous and unreliable

Assume failures will occur

Optimize for demo clarity over speed

Avoid brittle selectors and race conditions

The agent MUST NOT:

Assume commands succeed

Skip verification steps

Rush transitions

Hardcode timing without observation
