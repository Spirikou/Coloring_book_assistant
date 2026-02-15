"""Compatibility shim: re-export from features.image_generation.monitor."""

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
