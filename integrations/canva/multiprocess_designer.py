"""
Multiprocessing wrapper for Canva Designer.

This module runs the Canva design creator in a separate process to completely
isolate it from Streamlit's event loop restrictions.
"""

import multiprocessing
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _put_error_result(result_queue: multiprocessing.Queue, message: str, errors: list) -> None:
    """Put error result in queue. Swallow any exception to avoid masking the original error."""
    try:
        result_queue.put({
            "success": False,
            "design_url": "",
            "design_id": "",
            "total_images": 0,
            "successful": 0,
            "failed": 0,
            "total_pages": 0,
            "blank_pages_added": 0,
            "message": message,
            "errors": errors,
            "output_json_path": "",
        })
    except Exception:
        pass


def run_designer_in_process(
    folder_path: str,
    page_size: Optional[str],
    page_count: Optional[int],
    margin_percent: Optional[float],
    outline_height_percent: Optional[float],
    blank_between: Optional[bool],
    progress_queue: multiprocessing.Queue,
    result_queue: multiprocessing.Queue,
    dry_run: bool = False,
) -> None:
    """
    Run Canva design creator in separate process - isolated from Streamlit.

    This function runs in a completely separate process with its own event loop,
    just like the original CLI. This avoids Streamlit's event loop restrictions.

    Args:
        folder_path: Path to folder containing images
        page_size: Page size e.g. "8.625x8.75"
        page_count: Initial page count
        margin_percent: Margin percentage
        outline_height_percent: Outline height percentage
        blank_between: Add blank pages between images
        progress_queue: Queue to send progress updates to main process
        result_queue: Queue to send final result to main process
        dry_run: If True, simulate without actually creating
    """
    import traceback
    import sys

    # Ensure project root is in path (Windows spawn can lose it)
    try:
        _this_dir = Path(__file__).resolve().parent
        _project_root = _this_dir.parent.parent
        if str(_project_root) not in sys.path:
            sys.path.insert(0, str(_project_root))
    except Exception:
        pass

    try:
        logger.info(f"Process {multiprocessing.current_process().pid}: Starting Canva designer")

        progress_queue.put({
            "step": "connecting",
            "current": 0,
            "total": 0,
            "status": "in_progress",
            "message": "Connecting to browser in isolated process..."
        })

        from .canva_tool import create_canva_design_core

        progress_queue.put({
            "step": "creating",
            "current": 0,
            "total": 0,
            "status": "in_progress",
            "message": "Creating Canva design..."
        })

        def _progress_callback(update: dict) -> None:
            try:
                progress_queue.put(update)
            except Exception:
                pass

        result = create_canva_design_core(
            folder_path=folder_path,
            page_size=page_size,
            page_count=page_count,
            margin_percent=margin_percent,
            outline_height_percent=outline_height_percent,
            blank_between=blank_between,
            dry_run=dry_run,
            progress_callback=_progress_callback,
        )

        result_dict = result.model_dump() if hasattr(result, "model_dump") else dict(result)

        progress_queue.put({
            "step": "completed",
            "current": result_dict.get("successful", 0),
            "total": result_dict.get("total_images", 0),
            "status": "completed" if result_dict.get("success") else "failed",
            "message": result_dict.get("message", "Design creation completed")
        })

        result_queue.put(result_dict)

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Process error: {e}\n{error_trace}")
        _put_error_result(result_queue, f"Error in Canva designer process: {str(e)}", [str(e), error_trace])
