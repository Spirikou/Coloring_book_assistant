"""Adapter for Pinterest_agent functionality with progress tracking."""

from typing import Dict, Callable, Optional
import logging
import traceback

# Import workflow logger
try:
    from .workflow_logger import get_workflow_logger
    workflow_logger = get_workflow_logger()
    workflow_logger.log("adapter.py: Module loaded", "INFO")
    workflow_logger.log_action("import_adapter", {"module": "integrations.pinterest.adapter"})
except Exception as e:
    workflow_logger = None
    print(f"Warning: Could not initialize workflow logger: {e}")

from .pinterest_tool import publish_pinterest_pins_core, PinterestPublishOutput
from .browser_utils import check_browser_connection

logger = logging.getLogger(__name__)

# Log import attempts
if workflow_logger:
    try:
        workflow_logger.log_import("integrations.pinterest.pinterest_tool", True)
    except Exception as e:
        workflow_logger.log_import("integrations.pinterest.pinterest_tool", False, e)


def publish_pins_with_progress(
    folder_path: str,
    board_name: str,
    progress_callback: Optional[Callable] = None,
    force_streamlit_mode: bool = False,
) -> Dict:
    """
    Publish pins with progress tracking.
    
    Args:
        folder_path: Path to folder containing images and JSON config
        board_name: Name of Pinterest board
        progress_callback: Optional callback function for progress updates
                         Called with: {"step": str, "current": int, "total": int, "status": str, "message": str}
    
    Returns:
        dict with publishing results
    """
    if workflow_logger:
        workflow_logger.log_function_call("publish_pins_with_progress", {
            "folder_path": folder_path,
            "board_name": board_name,
            "has_callback": progress_callback is not None
        })
    
    try:
        # Initial progress update
        if progress_callback:
            progress_callback({
                "step": "preparing",
                "current": 0,
                "total": 0,
                "status": "in_progress",
                "message": "Preparing to publish pins..."
            })
        
        if workflow_logger:
            workflow_logger.log_action("calling_publish_core", {
                "folder_path": folder_path,
                "board_name": board_name
            })
        
        # Call Pinterest_agent's core function
        result = publish_pinterest_pins_core(
            folder_path=folder_path,
            board_name=board_name,
            dry_run=False,
            force_streamlit_mode=force_streamlit_mode,
        )
        
        if workflow_logger:
            workflow_logger.log_action("publish_core_completed", {
                "success": result.success if hasattr(result, 'success') else result.get('success', False),
                "result_type": type(result).__name__
            })
        
        # Convert Pydantic model to dict
        if isinstance(result, PinterestPublishOutput):
            result_dict = result.model_dump()
        else:
            result_dict = result
        
        # Final progress update
        if progress_callback:
            if result_dict.get("success", False):
                progress_callback({
                    "step": "completed",
                    "current": result_dict.get("published", 0),
                    "total": result_dict.get("total_images", 0),
                    "status": "completed",
                    "message": result_dict.get("message", "Publishing completed")
                })
            else:
                progress_callback({
                    "step": "failed",
                    "current": 0,
                    "total": result_dict.get("total_images", 0),
                    "status": "failed",
                    "message": result_dict.get("message", "Publishing failed")
                })
        
        return result_dict
        
    except Exception as e:
        logger.error(f"Error publishing pins: {e}")
        if workflow_logger:
            workflow_logger.log_error(e, "publish_pins_with_progress")
        
        error_result = {
            "success": False,
            "total_images": 0,
            "already_published": 0,
            "published": 0,
            "failed": 0,
            "message": f"Error: {str(e)}",
            "errors": [str(e)]
        }
        
        if progress_callback:
            progress_callback({
                "step": "failed",
                "current": 0,
                "total": 0,
                "status": "failed",
                "message": f"Error: {str(e)}"
            })
        
        return error_result

