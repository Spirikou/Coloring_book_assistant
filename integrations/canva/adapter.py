"""Adapter for Canva agent functionality with progress tracking."""

import shutil
import tempfile
from pathlib import Path
from typing import Dict, Callable, Optional, List
import logging
import multiprocessing
import time

from . import config
from .utils import _find_images

logger = logging.getLogger(__name__)


def _is_in_streamlit_context() -> bool:
    """Check if we're running in Streamlit context."""
    try:
        import streamlit as st
        if hasattr(st.runtime, 'scriptrunner'):
            if st.runtime.scriptrunner.is_streamlit_script_run_context():
                return True
    except Exception:
        pass

    try:
        import os
        if os.environ.get('STREAMLIT_SERVER_PORT') or os.environ.get('STREAMLIT_SERVER_ADDRESS'):
            return True
    except Exception:
        pass

    return False


def _create_design_via_multiprocessing(
    folder_path: str,
    page_size: Optional[str],
    page_count: Optional[int],
    margin_percent: Optional[float],
    outline_height_percent: Optional[float],
    blank_between: Optional[bool],
    progress_callback: Optional[Callable] = None,
    dry_run: bool = False,
    selected_images: Optional[List[str]] = None,
) -> Dict:
    """
    Create Canva design using multiprocessing to isolate from Streamlit's event loop.
    """
    logger.info("Using multiprocessing to isolate Canva designer from Streamlit")

    effective_folder = folder_path
    temp_dir = None
    if selected_images and len(selected_images) > 0:
        temp_dir = tempfile.mkdtemp(prefix="canva_selected_")
        for src in selected_images:
            p = Path(src)
            if p.exists() and p.is_file():
                shutil.copy2(src, Path(temp_dir) / p.name)
        effective_folder = temp_dir

    try:
        progress_queue = multiprocessing.Queue()
        result_queue = multiprocessing.Queue()

        from .multiprocess_designer import run_designer_in_process

        process = multiprocessing.Process(
            target=run_designer_in_process,
            args=(
                effective_folder,
                page_size,
                page_count,
                margin_percent,
                outline_height_percent,
                blank_between,
                progress_queue,
                result_queue,
                dry_run,
            ),
            daemon=False,
        )

        process.start()
        logger.info(f"Started Canva designer process (PID: {process.pid})")

        # Compute timeout: base + per_image * count, capped at max
        image_count = len(_find_images(Path(effective_folder)))
        process_timeout = min(
            config.CANVA_PROCESS_TIMEOUT_MAX,
            config.CANVA_PROCESS_TIMEOUT_BASE
            + config.CANVA_PROCESS_TIMEOUT_PER_IMAGE * max(1, image_count),
        )
        logger.info(f"Process timeout: {process_timeout}s (base + {image_count} images)")

        result = None
        start_time = time.time()
        deadline = start_time + process_timeout

        while process.is_alive():
            try:
                progress_update = progress_queue.get(timeout=0.1)
                if progress_callback:
                    progress_callback(progress_update)
                # Extend deadline when we receive per-image progress (work is ongoing)
                if progress_update.get("step") == "uploading_image":
                    remaining = progress_update.get("total", image_count) - progress_update.get(
                        "current", 0
                    )
                    if remaining > 0:
                        # Give enough time for remaining images plus buffer
                        extension = (
                            config.CANVA_PROCESS_TIMEOUT_PER_IMAGE * remaining + 60
                        )
                        new_deadline = time.time() + extension
                        if new_deadline > deadline:
                            deadline = min(new_deadline, start_time + config.CANVA_PROCESS_TIMEOUT_MAX)
                            logger.debug(f"Extended deadline: {int(deadline - time.time())}s remaining")
            except Exception:
                pass

            if time.time() > deadline:
                logger.error("Canva designer process timeout")
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()
                raise TimeoutError(
                    f"Canva designer exceeded {int(deadline - start_time)} second timeout"
                )

            time.sleep(0.05)

        try:
            result = result_queue.get(timeout=5)
        except Exception:
            exit_code = process.exitcode if process else None
            exit_hint = f" (exit code: {exit_code})" if exit_code is not None else ""
            result = {
                "success": False,
                "design_url": "",
                "design_id": "",
                "total_images": 0,
                "successful": 0,
                "failed": 0,
                "total_pages": 0,
                "blank_pages_added": 0,
                "message": f"Failed to get result from Canva designer process{exit_hint}",
                "errors": [
                    "Process completed but no result available. "
                    "The child process may have crashed during import or startup. "
                    "Check that all dependencies (playwright, pydantic, langchain-core) are installed."
                ],
                "output_json_path": "",
            }

        process.join(timeout=5)

    except Exception as e:
        logger.error(f"Error in multiprocessing Canva designer: {e}")
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()

        result = {
            "success": False,
            "design_url": "",
            "design_id": "",
            "total_images": 0,
            "successful": 0,
            "failed": 0,
            "total_pages": 0,
            "blank_pages_added": 0,
            "message": f"Error: {str(e)}",
            "errors": [str(e)],
            "output_json_path": "",
        }

    finally:
        if temp_dir and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.debug(f"Could not clean temp dir: {e}")

    return result


