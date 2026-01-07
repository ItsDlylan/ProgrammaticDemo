"""CLI commands for video effects management."""

import json
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="Video effects commands.")


# Global effects configuration state
_effects_config = {
    "enabled": True,
    "highlight": {"enabled": True, "color": "#FFEB3B", "opacity": 0.3},
    "click": {"enabled": True, "radius": 30, "color": "#FF5722", "duration_ms": 300},
    "zoom": {"enabled": True, "factor": 1.5, "duration_ms": 500},
    "callout": {"enabled": True, "font_size": 16, "text_color": "#FFFFFF"},
}


@app.command("enable")
def enable(
    effect_type: Optional[str] = typer.Argument(None, help="Effect type to enable (all if not specified)"),
    disable: bool = typer.Option(False, "--disable", "-d", help="Disable instead of enable"),
) -> None:
    """Enable or disable effects.

    Examples:
        pdemo effects enable                    # Enable all effects
        pdemo effects enable highlight          # Enable highlight effect
        pdemo effects enable click --disable    # Disable click effect
    """
    global _effects_config

    if effect_type is None:
        # Toggle all effects
        _effects_config["enabled"] = not disable
        status = "disabled" if disable else "enabled"
        typer.echo(json.dumps({"success": True, "message": f"All effects {status}", "enabled": _effects_config["enabled"]}))
    elif effect_type in _effects_config:
        if isinstance(_effects_config[effect_type], dict):
            _effects_config[effect_type]["enabled"] = not disable
            status = "disabled" if disable else "enabled"
            typer.echo(json.dumps({"success": True, "effect": effect_type, "status": status}))
        else:
            typer.echo(json.dumps({"success": False, "error": f"Cannot toggle '{effect_type}' - not an effect type"}))
    else:
        valid_types = [k for k, v in _effects_config.items() if isinstance(v, dict)]
        typer.echo(json.dumps({"success": False, "error": f"Unknown effect type: {effect_type}", "valid_types": valid_types}))
        raise typer.Exit(1)


