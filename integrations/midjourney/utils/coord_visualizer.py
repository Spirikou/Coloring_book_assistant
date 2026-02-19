"""Draw coordinate overlays on screenshots for debugging."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def draw_coord_overlays(
    image_path: Path,
    output_path: Path,
    button_coordinates: dict[str, list[int]],
    coordinates_viewport: dict[str, int],
    viewport: dict[str, int],
    radius: int = 20,
) -> None:
    """Draw circles and labels at each button coordinate on the screenshot.

    Coordinates are scaled from coordinates_viewport to viewport (same as controller).
    """
    img = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    font = None
    for name in ("arial.ttf", "Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            font = ImageFont.truetype(name, 14)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    ref_w = coordinates_viewport.get("width", 1920)
    ref_h = coordinates_viewport.get("height", 1080)
    tgt_w = viewport.get("width", 1920)
    tgt_h = viewport.get("height", 1080)
    img_w, img_h = img.size

    for key, coords in button_coordinates.items():
        if not coords or len(coords) < 2:
            continue
        x_ref, y_ref = coords[0], coords[1]
        if ref_w == tgt_w and ref_h == tgt_h:
            x, y = int(x_ref), int(y_ref)
        else:
            x = int(x_ref * tgt_w / ref_w)
            y = int(y_ref * tgt_h / ref_h)

        if x < 0 or x >= img_w or y < 0 or y >= img_h:
            continue

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
        label = key.replace("_", " ")
        draw.text((x - 30, y + radius + 4), label, fill="red", font=font)

    img.convert("RGB").save(output_path)
    img.close()
