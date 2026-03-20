"""Debug screenshot utility - capture page with circled click points."""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from playwright.sync_api import Page


def maybe_save_debug(
    debug_ctx: dict[str, Any] | None,
    page: Page,
    step_name: str,
    click_points: list[tuple[int, int] | dict],
) -> None:
    """
    If debug_ctx is enabled, save screenshot with circled click points.
    Increments step counter in debug_ctx.
    """
    if not debug_ctx or not debug_ctx.get("enabled"):
        return
    output_dir = debug_ctx.get("output_dir")
    if not output_dir:
        return
    step = debug_ctx.get("step", 0)
    debug_ctx["step"] = step + 1
    save_debug_screenshot(
        page, output_dir, f"{step:02d}_{step_name}", click_points
    )


def _get_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Get a font for labels."""
    for name in ("arial.ttf", "Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, 14)
        except OSError:
            continue
    return ImageFont.load_default()


def _normalize_point(pt: tuple[int, int] | dict) -> tuple[int, int, str]:
    """Convert point to (x, y, label)."""
    if isinstance(pt, dict):
        x = int(pt.get("x", 0))
        y = int(pt.get("y", 0))
        label = str(pt.get("label", ""))
        return (x, y, label)
    x, y = int(pt[0]), int(pt[1])
    return (x, y, "")


def save_debug_screenshot(
    page: Page,
    output_dir: Path,
    step_name: str,
    click_points: list[tuple[int, int] | dict],
    *,
    radius: int = 20,
) -> Path | None:
    """
    Capture page screenshot and draw circles at each click point.

    Args:
        page: Playwright page object
        output_dir: Directory to save the screenshot
        step_name: Descriptive name for this step (e.g. "create_modal_opened")
        click_points: List of (x, y) or {"x": int, "y": int, "label": str}
        radius: Circle radius in pixels

    Returns:
        Path to saved file, or None if capture failed
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        screenshot_bytes = page.screenshot(full_page=True)
        img = Image.open(io.BytesIO(screenshot_bytes)).convert("RGBA")
        draw = ImageDraw.Draw(img)
        font = _get_font()
        img_w, img_h = img.size

        for i, pt in enumerate(click_points):
            x, y, label = _normalize_point(pt)
            if x < 0 or x >= img_w or y < 0 or y >= img_h:
                continue
            lbl = label or f"click_{i + 1}"
            # Outer white circle (border)
            draw.ellipse(
                (x - radius - 2, y - radius - 2, x + radius + 2, y + radius + 2),
                outline="white",
                width=3,
            )
            # Inner red circle
            draw.ellipse(
                (x - radius, y - radius, x + radius, y + radius),
                outline="red",
                width=2,
            )
            # Crosshair
            draw.line((x - radius - 5, y, x + radius + 5, y), fill="red", width=1)
            draw.line((x, y - radius - 5, x, y + radius + 5), fill="red", width=1)
            # Label
            draw.text((x - 30, y + radius + 4), lbl, fill="red", font=font)

        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{step_name}_{timestamp}.png"
        output_path = output_dir / filename
        img.convert("RGB").save(output_path)
        img.close()
        return output_path
    except Exception:
        return None
