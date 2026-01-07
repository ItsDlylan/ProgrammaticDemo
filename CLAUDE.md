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

---

## Demo Recording Workflow

There are two approaches to recording demos:

### Approach 1: Playwright Script (Recommended for Clean Recordings)

Use standalone Python scripts in `scripts/` for maximum control. This approach:
- Records clean raw video with Playwright's built-in recording
- Tracks events (clicks, scrolls) to `events.json` for post-processing
- Injects custom cursor (Playwright doesn't capture system cursor)

**Example workflow:**
```bash
# 1. Run the recording script
python scripts/stripe_landing_demo.py

# 2. Output goes to recordings/stripe_demo_YYYYMMDD_HHMMSS/
#    - *.webm  (raw video)
#    - events.json (click/scroll metadata with timestamps)

# 3. Apply post-processing effects
python scripts/apply_zoom_effects.py
```

**Key file: `scripts/stripe_landing_demo.py`**
- `StripeLandingDemo` class handles browser setup with video recording
- `_inject_cursor()` adds SVG cursor element (required - Playwright doesn't capture system cursor)
- `log_event()` tracks clicks/scrolls with timestamps for post-processing
- Events exported to `events.json` with viewport info

### Approach 2: YAML/JSON Demo Scripts

Use declarative scripts in `demos/` with the orchestrator:

```bash
# Run a demo script
pdemo run demo demos/tcg_elevate_landing.yaml

# Run single scene
pdemo run scene demos/tcg_elevate_landing.yaml --scene 2

# Run single step
pdemo run step demos/tcg_elevate_landing.yaml --scene 0 --step 1
```

---

## Demo Script Format

Demo scripts (YAML/JSON) define scenes with steps:

```yaml
name: My Demo
description: Demo description

config:
  resolution: 1920x1080
  fps: 30
  mouse_speed: smooth  # instant, fast, smooth, natural

scenes:
  - name: Scene Name
    goal: What this scene accomplishes
    narration: "Voiceover text"
    on_failure: retry  # retry, skip, abort
    steps:
      - action: navigate
        target:
          type: url
          value: "https://example.com"
        wait_for:
          type: timeout
          value: 2000

      - action: click
        target:
          type: selector
          selector: "button.submit"
          description: "Submit button"
        wait_for:
          type: text
          value: "Success"

      - action: scroll
        params:
          direction: down
          amount: 400
          duration: 1500
          easing: ease-out

      - action: type
        target:
          type: selector
          selector: "input[name=email]"
        params:
          text: "user@example.com"
          delay: 50  # ms between keystrokes

effects:
  - type: cursor_highlight
    params:
      color: "#FFD700"
      radius: 20

export:
  format: mp4
  codec: h264
  quality: high
```

**Action Types:** `click`, `type`, `press`, `scroll`, `wait`, `navigate`, `terminal`, `hotkey`, `drag`

**Target Types:** `screen`, `selector`, `coordinates`, `text`, `window`

---

## Post-Processing Workflow

Post-processing applies effects to raw recordings using FFmpeg.

### Philosophy: Keep Raw Video Clean

Record clean video without effects, then apply effects in post-processing. This allows:
- Multiple versions with different effects from one recording
- Experimentation without re-recording
- Flexibility to change effects later

### Key Post-Processing Files

| File | Purpose |
|------|---------|
| `scripts/apply_zoom_effects.py` | Apply zoom at click points (creates 3 versions) |
| `src/programmatic_demo/postprocess/editor.py` | `VideoEditor` class with FFmpeg operations |
| `src/programmatic_demo/postprocess/transitions.py` | Scene transitions |
| `src/programmatic_demo/postprocess/overlays.py` | Text/image overlays |
| `src/programmatic_demo/postprocess/audio.py` | Audio processing |

### VideoEditor Usage

```python
from programmatic_demo.postprocess import VideoEditor, FFmpegBuilder

editor = VideoEditor()

# Trim video
editor.trim("input.mp4", start_time=5.0, end_time=30.0, output_path="trimmed.mp4")

# Concatenate videos
editor.concat(["intro.mp4", "main.mp4", "outro.mp4"], "final.mp4", crossfade=0.5)

# Speed adjustment
editor.speed_adjust("input.mp4", factor=1.5, output_path="faster.mp4")

# Resize
editor.resize("input.mp4", width=1280, height=720, output_path="720p.mp4")

# Create title slide
editor.create_title_slide("My Demo", duration=3.0, output_path="title.mp4")

# Prepend intro with transition
editor.prepend_intro("main.mp4", "intro.mp4", "final.mp4", transition="fade")
```

### FFmpegBuilder for Custom Commands

```python
from programmatic_demo.postprocess import FFmpegBuilder

# Build custom FFmpeg command
builder = (
    FFmpegBuilder()
    .overwrite()
    .input("input.mp4")
    .filter("crop=1280:720:0:0")
    .filter("scale=1920:1080")
    .output("output.mp4", vcodec="libx264", crf="18")
)

# Execute
builder.run()

# Or get command string
print(builder.build_string())
```

### CLI Video Commands

```bash
# Trim video
pdemo video trim input.mp4 -o output.mp4 -s 5 -e 30

# Concatenate videos
pdemo video concat -o output.mp4 video1.mp4 video2.mp4 video3.mp4

# Add text overlay
pdemo video overlay input.mp4 -o output.mp4 -t "My Demo" -p bottom-right

# Export with preset
pdemo video export input.mp4 -o output.mp4 -p web

# Get video info
pdemo video info video.mp4
```

---

## Effects System

Available effects in `src/programmatic_demo/effects/`:

| Effect | Module | Usage |
|--------|--------|-------|
| Click ripple | `click_effect.py` | `create_click_effect(x, y, config)` |
| Zoom | `zoom_effect.py` | `create_subtle_zoom()`, `create_medium_zoom()`, `create_dramatic_zoom()` |
| Highlight | `highlight.py` | `create_highlight(region, config)` |
| Callout | `callout.py` | `create_callout(text, position)`, `create_tooltip()` |
| Mouse tracking | `mouse_tracker.py` | `get_mouse_tracker()` |
| Compositor | `compositor.py` | Combines multiple effects with timing |

### Zoom Presets

```python
from programmatic_demo.effects import create_subtle_zoom, create_medium_zoom, create_dramatic_zoom

# Subtle: 1.3x zoom, 800ms duration
subtle = create_subtle_zoom(center_x=500, center_y=300)

# Medium: 1.5x zoom, 1000ms duration
medium = create_medium_zoom(center_x=500, center_y=300)

# Dramatic: 2.0x zoom, 1200ms duration
dramatic = create_dramatic_zoom(center_x=500, center_y=300)
```

---

## Key Files Reference

### Recording & Orchestration
```
scripts/stripe_landing_demo.py      # Example Playwright recording script
src/programmatic_demo/orchestrator/runner.py    # Demo execution runner
src/programmatic_demo/orchestrator/dispatcher.py # Action dispatcher
src/programmatic_demo/models/script.py          # Script/Scene/Step models
```

### Post-Processing
```
scripts/apply_zoom_effects.py                   # Zoom post-processor
src/programmatic_demo/postprocess/editor.py     # VideoEditor + FFmpegBuilder
src/programmatic_demo/postprocess/transitions.py
src/programmatic_demo/postprocess/overlays.py
```

### Effects
```
src/programmatic_demo/effects/zoom_effect.py
src/programmatic_demo/effects/click_effect.py
src/programmatic_demo/effects/highlight.py
src/programmatic_demo/effects/callout.py
src/programmatic_demo/effects/compositor.py
```

### Visual Intelligence
```
src/programmatic_demo/visual/section_detector.py  # Auto-detect page sections
src/programmatic_demo/visual/auto_scroll.py       # Smart scrolling
src/programmatic_demo/visual/animation_detector.py # Wait for animations
src/programmatic_demo/visual/framing_analyzer.py  # Verify framing
src/programmatic_demo/visual/waypoint_generator.py # Generate scroll waypoints
```

### CLI Entry Points
```
src/programmatic_demo/cli/main.py     # Main CLI (pdemo command)
src/programmatic_demo/cli/run.py      # pdemo run demo/scene/step
src/programmatic_demo/cli/video.py    # pdemo video trim/concat/overlay/export
src/programmatic_demo/cli/effects.py  # pdemo effects commands
src/programmatic_demo/cli/visual.py   # pdemo visual commands
```

---

## Common Workflows

### Record + Apply Zoom Effects
```bash
# 1. Record clean video
python scripts/stripe_landing_demo.py

# 2. Apply zoom effects (creates v1_subtle, v2_medium, v3_dramatic)
python scripts/apply_zoom_effects.py
```

### Create Demo with Intro/Outro
```python
from programmatic_demo.postprocess import VideoEditor

editor = VideoEditor()

# Create intro
editor.create_title_slide("My Product Demo", 3.0, "intro.mp4")

# Create outro
editor.create_outro_slide("Thanks for watching!", 2.0, "outro.mp4")

# Combine with main video
editor.concat(["intro.mp4", "main.mp4", "outro.mp4"], "final.mp4", crossfade=0.5)
```

### Recording Output Structure
```
recordings/
└── stripe_demo_20260107_132941/
    ├── *.webm           # Raw video from Playwright
    ├── events.json      # Click/scroll metadata
    ├── v1_subtle_zoom.mp4
    ├── v2_medium_zoom.mp4
    └── v3_dramatic_zoom.mp4
```

### events.json Format
```json
{
  "viewport": {"width": 1280, "height": 800},
  "url": "https://stripe.com",
  "events": [
    {"type": "start", "timestamp": 0.0, "x": 0, "y": 0, "label": "recording_start"},
    {"type": "click", "timestamp": 2.93, "x": 979, "y": 35, "label": "Sign In"},
    {"type": "scroll_start", "timestamp": 5.75, "x": 640, "y": 400, "label": "scroll_down"},
    {"type": "scroll_end", "timestamp": 6.95, "x": 640, "y": 400, "label": "scroll_down"},
    {"type": "end", "timestamp": 8.91, "x": 0, "y": 0, "label": "recording_end"}
  ]
}
```

---

## Smooth Zoom System (Screen Studio-Style)

The zoom system provides smooth, animated zoom effects with mouse tracking. Key features:

### Recording with Mouse Tracking
```python
# stripe_landing_demo.py now captures mouse_path at ~30fps
python scripts/stripe_landing_demo.py
# Output includes mouse_path in events.json for smooth zoom
```

### Apply Smooth Animated Zoom
```python
from scripts.apply_zoom_effects import create_zoom_versions, ZoomTriggerConfig

# Basic smooth animated zoom (default)
create_zoom_versions("./recordings/stripe_demo_XXXXXX/")

# With smart triggers (skip zoom during fast movement)
create_zoom_versions(
    "./recordings/stripe_demo_XXXXXX/",
    smart_triggers=True,
    trigger_config=ZoomTriggerConfig(velocity_threshold=50)
)

# With mouse-following pan
create_zoom_versions(
    "./recordings/stripe_demo_XXXXXX/",
    follow_mouse=True
)

# Frame-by-frame rendering for precise control
create_zoom_versions(
    "./recordings/stripe_demo_XXXXXX/",
    frame_by_frame=True
)
```

### Easing Functions
Available in `src/programmatic_demo/effects/easing.py`:
- `ease_out_expo` - Fast start, slow end (recommended for zoom-in)
- `ease_in_expo` - Slow start, fast end (recommended for zoom-out)
- `ease_in_out_cubic` - Smooth start and end
- `smoothstep`, `smootherstep` - Classic interpolation
- Full registry with `get_easing("ease-out-expo")`
