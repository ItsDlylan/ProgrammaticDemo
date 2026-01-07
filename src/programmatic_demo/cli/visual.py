"""CLI commands for visual verification and smart recording."""

import json
from pathlib import Path
from typing import Optional

import typer

from programmatic_demo.actuators.browser import get_browser
from programmatic_demo.utils.output import error_response, success_response

app = typer.Typer(help="Visual verification and smart recording commands.")


def _get_page():
    """Get active browser page or return error."""
    browser = get_browser()
    page = browser.get_page()
    if page is None:
        return None, error_response(
            "no_browser",
            "No browser page available. Launch browser first with 'pdemo browser launch'",
            recoverable=True,
            suggestion="Run 'pdemo browser launch --url <url>' first",
        )
    return page, None


@app.command("detect-sections")
def detect_sections(
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Output as JSON"
    ),
) -> None:
    """Detect semantic sections on the current page.

    Analyzes the page DOM to find sections like hero, features, pricing, etc.
    """
    page, error = _get_page()
    if error:
        typer.echo(json.dumps(error, indent=2))
        raise typer.Exit(1)

    from programmatic_demo.visual.section_detector import SectionDetector

    detector = SectionDetector(page)
    sections = detector.find_sections()

    if json_output:
        result = {
            "status": "success",
            "action": "detect_sections",
            "data": {
                "count": len(sections),
                "sections": [
                    {
                        "name": s.name,
                        "type": s.section_type,
                        "top": s.bounds.top,
                        "height": s.bounds.height,
                        "scroll_position": s.scroll_position,
                    }
                    for s in sections
                ],
            },
        }
        typer.echo(json.dumps(result, indent=2))
    else:
        typer.echo(f"Detected {len(sections)} sections:\n")
        for i, section in enumerate(sections):
            typer.echo(
                f"  {i + 1}. {section.name} ({section.section_type})\n"
                f"     Position: {section.bounds.top:.0f}px, "
                f"Height: {section.bounds.height:.0f}px"
            )


@app.command("generate-waypoints")
def generate_waypoints(
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file path for waypoints JSON"
    ),
    min_height: float = typer.Option(
        200, "--min-height", help="Minimum section height to include"
    ),
    include_return: bool = typer.Option(
        True, "--include-return/--no-return", help="Include return to top waypoint"
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Output as JSON"
    ),
) -> None:
    """Generate scroll waypoints from page sections.

    Analyzes the page and generates optimal waypoints for demo recording.
    """
    page, error = _get_page()
    if error:
        typer.echo(json.dumps(error, indent=2))
        raise typer.Exit(1)

    from programmatic_demo.visual.waypoint_generator import WaypointGenerator

    viewport_size = page.viewport_size or {"height": 800}
    generator = WaypointGenerator(page, viewport_height=viewport_size["height"])

    waypoints = generator.generate_waypoints(
        include_return_to_top=include_return,
        min_section_height=min_height,
    )

    if output:
        generator.export_waypoints_json(output, include_return_to_top=include_return)
        typer.echo(f"Waypoints saved to {output}")

    if json_output:
        result = {
            "status": "success",
            "action": "generate_waypoints",
            "data": {
                "count": len(waypoints),
                "waypoints": [
                    {
                        "name": w.name,
                        "position": w.position,
                        "pause": w.pause,
                        "scroll_duration": w.scroll_duration,
                        "description": w.description,
                    }
                    for w in waypoints
                ],
            },
        }
        typer.echo(json.dumps(result, indent=2))
    elif not output:
        typer.echo(f"Generated {len(waypoints)} waypoints:\n")
        for i, wp in enumerate(waypoints):
            typer.echo(
                f"  {i + 1}. {wp.name}\n"
                f"     Position: {wp.position:.0f}px, "
                f"Pause: {wp.pause:.1f}s, Scroll: {wp.scroll_duration:.1f}s"
            )