@app.command("config")
def config(
    effect_type: str = typer.Argument(..., help="Effect type to configure"),
    param: str = typer.Argument(..., help="Parameter name to set"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Configure effect parameters.

    Examples:
        pdemo effects config highlight color "#FF0000"
        pdemo effects config click radius 50
        pdemo effects config zoom factor 2.0
    """
    global _effects_config

    if effect_type not in _effects_config:
        valid_types = [k for k, v in _effects_config.items() if isinstance(v, dict)]
        typer.echo(json.dumps({"success": False, "error": f"Unknown effect type: {effect_type}", "valid_types": valid_types}))
        raise typer.Exit(1)

    effect_cfg = _effects_config[effect_type]
    if not isinstance(effect_cfg, dict):
        typer.echo(json.dumps({"success": False, "error": f"'{effect_type}' is not configurable"}))
        raise typer.Exit(1)

    if param not in effect_cfg:
        valid_params = list(effect_cfg.keys())
        typer.echo(json.dumps({"success": False, "error": f"Unknown parameter: {param}", "valid_params": valid_params}))
        raise typer.Exit(1)

    # Convert value to appropriate type
    old_value = effect_cfg[param]
    try:
        if isinstance(old_value, bool):
            new_value = value.lower() in ("true", "1", "yes")
        elif isinstance(old_value, int):
            new_value = int(value)
        elif isinstance(old_value, float):
            new_value = float(value)
        else:
            new_value = value
    except ValueError:
        typer.echo(json.dumps({"success": False, "error": f"Invalid value type for {param}"}))
        raise typer.Exit(1)

    effect_cfg[param] = new_value
    typer.echo(json.dumps({
        "success": True,
        "effect": effect_type,
        "param": param,
        "old_value": old_value,
        "new_value": new_value,
    }, indent=2))


@app.command("show")
def show(
    effect_type: Optional[str] = typer.Argument(None, help="Effect type to show config for (all if not specified)"),
) -> None:
    """Show current effects configuration.

    Examples:
        pdemo effects show              # Show all config
        pdemo effects show highlight    # Show highlight config
    """
    if effect_type is None:
        typer.echo(json.dumps(_effects_config, indent=2))
    elif effect_type in _effects_config:
        typer.echo(json.dumps({effect_type: _effects_config[effect_type]}, indent=2))
    else:
        valid_types = list(_effects_config.keys())
        typer.echo(json.dumps({"error": f"Unknown effect type: {effect_type}", "valid_types": valid_types}))
        raise typer.Exit(1)


@app.command("preview")
def preview(
    input_file: str = typer.Argument(..., help="Input image or video file"),
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    effect: str = typer.Option("highlight", "--effect", "-e", help="Effect to preview: highlight, click, zoom, callout"),
    x: int = typer.Option(500, "--x", help="X coordinate for effect"),
    y: int = typer.Option(300, "--y", help="Y coordinate for effect"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Text for callout effect"),
    duration: float = typer.Option(1.0, "--duration", "-d", help="Effect duration in seconds"),
) -> None:
    """Preview an effect on an image or video.

    Examples:
        pdemo effects preview screenshot.png -o preview.png -e highlight -x 100 -y 200
        pdemo effects preview video.mp4 -o preview.mp4 -e click -x 500 -y 300
        pdemo effects preview video.mp4 -o preview.mp4 -e callout -x 100 -y 50 -t "Click here"
    """
    from programmatic_demo.effects import Compositor, Effect, EffectConfig, EffectEvent, EffectType
    import subprocess

    if not Path(input_file).exists():
        typer.echo(json.dumps({"success": False, "error": f"File not found: {input_file}"}))
        raise typer.Exit(1)

    # Create compositor with the preview effect
    compositor = Compositor()

    # Map effect name to EffectType
    effect_map = {
        "highlight": EffectType.HIGHLIGHT,
        "click": EffectType.RIPPLE,
        "zoom": EffectType.ZOOM,
        "spotlight": EffectType.SPOTLIGHT,
        "callout": EffectType.CALLOUT,
    }

    if effect not in effect_map:
        typer.echo(json.dumps({"success": False, "error": f"Unknown effect: {effect}", "valid_effects": list(effect_map.keys())}))
        raise typer.Exit(1)

    effect_type = effect_map[effect]

    # Build effect parameters based on type
    params = {}
    if effect == "highlight":
        cfg = _effects_config.get("highlight", {})
        params = {
            "width": 200,
            "height": 100,
            "color": cfg.get("color", "FFEB3B").lstrip("#"),
            "opacity": cfg.get("opacity", 0.3),
        }
    elif effect == "click":
        cfg = _effects_config.get("click", {})
        params = {
            "radius": cfg.get("radius", 30),
            "color": cfg.get("color", "FF5722").lstrip("#"),
        }
    elif effect == "zoom":
        cfg = _effects_config.get("zoom", {})
        params = {
            "zoom_factor": cfg.get("factor", 1.5),
        }
    elif effect == "callout":
        cfg = _effects_config.get("callout", {})
        params = {
            "text": text or "Preview",
            "font_size": cfg.get("font_size", 16),
            "text_color": cfg.get("text_color", "FFFFFF").lstrip("#"),
        }

    # Create effect config and event
    config = EffectConfig(
        type=effect_type,
        params=params,
        duration_ms=int(duration * 1000),
    )

    event = EffectEvent(
        type=effect_type,
        timestamp_ms=0,
        position=(x, y),
        config=config,
    )

    compositor.event_queue.add_event(event)

    # Detect if input is image or video
    input_ext = Path(input_file).suffix.lower()
    is_image = input_ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

    if is_image:
        # For images, convert to short video, apply effect, extract frame
        import tempfile
        temp_video = tempfile.mktemp(suffix=".mp4")
        temp_output = tempfile.mktemp(suffix=".mp4")

        try:
            # Convert image to 2-second video
            subprocess.run([
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", input_file,
                "-c:v", "libx264",
                "-t", "2",
                "-pix_fmt", "yuv420p",
                temp_video,
            ], capture_output=True, check=True)

            # Apply effects
            result = compositor.apply_to_video(temp_video, temp_output)

            if result.get("success"):
                # Extract frame back to image
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", temp_output,
                    "-vframes", "1",
                    output,
                ], capture_output=True, check=True)
                typer.echo(json.dumps({"success": True, "output": output, "effect": effect}))
            else:
                typer.echo(json.dumps(result))
                raise typer.Exit(1)

        except subprocess.CalledProcessError as e:
            typer.echo(json.dumps({"success": False, "error": str(e)}))
            raise typer.Exit(1)
        finally:
            # Cleanup
            import os
            for f in [temp_video, temp_output]:
                if os.path.exists(f):
                    os.remove(f)
    else:
        # For video, apply effects directly
        result = compositor.apply_to_video(input_file, output)
        if result.get("success"):
            result["effect"] = effect
        typer.echo(json.dumps(result, indent=2))

        if not result.get("success"):
            raise typer.Exit(1)


@app.command("reset")
def reset() -> None:
    """Reset all effects configuration to defaults.

    Example:
        pdemo effects reset
    """
    global _effects_config

    _effects_config = {
        "enabled": True,
        "highlight": {"enabled": True, "color": "#FFEB3B", "opacity": 0.3},
        "click": {"enabled": True, "radius": 30, "color": "#FF5722", "duration_ms": 300},
        "zoom": {"enabled": True, "factor": 1.5, "duration_ms": 500},
        "callout": {"enabled": True, "font_size": 16, "text_color": "#FFFFFF"},
    }

    typer.echo(json.dumps({"success": True, "message": "Effects configuration reset to defaults"}))
