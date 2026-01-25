"""Folder monitoring utilities for image files."""

import os
from pathlib import Path
from typing import List, Dict
from datetime import datetime


# Supported image file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}


def get_images_in_folder(folder_path: str) -> List[str]:
    """
    Scan folder for image files and return list of paths.
    
    Args:
        folder_path: Path to the folder to scan
        
    Returns:
        List of full paths to image files found in the folder
    """
    if not folder_path or not os.path.exists(folder_path):
        return []
    
    folder = Path(folder_path)
    if not folder.is_dir():
        return []
    
    image_files = []
    for file_path in folder.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS:
            image_files.append(str(file_path))
    
    # Sort by filename for consistent ordering
    image_files.sort()
    return image_files


def validate_image_count(folder_path: str, expected_count: int) -> Dict:
    """
    Check if folder has expected number of images.
    
    Args:
        folder_path: Path to the folder to check
        expected_count: Expected number of images
        
    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "found_count": int,
            "expected_count": int,
            "missing_count": int,
            "status": str  # "complete", "partial", "empty", "excess"
        }
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
        Dictionary with metadata:
        {
            "filename": str,
            "size_bytes": int,
            "size_mb": float,
            "modified_time": str,
            "extension": str
        }
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

