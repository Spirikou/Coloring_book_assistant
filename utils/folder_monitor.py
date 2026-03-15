"""Compatibility shim: re-export from features.image_generation.monitor.

DEPRECATED: Prefer importing from features.image_generation.monitor directly.
This module is kept for backward compatibility only.
"""

from features.image_generation.monitor import (  # noqa: F401
    get_images_in_folder,
    validate_image_count,
    get_image_metadata,
    IMAGE_EXTENSIONS,
)

__all__ = [
    "get_images_in_folder",
    "validate_image_count",
    "get_image_metadata",
    "IMAGE_EXTENSIONS",
]
