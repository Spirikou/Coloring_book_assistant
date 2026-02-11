"""
Multiprocessing wrapper for Pinterest Publisher.

This module runs the Pinterest publisher in a separate process to completely
isolate it from Streamlit's event loop restrictions.
"""

import multiprocessing
import logging
import traceback
from typing import Dict, Optional
from pathlib import Path

# Import workflow logger
try:
    from .workflow_logger import get_workflow_logger
    workflow_logger = get_workflow_logger()
except Exception as e:
    workflow_logger = None
    print(f"Warning: Could not initialize workflow logger in multiprocess_publisher: {e}")

logger = logging.getLogger(__name__)


# Windows multiprocessing requires functions to be importable
# This function will be called in a separate process
def run_publisher_in_process(
    folder_path: str,
    board_name: str,
    progress_queue: multiprocessing.Queue,
    result_queue: multiprocessing.Queue,
    dry_run: bool = False
) -> None:
    """
    Run publisher in separate process - isolated from Streamlit.
    
    This function runs in a completely separate process with its own event loop,
    just like the original CLI. This avoids Streamlit's event loop restrictions.
    
    Args:
        folder_path: Path to folder containing images and JSON config
        board_name: Name of Pinterest board
        progress_queue: Queue to send progress updates to main process
        result_queue: Queue to send final result to main process
        dry_run: If True, simulate without actually publishing
    """
    try:
        if workflow_logger:
            workflow_logger.log(f"Process: Starting publisher in isolated process (PID: {multiprocessing.current_process().pid})", "INFO")
        logger.info(f"Process {multiprocessing.current_process().pid}: Starting publisher")
        
        # Import here to avoid issues with multiprocessing on Windows
        from .pinterest_publisher_ocr import PinterestPublisher
        
        # Send initial progress
        progress_queue.put({
            "step": "connecting",
            "current": 0,
            "total": 0,
            "status": "in_progress",
            "message": "Connecting to browser in isolated process..."
        })
        
        # Run publisher - this will work because we're in a separate process
        # with a normal event loop, just like the original CLI
        with PinterestPublisher(
            folder_path=folder_path,
            board_name=board_name,
            dry_run=dry_run,
            connect_existing=True,  # Always use existing browser
            force_streamlit_mode=False,  # Not in Streamlit in this process!
        ) as publisher:
            
            if workflow_logger:
                workflow_logger.log("Process: Publisher initialized, getting images...", "INFO")
            logger.info("Process: Publisher initialized, getting images...")
            
            # Get images
            all_images = publisher.get_images()
            total = len(all_images)
            
            unpublished = [
                img for img in all_images 
                if not publisher.state_manager.is_published(img.filename)
            ]
            already_published = total - len(unpublished)
            
            progress_queue.put({
                "step": "publishing",
                "current": 0,
                "total": len(unpublished),
                "status": "in_progress",
                "message": f"Publishing {len(unpublished)} images ({already_published} already published)..."
            })
            
            if workflow_logger:
                workflow_logger.log(f"Process: Found {total} images, {len(unpublished)} to publish", "INFO")
            logger.info(f"Process: Found {total} images, {len(unpublished)} to publish")
            
            if not unpublished:
                result = {
                    "success": True,
                    "total_images": total,
                    "already_published": already_published,
                    "published": 0,
                    "failed": 0,
                    "message": "All images already published",
                    "errors": []
                }
                result_queue.put(result)
                return
            
            # Publish each image with progress updates
            successful = 0
            failed = 0
            errors = []
            
            for i, image_info in enumerate(unpublished, 1):
                try:
                    if workflow_logger:
                        workflow_logger.log(f"Process: Publishing image {i}/{len(unpublished)}: {image_info.filename}", "INFO")
                    logger.info(f"Process: Publishing {i}/{len(unpublished)}: {image_info.filename}")
                    
                    success = publisher._publish_single_pin(image_info)
                    
                    if success:
                        successful += 1
                    else:
                        failed += 1
                        errors.append(f"Failed to publish {image_info.filename}")
                    
                    # Send progress update
                    progress_queue.put({
                        "step": "publishing",
                        "current": i,
                        "total": len(unpublished),
                        "status": "in_progress",
                        "message": f"Published {i}/{len(unpublished)} images..."
                    })
                    
                except Exception as e:
                    failed += 1
                    error_msg = f"Error publishing {image_info.filename}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    if workflow_logger:
                        workflow_logger.log_error(e, f"publish_image_{image_info.filename}")
            
            # Final result
            result = {
                "success": failed == 0,
                "total_images": total,
                "already_published": already_published,
                "published": successful,
                "failed": failed,
                "message": f"Published {successful} pins, {failed} failed" if failed > 0 else f"Successfully published {successful} pins",
                "errors": errors
            }
            
            if workflow_logger:
                workflow_logger.log(f"Process: Publishing complete. Success: {successful}, Failed: {failed}", "INFO")
            logger.info(f"Process: Publishing complete. Success: {successful}, Failed: {failed}")
            
            result_queue.put(result)
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Process error: {e}\n{error_trace}")
        if workflow_logger:
            workflow_logger.log_error(e, "run_publisher_in_process")
        
        error_result = {
            "success": False,
            "total_images": 0,
            "already_published": 0,
            "published": 0,
            "failed": 0,
            "message": f"Error in publisher process: {str(e)}",
            "errors": [str(e)]
        }
        result_queue.put(error_result)

