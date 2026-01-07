"""CLI commands for running demos, scenes, and steps."""

import json
from pathlib import Path
from typing import Optional

import typer

from programmatic_demo.models import Script
from programmatic_demo.orchestrator import Runner, RunnerConfig

app = typer.Typer(help="Run demo scripts, scenes, or individual steps.")


def _load_script(file: Path) -> Script:
    """Load a script file and return the Script object."""
    if not file.exists():
        raise FileNotFoundError(f"File not found: {file}")

    if file.suffix in (".yaml", ".yml"):
        return Script.from_yaml(file)
    elif file.suffix == ".json":
        return Script.from_json(file)
    else:
        raise ValueError(f"Unsupported file type: {file.suffix}")


def _create_progress_callback(verbose: bool):
    """Create a progress callback that outputs events."""
    def callback(event: dict) -> None:
        event_type = event.get("event", "unknown")

        if event_type == "demo_start":
            if verbose:
                typer.echo(f"Starting demo with {event.get('scenes_total', 0)} scenes")

        elif event_type == "scene_start":
            scene_name = event.get("scene_name") or f"Scene {event.get('scene_index', 0)}"
            if verbose:
                typer.echo(f"  Starting: {scene_name}")

        elif event_type == "scene_complete":
            scene_name = event.get("scene_name") or f"Scene {event.get('scene_index', 0)}"
            duration = event.get("duration", 0)
            if verbose:
                typer.echo(f"  Completed: {scene_name} ({duration:.2f}s)")

        elif event_type == "step_start":
            action = event.get("action", "action")
            step_idx = event.get("step_index", 0)
            if verbose:
                typer.echo(f"    Step {step_idx}: {action}")

        elif event_type == "step_complete":
            retries = event.get("retries", 0)
            if verbose and retries > 0:
                typer.echo(f"      (completed after {retries} retries)")

        elif event_type == "step_failed":
            error = event.get("error", {})
            typer.echo(f"    FAILED: {error.get('message', 'Unknown error')}")

        elif event_type == "demo_complete":
            duration = event.get("duration", 0)
            scenes = event.get("scenes_completed", 0)
            total = event.get("scenes_total", 0)
            if verbose:
                typer.echo(f"Demo completed: {scenes}/{total} scenes ({duration:.2f}s)")

    return callback


@app.command("demo")
def run_demo(
    file: Path = typer.Argument(..., help="Path to script file (YAML or JSON)"),
    verbose: bool = typer.Option(True, "--verbose/--quiet", "-v/-q", help="Show progress"),
    max_retries: int = typer.Option(3, "--retries", "-r", help="Maximum retries per step"),
    step_timeout: float = typer.Option(30.0, "--step-timeout", help="Step timeout in seconds"),
    handle_interrupt: bool = typer.Option(True, "--handle-interrupt/--no-interrupt", help="Handle Ctrl+C gracefully"),
) -> None:
    """Run a complete demo script."""
    try:
        script = _load_script(file)

        # Validate script first
        errors = script.validate()
        if errors:
            result = {"status": "invalid", "errors": errors}
            typer.echo(json.dumps(result, indent=2))
            raise typer.Exit(1)

        # Create runner with config
        config = RunnerConfig(
            max_retries=max_retries,
            step_timeout=step_timeout,
        )

        progress_callback = _create_progress_callback(verbose) if verbose else None
        runner = Runner(config=config, on_progress=progress_callback)

        # Register signal handler if requested
        if handle_interrupt:
            runner.register_signal_handler()

        # Execute demo
        demo_result = runner.execute_demo(script)

        result = {
            "status": "success" if demo_result.success else "failed",
            "scenes_completed": demo_result.scenes_completed,
            "scenes_total": demo_result.scenes_total,
            "duration": demo_result.duration,
            "interrupted": runner.interrupted,
        }

        if runner.interrupted:
            result["interrupt_reason"] = runner.interrupt_reason

        typer.echo(json.dumps(result, indent=2))

        if not demo_result.success:
            raise typer.Exit(1)

    except FileNotFoundError as e:
        result = {"status": "error", "message": str(e)}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)
    except ValueError as e:
        result = {"status": "error", "message": str(e)}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)
    except Exception as e:
        result = {"status": "error", "message": str(e)}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)