@app.command("preview")
def preview(
    waypoints_file: Optional[str] = typer.Option(
        None, "--waypoints", "-w", help="Waypoints JSON file (auto-generates if not provided)"
    ),
    output_dir: str = typer.Option(
        "preview_screenshots", "--output-dir", "-o", help="Directory for preview screenshots"
    ),
    pause: float = typer.Option(
        1.0, "--pause", "-p", help="Pause duration at each waypoint"
    ),
    no_screenshots: bool = typer.Option(
        False, "--no-screenshots", help="Skip screenshot capture"
    ),
    report_format: str = typer.Option(
        "json", "--format", "-f", help="Report format: json or html"
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Output as JSON"
    ),
) -> None:
    """Preview waypoints before recording.

    Scrolls through each waypoint, captures screenshots, and generates a report.
    """
    page, error = _get_page()
    if error:
        typer.echo(json.dumps(error, indent=2))
        raise typer.Exit(1)

    from programmatic_demo.visual.base import Waypoint
    from programmatic_demo.visual.preview_mode import (
        PreviewConfig,
        WaypointPreviewer,
    )
    from programmatic_demo.visual.waypoint_generator import WaypointGenerator

    # Load or generate waypoints
    if waypoints_file:
        with open(waypoints_file) as f:
            data = json.load(f)
        waypoints_data = data.get("waypoints", data)
        waypoints = [
            Waypoint(
                name=w["name"],
                position=w["position"],
                pause=w.get("pause", 2.0),
                scroll_duration=w.get("scroll_duration", 1.5),
                description=w.get("description", ""),
            )
            for w in waypoints_data
        ]
    else:
        viewport_size = page.viewport_size or {"height": 800}
        generator = WaypointGenerator(page, viewport_height=viewport_size["height"])
        waypoints = generator.generate_waypoints()

    # Configure preview
    config = PreviewConfig(
        pause_duration=pause,
        capture_screenshots=not no_screenshots,
        screenshot_dir=output_dir,
    )

    previewer = WaypointPreviewer(page, config)
    previews = previewer.preview_all(waypoints, interactive=False)
    report = previewer.generate_report(waypoints)

    # Export report
    report_path = f"{output_dir}/preview_report.{report_format}"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if report_format == "json":
        previewer.export_report_json(report, report_path)
    else:
        previewer.export_report_html(report, report_path)

    if json_output:
        result = {
            "status": "success",
            "action": "preview",
            "data": {
                "waypoints_previewed": len(previews),
                "total_scroll_distance": report.total_scroll_distance,
                "estimated_duration": report.estimated_duration,
                "screenshot_dir": output_dir if not no_screenshots else None,
                "report_path": report_path,
            },
        }
        typer.echo(json.dumps(result, indent=2))
    else:
        typer.echo(f"Preview complete:")
        typer.echo(f"  - Waypoints: {len(previews)}")
        typer.echo(f"  - Total scroll: {report.total_scroll_distance:.0f}px")
        typer.echo(f"  - Est. duration: {report.estimated_duration:.1f}s")
        typer.echo(f"  - Report: {report_path}")
        if not no_screenshots:
            typer.echo(f"  - Screenshots: {output_dir}/")


@app.command("verify-framing")
def verify_framing(
    selector: Optional[str] = typer.Option(
        None, "--selector", "-s", help="CSS selector for element to verify"
    ),
    section: Optional[str] = typer.Option(
        None, "--section", help="Section name to verify"
    ),
    position: Optional[float] = typer.Option(
        None, "--position", "-p", help="Expected scroll position"
    ),
    tolerance: int = typer.Option(
        30, "--tolerance", "-t", help="Tolerance in pixels"
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Output as JSON"
    ),
) -> None:
    """Verify that an element or section is properly framed.

    Checks if the target is visible and properly positioned in the viewport.
    """
    page, error = _get_page()
    if error:
        typer.echo(json.dumps(error, indent=2))
        raise typer.Exit(1)

    if not selector and not section and position is None:
        result = error_response(
            "missing_target",
            "Must specify --selector, --section, or --position",
            recoverable=True,
        )
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(1)

    from programmatic_demo.visual.section_detector import SectionDetector
    from programmatic_demo.visual.element_bounds import ElementBoundsDetector
    from programmatic_demo.visual.framing_rules import is_element_properly_framed, get_rule_for_section_type
    from programmatic_demo.visual.base import Viewport

    # Get viewport
    viewport_size = page.viewport_size or {"width": 1280, "height": 800}
    scroll_y = page.evaluate("window.scrollY")
    viewport = Viewport(
        width=viewport_size["width"],
        height=viewport_size["height"],
        scroll_y=scroll_y,
    )

    issues = []
    verified = False

    if selector:
        # Verify element by selector
        detector = ElementBoundsDetector(page)
        bounds = detector.get_bounds(selector)
        if bounds:
            rule = get_rule_for_section_type("default")
            verified = is_element_properly_framed(bounds, viewport, rule, tolerance)
            if not verified:
                issues.append(f"Element '{selector}' not properly framed")
        else:
            issues.append(f"Element '{selector}' not found")

    elif section:
        # Verify section by name
        section_detector = SectionDetector(page)
        found = section_detector.find_section_by_name(section)
        if found:
            rule = get_rule_for_section_type(found.section_type)
            verified = is_element_properly_framed(found.bounds, viewport, rule, tolerance)
            if not verified:
                issues.append(f"Section '{section}' not properly framed")
        else:
            issues.append(f"Section '{section}' not found")

    elif position is not None:
        # Verify scroll position
        position_diff = abs(scroll_y - position)
        verified = position_diff <= tolerance
        if not verified:
            issues.append(
                f"Scroll position mismatch: expected {position:.0f}, "
                f"actual {scroll_y:.0f} (diff: {position_diff:.0f})"
            )

    if json_output:
        result = {
            "status": "success" if verified else "error",
            "action": "verify_framing",
            "data": {
                "verified": verified,
                "current_scroll": scroll_y,
                "viewport_height": viewport.height,
                "issues": issues,
            },
        }
        typer.echo(json.dumps(result, indent=2))
    else:
        if verified:
            typer.echo("Framing verified: OK")
        else:
            typer.echo("Framing issues:")
            for issue in issues:
                typer.echo(f"  - {issue}")

    if not verified:
        raise typer.Exit(1)


