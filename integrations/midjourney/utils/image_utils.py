"""Image download, save, and path management utilities."""

from __future__ import annotations

import re
import time
from pathlib import Path

import httpx

from integrations.midjourney.utils.logging_config import logger


def sanitize_filename(prompt: str, max_length: int = 80) -> str:
    """Turn a prompt string into a safe filename fragment."""
    name = re.sub(r"[^\w\s-]", "", prompt).strip()
    name = re.sub(r"[\s]+", "_", name)
    return name[:max_length]


def build_image_path(
    output_folder: str | Path,
    prompt: str,
    attempt: int,
    upscale_index: int | None = None,
) -> Path:
    """Return the destination path for a downloaded image."""
    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)
    stem = sanitize_filename(prompt)
    timestamp = int(time.time())
    if upscale_index is not None:
        filename = f"{stem}_U{upscale_index}_attempt{attempt}_{timestamp}.png"
    else:
        filename = f"{stem}_attempt{attempt}_{timestamp}.png"
    return folder / filename


async def download_image(url: str, dest: Path) -> Path:
    """Download an image from *url* and save it to *dest*."""
    logger.info("Downloading image to %s", dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    logger.info("Image saved (%d bytes)", dest.stat().st_size)
    return dest


def download_image_sync(url: str, dest: Path) -> Path:
    """Synchronous version of download_image."""
    logger.info("Downloading image to %s", dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60) as client:
        resp = client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    logger.info("Image saved (%d bytes)", dest.stat().st_size)
    return dest
