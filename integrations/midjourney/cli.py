"""Command-line interface for Midjourney Agent."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Windows: ProactorEventLoop required for Playwright subprocess support
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from typing import Optional

import click

from integrations.midjourney import AgentConfig, run_agent
from integrations.midjourney.config import get_file_config_overrides
from integrations.midjourney.automation.health_check import run_health_checks
from integrations.midjourney.automation.browser_utils import check_browser_connection
from integrations.midjourney.automation.browser_config import DEBUG_FOLDER, DEBUG_PORT
from config import PROJECT_ROOT


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    help="Path to config.json (default: project_root/config.json)",
)
@click.pass_context
def cli(ctx: click.Context, config: Optional[str]) -> None:
    """Midjourney Automation Agent — CLI."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = Path(config) if config else (PROJECT_ROOT / "config.json")


@cli.command()
@click.argument("prompt", nargs=-1, required=True)
@click.option("--output", "-o", type=click.Path(), default="./output")
@click.option("--dry-run", is_flag=True, help="Simulate without browser interaction")
@click.option("--browser-port", type=int, default=None, help=f"Browser debug port (default: {DEBUG_PORT})")
@click.option("--max-retries", type=int, default=3)
@click.pass_context
def run(
    ctx: click.Context,
    prompt: tuple[str, ...],
    output: str,
    dry_run: bool,
    browser_port: Optional[int],
    max_retries: int,
) -> None:
    """Run one or more prompts."""
    prompts = list(prompt)
    file_overrides = get_file_config_overrides(ctx.obj.get("config_path"))
    cfg_kw = {**file_overrides, "output_folder": Path(output), "dry_run": dry_run, "max_retries": max_retries}
    if browser_port is not None:
        cfg_kw["browser_debug_port"] = browser_port
    cfg = AgentConfig(**cfg_kw)

    if not dry_run:
        health = run_health_checks(
            output_folder=Path(output),
            browser_port=cfg.browser_debug_port,
        )
        if health.has_errors():
            for c in health.checks:
                if c.severity == "error" and not c.status:
                    click.echo(f"  ✗ {c.name}: {c.message}", err=True)
            sys.exit(1)

    result = run_agent(prompts=prompts, config=cfg)
    tasks = result.get("tasks", [])
    for i, t in enumerate(tasks):
        status = t.get("status", "?")
        click.echo(f"  {i+1}. {status}: {t.get('prompt', '')[:50]}...")
    failed = sum(1 for t in tasks if t.get("status") == "failed")
    sys.exit(1 if failed > 0 else 0)


@cli.command()
@click.option("--file", "-f", type=click.Path(exists=True), required=True)
@click.option("--output", "-o", type=click.Path(), default="./output")
@click.option("--dry-run", is_flag=True)
@click.option("--browser-port", type=int, default=None, help=f"Browser debug port (default: {DEBUG_PORT})")
@click.pass_context
def queue(
    ctx: click.Context,
    file: str,
    output: str,
    dry_run: bool,
    browser_port: Optional[int],
) -> None:
    """Process prompts from file (one per line)."""
    path = Path(file)
    prompts = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not prompts:
        click.echo("No prompts found in file", err=True)
        sys.exit(1)

    file_overrides = get_file_config_overrides(ctx.obj.get("config_path"))
    cfg_kw = {**file_overrides, "output_folder": Path(output), "dry_run": dry_run}
    if browser_port is not None:
        cfg_kw["browser_debug_port"] = browser_port
    cfg = AgentConfig(**cfg_kw)

    if not dry_run:
        health = run_health_checks(
            output_folder=Path(output),
            browser_port=cfg.browser_debug_port,
        )
        if health.has_errors():
            sys.exit(1)

    result = run_agent(prompts=prompts, config=cfg)
    tasks = result.get("tasks", [])
    ok = sum(1 for t in tasks if t.get("status") == "accepted")
    click.echo(f"Done: {ok}/{len(tasks)} accepted")
    sys.exit(0 if ok == len(tasks) else 1)


