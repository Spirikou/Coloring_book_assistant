"""Image handling utilities for thumbnails and validation."""

import os
from pathlib import Path
from typing import Optional
from PIL import Image
import io

# Supported image file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}


def validate_image_file(file_path: str) -> bool:
    """
    Validate that file is a valid image.
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        True if file is a valid image, False otherwise
    """
    if not os.path.exists(file_path):
        return False
    
    file_path_obj = Path(file_path)
    
    # Check extension
    if file_path_obj.suffix.lower() not in IMAGE_EXTENSIONS:
        return False
    
    # Try to open with PIL to verify it's actually an image
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def create_thumbnail(image_path: str, size: tuple = (200, 200)) -> Optional[bytes]:
    """
    Create thumbnail for gallery display.
    
    Args:
        image_path: Path to the source image
        size: Tuple of (width, height) for thumbnail size
        
    Returns:
        Bytes of the thumbnail image, or None if creation fails
    """
    if not validate_image_file(image_path):
        return None
    
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (handles RGBA, P mode, etc.)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create a white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Create thumbnail maintaining aspect ratio
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            return buffer.getvalue()
    except Exception:
        return None

