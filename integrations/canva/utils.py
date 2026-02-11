import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, List


IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]


def setup_file_logging(log_dir: str = ".") -> Path:
    """
    Configure file logging with timestamped filename and return the log path.
    """
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    log_filename = f"canva_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = Path(log_dir) / log_filename
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(file_handler)
    return log_path


def _find_images(folder_path: Path) -> List[Path]:
    """
    Find all image files in the folder, avoiding duplicates.
    On Windows, file systems are case-insensitive, so we deduplicate by resolving paths.
    """
    images_set = set()  # Use set to avoid duplicates
    for ext in IMAGE_EXTENSIONS:
        # Search for both lowercase and uppercase extensions
        for pattern in [f"*{ext}", f"*{ext.upper()}"]:
            found = list(folder_path.glob(pattern))
            # Resolve paths to handle case-insensitive duplicates on Windows
            for img_path in found:
                # Use resolved path to avoid duplicates (Windows is case-insensitive)
                resolved = img_path.resolve()
                images_set.add(resolved)

    # Convert back to list and sort
    images = sorted(list(images_set))
    return images


def validate_folder(folder: str) -> Path:
    folder_path = Path(folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")
    if not folder_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {folder}")
    images = _find_images(folder_path)
    if not images:
        raise FileNotFoundError(f"No images found in {folder}")
    return folder_path


def chunk_pairs(items: Iterable[Path]) -> List[tuple[Path, Path | None]]:
    """
    Return list of tuples for pairing each image with a blank follower page slot.
    Second item may be None to signal no paired blank page content.
    """
    result: List[tuple[Path, Path | None]] = []
    for item in items:
        result.append((item, None))
    return result
