"""Canva design workflow."""

import os
from pathlib import Path
from typing import Dict, Callable, Optional, List

from integrations.canva.adapter import create_design_with_progress
from integrations.canva.config import (
    DEFAULT_PAGE_SIZE,
    DEFAULT_MARGIN_PERCENT,
    DEFAULT_OUTLINE_HEIGHT_PERCENT,
    DEFAULT_BLANK_BETWEEN,
)


def _is_streamlit_context() -> bool:
    """Check if we're running in Streamlit context at workflow level."""
    try:
        import streamlit as st
        if hasattr(st.runtime, 'scriptrunner'):
            if st.runtime.scriptrunner.is_streamlit_script_run_context():
                return True
    except Exception:
        pass

    if os.environ.get('STREAMLIT_SERVER_PORT') or os.environ.get('STREAMLIT_SERVER_ADDRESS'):
        return True

    try:
        import sys
        if 'streamlit' in sys.modules:
            return True
    except Exception:
        pass

    return False


class CanvaDesignWorkflow:
    """Manages the Canva design creation process."""

    def create_design(
        self,
        images_folder: str,
        page_size: Optional[str] = None,
        page_count: Optional[int] = None,
        margin_percent: Optional[float] = None,
        outline_height_percent: Optional[float] = None,
        blank_between: Optional[bool] = None,
        progress_callback: Optional[Callable] = None,
        dry_run: bool = False,
        selected_images: Optional[List[str]] = None,
    ) -> Dict:
        """
        Create Canva design from images in folder.

        Uses the same images_folder_path as Pinterest (shared workflow data).

        Args:
            images_folder: Path to folder containing images (state["images_folder_path"])
            page_size: Page size e.g. "8.625x8.75"
            page_count: Initial page count
            margin_percent: Margin percentage
            outline_height_percent: Outline height percentage
            blank_between: Add blank pages between images
            progress_callback: Optional callback for progress updates
            dry_run: If True, simulate without creating

        Returns:
            dict with design results
        """
        force_streamlit = _is_streamlit_context()

        return create_design_with_progress(
            folder_path=images_folder,
            page_size=page_size or DEFAULT_PAGE_SIZE,
            page_count=page_count,
            margin_percent=margin_percent if margin_percent is not None else DEFAULT_MARGIN_PERCENT,
            outline_height_percent=(
                outline_height_percent
                if outline_height_percent is not None
                else DEFAULT_OUTLINE_HEIGHT_PERCENT
            ),
            blank_between=blank_between if blank_between is not None else DEFAULT_BLANK_BETWEEN,
            progress_callback=progress_callback,
            force_streamlit_mode=force_streamlit,
            dry_run=dry_run,
            selected_images=selected_images,
        )
