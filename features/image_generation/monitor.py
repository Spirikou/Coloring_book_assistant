"""Folder monitoring utilities for image files.

By default, image discovery is recursive to support design packages that organize
downloads into nested subfolders (e.g. one subfolder per concept/style). This
keeps the filesystem tidy while still allowing the dashboard and downstream tabs
to "see" all images under a package folder.
"""

import os
from pathlib import Path
from typing import Dict, Iterable, List, Set
from datetime import datetime


# Supported image file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}

DEFAULT_EXCLUDE_DIR_NAMES: Set[str] = {"cover", "__pycache__"}


def _iter_image_files(
    folder: Path,
    *,
    recursive: bool,
    exclude_dir_names: Set[str],
) -> Iterable[Path]:
    if not recursive:
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                yield p
        return

    for p in folder.rglob("*"):
        if p.is_dir() and p.name in exclude_dir_names:
            # rglob doesn't support pruning; skip by not yielding and relying on path checks below.
            continue
        if not p.is_file():
            continue
        # Exclude files that live under excluded directories anywhere in the path
        if any(part in exclude_dir_names for part in p.parts):
            continue
        if p.suffix.lower() in IMAGE_EXTENSIONS:
            yield p


def get_images_in_folder(
    folder_path: str,
    *,
    recursive: bool = True,
    exclude_dir_names: Set[str] | None = None,
) -> List[str]:
    """
    Scan folder for image files and return list of paths.

    Args:
        folder_path: Path to the folder to scan

    Args:
        recursive: If True, scan nested subfolders too (recommended for design packages).
        exclude_dir_names: Directory names to ignore anywhere in the path (defaults include "cover").

    Returns:
        List of full paths to image files found in the folder
    """
    if not folder_path or not os.path.exists(folder_path):
        return []

    folder = Path(folder_path)
    if not folder.is_dir():
        return []

    exclude = exclude_dir_names or DEFAULT_EXCLUDE_DIR_NAMES
    image_files = [str(p) for p in _iter_image_files(folder, recursive=recursive, exclude_dir_names=exclude)]

    # Sort by filename for consistent ordering
    image_files.sort()
    return image_files


def list_images_in_folder(
    folder_path: str,
    *,
    recursive: bool = True,
    exclude_dir_names: Set[str] | None = None,
) -> List[Path]:
    """
    Scan folder for image files and return list of Paths sorted by mtime (newest first).
    Used for downloaded images gallery.
    """
    if not folder_path or not os.path.exists(folder_path):
        return []

    folder = Path(folder_path)
    if not folder.is_dir():
        return []

    exclude = exclude_dir_names or DEFAULT_EXCLUDE_DIR_NAMES
    paths = list(_iter_image_files(folder, recursive=recursive, exclude_dir_names=exclude))
    return sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)


def validate_image_count(folder_path: str, expected_count: int) -> Dict:
    """
    Check if folder has expected number of images.

    Args:
        folder_path: Path to the folder to check
        expected_count: Expected number of images

    Returns:
        Dictionary with validation results
    """
    found_images = get_images_in_folder(folder_path)
    found_count = len(found_images)

    if found_count == 0:
        status = "empty"
    elif found_count < expected_count:
        status = "partial"
    elif found_count == expected_count:
        status = "complete"
    else:
        status = "excess"

    return {
        "valid": found_count >= expected_count,
        "found_count": found_count,
        "expected_count": expected_count,
        "missing_count": max(0, expected_count - found_count),
        "status": status
    }


def get_image_metadata(image_path: str) -> Dict:
    """
    Get image file metadata.

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary with metadata
    """
    if not os.path.exists(image_path):
        return {}

    file_path = Path(image_path)
    stat = file_path.stat()

    return {
        "filename": file_path.name,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "extension": file_path.suffix.lower()
    }