@cli.command()
@click.option("--port", "-p", type=int, default=DEBUG_PORT, help="Browser debug port")
@click.pass_context
def setup(ctx: click.Context, port: int) -> None:
    """First-time setup: create config from template, then record button coordinates."""
    config_path = ctx.obj.get("config_path", Path("config.json"))
    example_path = config_path.parent / "config.example.json"

    if not config_path.exists() and example_path.exists():
        import shutil
        shutil.copy(example_path, config_path)
        click.echo(f"Created {config_path} from template.")

    file_overrides = get_file_config_overrides(config_path)
    button_coords = file_overrides.get("button_coordinates") or {}

    if not button_coords:
        click.echo("Button coordinates not configured. Running record-coords...")
        click.echo("Ensure your browser is open with remote debugging on port 9222.")
        click.echo("")
        ctx.invoke(record_coords, output=str(DEBUG_FOLDER / "button_coordinates.json"), port=port, no_nav=False)
        click.echo("")
        click.echo("Copy button_coordinates and coordinates_viewport from debug/button_coordinates.json into config.json.")
    else:
        click.echo("Config already has button coordinates. Run record-coords to re-capture for a different screen.")


@cli.command()
@click.option("--port", "-p", type=int, default=DEBUG_PORT, help="Browser debug port")
def test_browser(port: int) -> None:
    """Test browser connection on debug port."""
    status = check_browser_connection(port)
    if status["connected"]:
        click.echo(f"✓ Browser connected on port {port}")
    else:
        click.echo(f"✗ Browser not connected on port {port}", err=True)
        click.echo(f"  {status.get('error', 'Unknown error')}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--output", "-o", type=click.Path(), default=None, help="Output path (default: debug/detail_view_screenshot.png)")