def create_design_with_progress(
    folder_path: str,
    page_size: Optional[str] = None,
    page_count: Optional[int] = None,
    margin_percent: Optional[float] = None,
    outline_height_percent: Optional[float] = None,
    blank_between: Optional[bool] = None,
    progress_callback: Optional[Callable] = None,
    force_streamlit_mode: bool = False,
    dry_run: bool = False,
    selected_images: Optional[List[str]] = None,
) -> Dict:
    """
    Create Canva design with progress tracking.

    Args:
        folder_path: Path to folder containing images (same as Pinterest - images_folder_path)
        page_size: Page size e.g. "8.625x8.75"
        page_count: Initial page count
        margin_percent: Margin percentage
        outline_height_percent: Outline height percentage
        blank_between: Add blank pages between images
        progress_callback: Optional callback for progress updates
        force_streamlit_mode: If True, force multiprocessing (for Streamlit)
        dry_run: If True, simulate without creating

    Returns:
        dict with design results (success, design_url, design_id, etc.)
    """
    use_multiprocessing = force_streamlit_mode or _is_in_streamlit_context()

    if use_multiprocessing:
        return _create_design_via_multiprocessing(
            folder_path=folder_path,
            page_size=page_size,
            page_count=page_count,
            margin_percent=margin_percent,
            outline_height_percent=outline_height_percent,
            blank_between=blank_between,
            progress_callback=progress_callback,
            dry_run=dry_run,
            selected_images=selected_images,
        )

    # Direct call for non-Streamlit contexts
    temp_dir = None
    try:
        effective_folder = folder_path
        if selected_images and len(selected_images) > 0:
            temp_dir = tempfile.mkdtemp(prefix="canva_selected_")
            for src in selected_images:
                p = Path(src)
                if p.exists() and p.is_file():
                    shutil.copy2(src, Path(temp_dir) / p.name)
            effective_folder = temp_dir

        if progress_callback:
            progress_callback({
                "step": "preparing",
                "current": 0,
                "total": 0,
                "status": "in_progress",
                "message": "Preparing to create Canva design..."
            })

        from .canva_tool import create_canva_design_core

        result = create_canva_design_core(
            folder_path=effective_folder,
            page_size=page_size,
            page_count=page_count,
            margin_percent=margin_percent,
            outline_height_percent=outline_height_percent,
            blank_between=blank_between,
            dry_run=dry_run,
        )

        result_dict = result.model_dump() if hasattr(result, "model_dump") else dict(result)

        if progress_callback:
            progress_callback({
                "step": "completed",
                "current": result_dict.get("successful", 0),
                "total": result_dict.get("total_images", 0),
                "status": "completed" if result_dict.get("success") else "failed",
                "message": result_dict.get("message", "Design creation completed")
            })

        return result_dict

    except Exception as e:
        logger.error(f"Error creating Canva design: {e}")
        return {
            "success": False,
            "design_url": "",
            "design_id": "",
            "total_images": 0,
            "successful": 0,
            "failed": 0,
            "total_pages": 0,
            "blank_pages_added": 0,
            "message": f"Error: {str(e)}",
            "errors": [str(e)],
            "output_json_path": "",
        }
    finally:
        if temp_dir and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
            except Exception as ex:
                logger.debug(f"Could not clean temp dir: {ex}")
