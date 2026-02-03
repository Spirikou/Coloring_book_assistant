"""Pinterest publishing workflow."""

import json
import shutil
import os
from pathlib import Path
from typing import Dict, Callable, Optional
from datetime import datetime

from integrations.pinterest.adapter import publish_pins_with_progress


def _is_streamlit_context() -> bool:
    """Check if we're running in Streamlit context at workflow level."""
    # Method 1: Try importing and checking Streamlit
    try:
        import streamlit as st
        if hasattr(st.runtime, 'scriptrunner'):
            if st.runtime.scriptrunner.is_streamlit_script_run_context():
                return True
    except:
        pass
    
    # Method 2: Check environment variables
    if os.environ.get('STREAMLIT_SERVER_PORT') or os.environ.get('STREAMLIT_SERVER_ADDRESS'):
        return True
    
    # Method 3: Check if streamlit is in sys.modules
    try:
        import sys
        if 'streamlit' in sys.modules:
            return True
    except:
        pass
    
    return False


class PinterestPublishingWorkflow:
    """Manages the Pinterest publishing process."""
    
    def __init__(self):
        self.output_base = Path("./pinterest_publish")
    
    def prepare_publishing_folder(
        self,
        design_state: Dict,
        images_folder: str,
        output_folder: Optional[str] = None
    ) -> str:
        """
        Prepare folder for Pinterest publishing.
        
        Args:
            design_state: State dict with title, description, seo_keywords
            images_folder: Path to folder containing images
            output_folder: Optional custom output folder path
            
        Returns:
            Path to prepared folder
        """
        # Create output folder with timestamp
        if output_folder is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_folder = str(self.output_base / f"publish_{timestamp}")
        
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create JSON config file from design state
        json_config = {
            "title": design_state.get("title", ""),
            "description": design_state.get("description", ""),
            "seo_keywords": design_state.get("seo_keywords", [])
        }
        
        json_file = output_path / "book_config.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_config, f, indent=2, ensure_ascii=False)
        
        # Copy images from images folder
        images_path = Path(images_folder)
        if images_path.exists() and images_path.is_dir():
            image_extensions = [".png", ".jpg", ".jpeg", ".webp"]
            copied_count = 0
            
            for ext in image_extensions:
                for image_file in images_path.glob(f"*{ext}"):
                    shutil.copy2(image_file, output_path / image_file.name)
                    copied_count += 1
            
            if copied_count == 0:
                raise ValueError(f"No images found in {images_folder}")
        else:
            raise ValueError(f"Images folder not found: {images_folder}")
        
        return str(output_path.resolve())
    
    def publish_to_pinterest(
        self,
        folder_path: str,
        board_name: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Publish pins to Pinterest.
        
        Args:
            folder_path: Path to prepared folder with images and JSON
            board_name: Name of Pinterest board
            progress_callback: Optional callback for progress updates
            
        Returns:
            dict with publishing results
        """
        # Detect Streamlit at workflow level and force Streamlit mode
        force_streamlit = _is_streamlit_context()
        
        return publish_pins_with_progress(
            folder_path=folder_path,
            board_name=board_name,
            progress_callback=progress_callback,
            force_streamlit_mode=force_streamlit,
        )