@click.option("--port", "-p", type=int, default=DEBUG_PORT, help="Browser debug port")
@click.option("--no-nav", is_flag=True, help="Skip navigation; connect and capture current page")
@click.pass_context
def capture(
    ctx: click.Context,
    output: str,
    port: int,
    no_nav: bool,
) -> None:
    """Capture screenshot for coordinate discovery."""
    if output is None:
        output = str(DEBUG_FOLDER / "detail_view_screenshot.png")
    from integrations.midjourney.automation.midjourney_web_controller import (
        MidjourneyWebController,
        MIDJOURNEY_IMAGINE_URL,
    )

    file_overrides = get_file_config_overrides(ctx.obj.get("config_path"))
    viewport = file_overrides.get("viewport") or {"width": 1920, "height": 1080}
    controller = MidjourneyWebController(debug_port=port, dry_run=False, viewport=viewport)
    try:
        controller.connect()
        if not no_nav:
            import time
            controller.page.goto(MIDJOURNEY_IMAGINE_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            click.echo("Navigate to the detail view (click an image), then press Enter to capture...")
        else:
            click.echo("Press Enter to capture the current page...")
        w, h = viewport.get("width", 1920), viewport.get("height", 1080)
        click.echo(f"Viewport set to {w}x{h}. Screenshot coordinates will match when config.viewport matches.")
        input()
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        controller.page.screenshot(path=str(out_path))
        click.echo(f"Screenshot saved to {out_path}")
        click.echo("Open it in an image editor to read x,y coordinates for each button.")
    finally:
        controller.close()


@cli.command()
@click.option("--output", "-o", type=click.Path(), default=None, help="Output path (default: debug/coords_preview.png)")
@click.option("--port", "-p", type=int, default=DEBUG_PORT, help="Browser debug port")
@click.option("--no-nav", is_flag=True, help="Skip navigation; use current page")
@click.pass_context
def visualize_coords(
    ctx: click.Context,
    output: str,
    port: int,
    no_nav: bool,
) -> None:
    """Capture screenshot with coordinate overlays for debugging."""
    if output is None:
        output = str(DEBUG_FOLDER / "coords_preview.png")
    import time
    from integrations.midjourney.automation.midjourney_web_controller import (
        MidjourneyWebController,
        MIDJOURNEY_IMAGINE_URL,
    )
    from integrations.midjourney.utils.coord_visualizer import draw_coord_overlays

    file_overrides = get_file_config_overrides(ctx.obj.get("config_path"))
    viewport = file_overrides.get("viewport") or {"width": 1920, "height": 1080}
    coordinates_viewport = file_overrides.get("coordinates_viewport") or {"width": 1920, "height": 1080}
    button_coords = file_overrides.get("button_coordinates") or {}

    if not button_coords:
        click.echo("No button_coordinates in config. Run record-coords first.", err=True)
        sys.exit(1)

    controller = MidjourneyWebController(
        debug_port=port,
        dry_run=False,
        viewport=viewport,
        coordinates_viewport=coordinates_viewport,
    )
    try:
        controller.connect()
        if not no_nav:
            controller.page.goto(MIDJOURNEY_IMAGINE_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            click.echo("Navigate to the detail view (click an image), then press Enter to capture...")
        else:
            click.echo("Press Enter to capture with coordinate overlays...")
        w, h = viewport.get("width", 1920), viewport.get("height", 1080)
        click.echo(f"Viewport {w}x{h}. Red circles show where the app will click.")
        input()
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path = out_path.parent / f"_raw_{out_path.name}"
        controller.page.screenshot(path=str(raw_path))
        draw_coord_overlays(
            raw_path,
            out_path,
            button_coords,
            coordinates_viewport,
            viewport,
        )
        raw_path.unlink(missing_ok=True)
        click.echo(f"Saved to {out_path}")
        click.echo("Red circles = click targets. Verify they align with the buttons.")
    finally:
        controller.close()


@cli.command()
@click.option("--output", "-o", type=click.Path(), default=None, help="Output path (default: debug/button_coordinates.json)")
@click.option("--port", "-p", type=int, default=DEBUG_PORT, help="Browser debug port")
@click.option("--no-nav", is_flag=True, help="Skip navigation; use current page")
@click.pass_context
def record_coords(
    ctx: click.Context,
    output: str,
    port: int,
    no_nav: bool,
) -> None:
    """Record button coordinates by clicking each button in order."""
    if output is None:
        output = str(DEBUG_FOLDER / "button_coordinates.json")
    import json
    import time
    from integrations.midjourney.automation.midjourney_web_controller import (
        MidjourneyWebController,
        MIDJOURNEY_IMAGINE_URL,
    )

    file_overrides = get_file_config_overrides(ctx.obj.get("config_path"))
    viewport = file_overrides.get("viewport") or {"width": 1920, "height": 1080}
    controller = MidjourneyWebController(debug_port=port, dry_run=False, viewport=viewport)
    buttons = [
        ("download", "Download"),
        ("vary_subtle", "Vary Subtle"),
        ("vary_strong", "Vary Strong"),
        ("upscale_subtle", "Upscale Subtle"),
        ("upscale_creative", "Upscale Creative"),
    ]
    coords: dict[str, list[int]] = {}

    try:
        controller.connect()
        w, h = viewport.get("width", 1920), viewport.get("height", 1080)
        click.echo(f"Viewport set to {w}x{h}. Use this size when running automation.")
        if not no_nav:
            controller.page.goto(MIDJOURNEY_IMAGINE_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            click.echo("Navigate to the detail view (click an image), then press Enter...")
            input()

        for key, label in buttons:
            click.echo(f"Click the '{label}' button (30s timeout)...")

            def make_handler(k: str) -> None:
                def handler(x: float, y: float) -> None:
                    coords[k] = [int(x), int(y)]
                return handler

            controller.page.expose_function("_recordClick", make_handler(key))
            controller.page.evaluate(
                """
                () => {
                    const handler = (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        window._recordClick(e.clientX, e.clientY);
                        document.removeEventListener('click', handler, true);
                    };
                    document.addEventListener('click', handler, true);
                }
                """
            )
            for _ in range(30):
                if key in coords:
                    break
                time.sleep(1)
            else:
                click.echo("  -> timed out, skipped")

            if key in coords:
                click.echo(f"  -> {coords[key]}")

        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        output_data = {"_viewport": viewport, "_coordinates_viewport": viewport, **coords}
        out_path.write_text(json.dumps(output_data, indent=2))
        click.echo(f"Saved to {out_path}")
        click.echo("Copy button_coordinates and coordinates_viewport (from _coordinates_viewport) into config.json.")
    finally:
        controller.close()


def main() -> None:
    """Entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
