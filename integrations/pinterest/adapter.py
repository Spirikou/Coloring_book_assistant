"""Adapter for Pinterest_agent functionality with progress tracking."""

from typing import Dict, Callable, Optional
import logging
import traceback
import multiprocessing
import time

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


def _is_in_streamlit_context() -> bool:
    """Check if we're running in Streamlit context."""
    try:
        import streamlit as st
        if hasattr(st.runtime, 'scriptrunner'):
            if st.runtime.scriptrunner.is_streamlit_script_run_context():
                return True
    except:
        pass
    
    try:
        import os
        if os.environ.get('STREAMLIT_SERVER_PORT') or os.environ.get('STREAMLIT_SERVER_ADDRESS'):
            return True
    except:
        pass
    
    return False


def _publish_via_multiprocessing(
    folder_path: str,
    board_name: str,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Publish pins using multiprocessing to isolate from Streamlit's event loop.
    
    Args:
        folder_path: Path to folder containing images and JSON config
        board_name: Name of Pinterest board
        progress_callback: Optional callback for progress updates
    
    Returns:
        dict with publishing results
    """
    if workflow_logger:
        workflow_logger.log("Using multiprocessing to isolate publisher from Streamlit", "INFO")
    logger.info("Using multiprocessing to isolate publisher from Streamlit")
    
    # Create queues for communication
    progress_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    
    # Import here to avoid issues with multiprocessing on Windows
    from .multiprocess_publisher import run_publisher_in_process
    
    # Create and start process
    process = multiprocessing.Process(
        target=run_publisher_in_process,
        args=(folder_path, board_name, progress_queue, result_queue, False),
        daemon=False
    )
    
    process.start()
    
    if workflow_logger:
        workflow_logger.log(f"Started publisher process (PID: {process.pid})", "INFO")
    logger.info(f"Started publisher process (PID: {process.pid})")
    
    # Poll for progress updates and results
    result = None
    process_timeout = 600  # 10 minutes max
    start_time = time.time()
    
    try:
        while process.is_alive():
            # Check for progress updates
            try:
                progress_update = progress_queue.get(timeout=0.1)
                if progress_callback:
                    progress_callback(progress_update)
                if workflow_logger:
                    workflow_logger.log_action("progress_update_from_process", progress_update)
            except:
                pass  # No progress update available
            
            # Check timeout
            if time.time() - start_time > process_timeout:
                logger.error("Publisher process timeout")
                if workflow_logger:
                    workflow_logger.log("Publisher process timeout", "ERROR")
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()
                raise TimeoutError(f"Publisher process exceeded {process_timeout} second timeout")
            
            # Small sleep to avoid busy waiting
            time.sleep(0.05)
        
        # Process finished, get final result
        try:
            result = result_queue.get(timeout=5)
        except:
            result = {
                "success": False,
                "total_images": 0,
                "already_published": 0,
                "published": 0,
                "failed": 0,
                "message": "Failed to get result from publisher process",
                "errors": ["Process completed but no result available"]
            }
        
        # Clean up
        process.join(timeout=5)
        
    except Exception as e:
        logger.error(f"Error in multiprocessing publisher: {e}")
        if workflow_logger:
            workflow_logger.log_error(e, "multiprocessing_publisher")
        
        # Try to clean up process
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
        
        result = {
            "success": False,
            "total_images": 0,
            "already_published": 0,
            "published": 0,
            "failed": 0,
            "message": f"Error in multiprocessing publisher: {str(e)}",
            "errors": [str(e)]
        }
    
    if workflow_logger:
        workflow_logger.log(f"Multiprocessing publisher completed. Success: {result.get('success', False)}", "INFO")
    logger.info(f"Multiprocessing publisher completed. Success: {result.get('success', False)}")
    
    return result


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
        force_streamlit_mode: If True, force use of multiprocessing (for Streamlit)
    
    Returns:
        dict with publishing results
    """
    if workflow_logger:
        workflow_logger.log_function_call("publish_pins_with_progress", {
            "folder_path": folder_path,
            "board_name": board_name,
            "has_callback": progress_callback is not None,
            "force_streamlit_mode": force_streamlit_mode
        })
    
    # Check if we should use multiprocessing (Streamlit context)
    use_multiprocessing = force_streamlit_mode or _is_in_streamlit_context()
    
    if use_multiprocessing:
        if workflow_logger:
            workflow_logger.log("Using multiprocessing for Streamlit isolation", "INFO")
        logger.info("Using multiprocessing to isolate from Streamlit's event loop")
        return _publish_via_multiprocessing(folder_path, board_name, progress_callback)
    
    # Direct call for non-Streamlit contexts (CLI, testing, etc.)
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
        
        # Call Pinterest_agent's core function directly
        result = publish_pinterest_pins_core(
            folder_path=folder_path,
            board_name=board_name,
            dry_run=False,
            force_streamlit_mode=False,  # Not in Streamlit, use direct call
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

