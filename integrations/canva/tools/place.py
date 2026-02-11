from pathlib import Path
from typing import Tuple

from playwright.sync_api import Page


def place_image_with_outline(
    page: Page,
    image_path: Path,
    margin_percent: float,
    outline_height_percent: float,
) -> None:
    """
    Insert an uploaded image onto the current page, fit within margins, center it,
    and add a top black outline/rectangle for a clean edge.

    NOTE: Uses placeholder selectors; adjust as needed for Canva UI updates.
    """
    # Insert image from uploads
    page.click("text=Uploads")
    page.click(f"img[alt*='{image_path.name}']", timeout=10_000)

    page.wait_for_timeout(1000)

    # Resize: use keyboard shortcut to fit (placeholder – adjust to real)
    page.keyboard.press("Control+Shift+F")  # hypothetical fit shortcut
    page.wait_for_timeout(500)

    # Add rectangle outline at top
    page.click("text=Elements")
    page.fill("input[placeholder='Search elements']", "rectangle")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)
    page.click("div:has-text('Rectangle') >> nth=0", timeout=10_000)

    page.wait_for_timeout(800)
    # Basic position tweak: align to top center using arrow keys as placeholder
    for _ in range(10):
        page.keyboard.press("ArrowUp")
    for _ in range(10):
        page.keyboard.press("ArrowLeft")
    page.wait_for_timeout(200)

    # Set stroke to black: placeholder selection
    page.click("button:has-text('Border')", timeout=5_000)
    page.click("text=Black", timeout=5_000)