@app.command("smart-record")
def smart_record(
    output: str = typer.Option(
        "demo.mp4", "--output", "-o", help="Output video file path"
    ),
    fps: int = typer.Option(30, "--fps", help="Frames per second"),
    preview_first: bool = typer.Option(
        False, "--preview", "-p", help="Preview waypoints before recording"
    ),
    waypoints_file: Optional[str] = typer.Option(
        None, "--waypoints", "-w", help="Use existing waypoints file"
    ),
    min_height: float = typer.Option(
        200, "--min-height", help="Minimum section height"
    ),
    pause_multiplier: float = typer.Option(
        1.0, "--pause-mult", help="Multiplier for pause durations"
    ),
    scroll_multiplier: float = typer.Option(
        1.0, "--scroll-mult", help="Multiplier for scroll durations"
    ),
    no_return: bool = typer.Option(
        False, "--no-return", help="Don't return to top at end"
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Output as JSON"
    ),
) -> None:
    """Execute a smart demo recording.

    Auto-detects sections, generates waypoints, and records the demo
    with intelligent animation waiting and framing verification.
    """
    page, error = _get_page()
    if error:
        typer.echo(json.dumps(error, indent=2))
        raise typer.Exit(1)

    from programmatic_demo.visual.smart_recorder import (
        RecordingConfig,
        SmartDemoRecorder,
    )
    from programmatic_demo.visual.base import Waypoint
    from programmatic_demo.visual.preview_mode import (
        PreviewConfig,
        WaypointPreviewer,
    )

    # Configure recording
    config = RecordingConfig(
        output_path=output,
        fps=fps,
        min_section_height=min_height,
        include_return_to_top=not no_return,
        pause_multiplier=pause_multiplier,
        scroll_duration_multiplier=scroll_multiplier,
    )

    recorder = SmartDemoRecorder(page, config)

    # Load custom waypoints if provided
    if waypoints_file:
        with open(waypoints_file) as f:
            data = json.load(f)
        waypoints_data = data.get("waypoints", data)
        waypoints = [
            Waypoint(
                name=w["name"],
                position=w["position"],
                pause=w.get("pause", 2.0),
                scroll_duration=w.get("scroll_duration", 1.5),
                description=w.get("description", ""),
            )
            for w in waypoints_data
        ]
        recorder.set_waypoints(waypoints)
    else:
        # Auto-detect and generate
        recorder.detect_sections()
        recorder.generate_waypoints()

    # Preview if requested
    if preview_first:
        typer.echo("Starting preview mode...")
        preview_config = PreviewConfig(
            pause_duration=0.5,
            capture_screenshots=False,
        )
        previewer = WaypointPreviewer(page, preview_config)
        previewer.preview_all(recorder.get_waypoints(), interactive=False)

        if not typer.confirm("Proceed with recording?"):
            typer.echo("Recording cancelled.")
            raise typer.Exit(0)

    # Progress callback
    if not json_output:
        def progress_callback(progress):
            typer.echo(
                f"[{progress.current_waypoint + 1}/{progress.total_waypoints}] "
                f"{progress.phase}: {progress.message}"
            )
        recorder.set_progress_callback(progress_callback)

    # Execute recording
    typer.echo("Starting recording..." if not json_output else "")
    result = recorder.record()

    if json_output:
        output_data = {
            "status": "success" if result.success else "error",
            "action": "smart_record",
            "data": {
                "success": result.success,
                "output_path": result.output_path,
                "duration": result.duration,
                "waypoints_visited": result.waypoints_visited,
                "sections_detected": result.sections_detected,
                "framing_corrections": result.framing_corrections,
                "animation_waits": result.animation_waits,
                "errors": result.errors,
            },
        }
        typer.echo(json.dumps(output_data, indent=2))
    else:
        if result.success:
            typer.echo(f"\nRecording complete:")
            typer.echo(f"  - Output: {result.output_path}")
            typer.echo(f"  - Duration: {result.duration:.1f}s")
            typer.echo(f"  - Waypoints: {result.waypoints_visited}")
            typer.echo(f"  - Sections: {result.sections_detected}")
        else:
            typer.echo(f"\nRecording failed:")
            for err in result.errors:
                typer.echo(f"  - {err}")
            raise typer.Exit(1)


@app.command("sections")
def list_section_types() -> None:
    """List all supported section types and their detection patterns."""
    from programmatic_demo.visual.section_detector import SECTION_TYPE_PATTERNS

    typer.echo("Supported section types:\n")
    for section_type, patterns in SECTION_TYPE_PATTERNS.items():
        typer.echo(f"  {section_type}:")
        typer.echo(f"    Patterns: {', '.join(patterns[:3])}...")