@app.command("scene")
def run_scene(
    file: Path = typer.Argument(..., help="Path to script file (YAML or JSON)"),
    scene_index: int = typer.Option(0, "--scene", "-s", help="Scene index to run (0-based)"),
    verbose: bool = typer.Option(True, "--verbose/--quiet", "-v/-q", help="Show progress"),
    max_retries: int = typer.Option(3, "--retries", "-r", help="Maximum retries per step"),
) -> None:
    """Run a single scene from a script."""
    try:
        script = _load_script(file)

        if not script.scenes:
            result = {"status": "error", "message": "Script has no scenes"}
            typer.echo(json.dumps(result, indent=2))
            raise typer.Exit(1)

        if scene_index < 0 or scene_index >= len(script.scenes):
            result = {
                "status": "error",
                "message": f"Invalid scene index {scene_index}. Valid range: 0-{len(script.scenes)-1}",
            }
            typer.echo(json.dumps(result, indent=2))
            raise typer.Exit(1)

        scene = script.scenes[scene_index]

        # Create runner
        config = RunnerConfig(max_retries=max_retries)
        progress_callback = _create_progress_callback(verbose) if verbose else None
        runner = Runner(config=config, on_progress=progress_callback)

        if verbose:
            typer.echo(f"Running scene: {scene.name or f'Scene {scene_index}'}")

        # Execute scene
        scene_result = runner.execute_scene(scene)

        result = {
            "status": "success" if scene_result.success else "failed",
            "steps_completed": scene_result.steps_completed,
            "steps_total": scene_result.steps_total,
            "duration": scene_result.duration,
        }

        if scene_result.error:
            result["error"] = scene_result.error

        typer.echo(json.dumps(result, indent=2))

        if not scene_result.success:
            raise typer.Exit(1)

    except FileNotFoundError as e:
        result = {"status": "error", "message": str(e)}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)
    except ValueError as e:
        result = {"status": "error", "message": str(e)}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)
    except Exception as e:
        result = {"status": "error", "message": str(e)}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)


@app.command("step")
def run_step(
    file: Path = typer.Argument(..., help="Path to script file (YAML or JSON)"),
    scene_index: int = typer.Option(0, "--scene", "-s", help="Scene index (0-based)"),
    step_index: int = typer.Option(0, "--step", "-t", help="Step index (0-based)"),
    max_retries: int = typer.Option(3, "--retries", "-r", help="Maximum retries"),
) -> None:
    """Run a single step from a script."""
    try:
        script = _load_script(file)

        if not script.scenes:
            result = {"status": "error", "message": "Script has no scenes"}
            typer.echo(json.dumps(result, indent=2))
            raise typer.Exit(1)

        if scene_index < 0 or scene_index >= len(script.scenes):
            result = {
                "status": "error",
                "message": f"Invalid scene index {scene_index}. Valid range: 0-{len(script.scenes)-1}",
            }
            typer.echo(json.dumps(result, indent=2))
            raise typer.Exit(1)

        scene = script.scenes[scene_index]

        if not scene.steps:
            result = {"status": "error", "message": f"Scene {scene_index} has no steps"}
            typer.echo(json.dumps(result, indent=2))
            raise typer.Exit(1)

        if step_index < 0 or step_index >= len(scene.steps):
            result = {
                "status": "error",
                "message": f"Invalid step index {step_index}. Valid range: 0-{len(scene.steps)-1}",
            }
            typer.echo(json.dumps(result, indent=2))
            raise typer.Exit(1)

        step = scene.steps[step_index]

        # Create runner
        config = RunnerConfig(max_retries=max_retries)
        runner = Runner(config=config)

        # Convert step to dict
        step_dict = step.to_dict() if hasattr(step, "to_dict") else step

        typer.echo(f"Running step: {step.action.value if hasattr(step, 'action') else step_dict.get('action')}")

        # Execute step
        step_result = runner.execute_step(step_dict)

        result = {
            "status": "success" if step_result.success else "failed",
            "duration": step_result.duration,
            "retries": step_result.retries,
        }

        if step_result.error:
            result["error"] = step_result.error

        typer.echo(json.dumps(result, indent=2))

        if not step_result.success:
            raise typer.Exit(1)

    except FileNotFoundError as e:
        result = {"status": "error", "message": str(e)}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)
    except ValueError as e:
        result = {"status": "error", "message": str(e)}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)
    except Exception as e:
        result = {"status": "error", "message": str(e)}
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)
