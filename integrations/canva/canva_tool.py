"""
Canva Design Creator - LangChain Tool Interface.

This module provides a LangChain-compatible tool for creating Canva designs from images.
It can be used by LangChain agents for automated design creation.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

from .publisher import CanvaPublisher
from .models import CanvaDesignInput, CanvaDesignOutput
from .utils import _find_images, validate_folder
from . import config

logger = logging.getLogger(__name__)


def parse_page_size(page_size_str: Optional[str]) -> tuple[float, float]:
    """
    Parse page size string like "8.625x8.75" into tuple (width, height).
    
    Args:
        page_size_str: Page size in format "WIDTHxHEIGHT" (inches)
    
    Returns:
        Tuple of (width, height) as floats
    """
    if page_size_str is None:
        return (config.PAGE_WIDTH_IN, config.PAGE_HEIGHT_IN)
    
    try:
        width_str, height_str = page_size_str.lower().replace("in", "").split("x")
        return (float(width_str), float(height_str))
    except Exception as e:
        raise ValueError(f"Invalid page size format '{page_size_str}'. Use format like '8.625x8.75'") from e


def create_canva_design_core(
    folder_path: str,
    page_size: Optional[str] = None,
    page_count: Optional[int] = None,
    margin_percent: Optional[float] = None,
    outline_height_percent: Optional[float] = None,
    blank_between: Optional[bool] = None,
    dry_run: bool = False,
) -> CanvaDesignOutput:
    """
    Core function to create a Canva design from images in a folder.
    
    This function handles all the logic and returns structured output.
    It catches all exceptions and returns them as part of the output.
    
    Args:
        folder_path: Path to folder containing images (.png, .jpg, .jpeg, .webp)
        page_size: Page size in format "WIDTHxHEIGHT" (e.g., "8.625x8.75"). If None, uses config defaults.
        page_count: Initial number of pages (default: 1, pages are added dynamically)
        margin_percent: Margin percentage per side (default: 8.0)
        outline_height_percent: Height of top outline box as percentage of page height (default: 6.0)
        blank_between: Add blank pages between images (default: True)
        dry_run: If True, simulate the process without actually creating the design
    
    Returns:
        CanvaDesignOutput with results and any error messages
    """
    errors: list[str] = []
    
    # Validate folder exists
    try:
        folder = validate_folder(folder_path)
    except FileNotFoundError as e:
        return CanvaDesignOutput(
            success=False,
            design_url="",
            design_id="",
            total_images=0,
            successful=0,
            failed=0,
            total_pages=0,
            blank_pages_added=0,
            message=f"Folder not found: {folder_path}",
            errors=[str(e)],
            output_json_path="",
        )
    except NotADirectoryError as e:
        return CanvaDesignOutput(
            success=False,
            design_url="",
            design_id="",
            total_images=0,
            successful=0,
            failed=0,
            total_pages=0,
            blank_pages_added=0,
            message=f"Path is not a directory: {folder_path}",
            errors=[str(e)],
            output_json_path="",
        )
    
    # Check for images
    images = _find_images(folder)
    if not images:
        return CanvaDesignOutput(
            success=False,
            design_url="",
            design_id="",
            total_images=0,
            successful=0,
            failed=0,
            total_pages=0,
            blank_pages_added=0,
            message=f"No images found in {folder_path}",
            errors=[f"No images found in {folder_path}. Expected .png, .jpg, .jpeg, or .webp files."],
            output_json_path="",
        )
    
    # Parse page size
    try:
        page_size_tuple = parse_page_size(page_size)
    except ValueError as e:
        return CanvaDesignOutput(
            success=False,
            design_url="",
            design_id="",
            total_images=len(images),
            successful=0,
            failed=0,
            total_pages=0,
            blank_pages_added=0,
            message=f"Invalid page size: {page_size}",
            errors=[str(e)],
            output_json_path="",
        )
    
    # Use config defaults if not provided
    page_count = page_count if page_count is not None else config.PAGE_COUNT
    margin_percent = margin_percent if margin_percent is not None else config.MARGIN_PERCENT
    outline_height_percent = outline_height_percent if outline_height_percent is not None else config.OUTLINE_HEIGHT_PERCENT
    blank_between = blank_between if blank_between is not None else config.BLANK_BETWEEN
    
    try:
        # Get browser user data dir
        user_data_dir = config.get_browser_user_data_dir()
        user_data_dir_path = Path(user_data_dir) if user_data_dir else config.CHROME_USER_DATA_DIR
        
        publisher = CanvaPublisher(
            page_size=page_size_tuple,
            page_count=page_count,
            margin_percent=margin_percent,
            outline_height_percent=outline_height_percent,
            blank_between=blank_between,
            headless=config.HEADLESS,
            dry_run=dry_run,
            connect_existing=config.CONNECT_EXISTING,
            remote_debug_url=config.REMOTE_DEBUG_URL,
            chrome_user_data_dir=user_data_dir_path,
            chrome_profile=config.BROWSER_PROFILE,
            cloudflare_mode=config.CLOUDFLARE_MODE,
        )
        
        with publisher:
            # Run the publisher
            summary = publisher.run(folder)
        
        # Read the output JSON file to get full details
        output_json_path = folder / "canva_output.json"
        design_url = ""
        design_id = ""
        total_pages = page_count
        blank_pages_added = 0
        
        if output_json_path.exists():
            try:
                with open(output_json_path, 'r', encoding='utf-8') as f:
                    output_data = json.load(f)
                
                design_url = output_data.get("design", {}).get("url", "")
                design_id = output_data.get("design", {}).get("design_id", "")
                total_pages = output_data.get("design", {}).get("total_pages", page_count)
                blank_pages_added = output_data.get("summary", {}).get("blank_pages_added", 0)
                
                # Collect any errors from output
                if "errors" in output_data:
                    for error in output_data["errors"]:
                        if isinstance(error, dict):
                            errors.append(error.get("error", str(error)))
                        else:
                            errors.append(str(error))
            except Exception as e:
                logger.warning(f"Could not read output JSON: {e}")
        
        # Build success message
        total_images = summary.get("total", len(images))
        successful = summary.get("successful", 0)
        failed = summary.get("failed", 0)
        
        if dry_run:
            message = f"[DRY RUN] Would create design with {total_images} images"
        elif failed == 0 and successful > 0:
            message = f"Successfully created Canva design with {successful} images"
        elif failed > 0:
            message = f"Created design with {successful} images, {failed} failed"
        else:
            message = f"Design creation completed with {total_images} images"
        
        return CanvaDesignOutput(
            success=(failed == 0),
            design_url=design_url,
            design_id=design_id,
            total_images=total_images,
            successful=successful,
            failed=failed,
            total_pages=total_pages,
            blank_pages_added=blank_pages_added,
            message=message,
            errors=errors,
            output_json_path=str(output_json_path),
        )
        
    except Exception as e:
        error_msg = str(e)
        errors.append(error_msg)
        
        # Provide helpful error messages
        from .browser_setup import check_browser_running
        browser_name = config.BROWSER_TYPE.capitalize()
        if not check_browser_running():
            errors.append(f"Browser not running. Make sure {browser_name} is running with: --remote-debugging-port={config.DEBUG_PORT}")
        
        return CanvaDesignOutput(
            success=False,
            design_url="",
            design_id="",
            total_images=len(images),
            successful=0,
            failed=len(images),
            total_pages=0,
            blank_pages_added=0,
            message=f"Error: {error_msg}",
            errors=errors,
            output_json_path="",
        )


@tool
def create_canva_design(
    folder_path: str,
    page_size: Optional[str] = None,
    page_count: Optional[int] = None,
    margin_percent: Optional[float] = None,
    outline_height_percent: Optional[float] = None,
    blank_between: Optional[bool] = None,
    dry_run: bool = False,
) -> dict:
    """
    Create a Canva design from images in a folder.
    
    Each image in the folder will be uploaded and placed on a page in the design.
    Blank pages can be added between images if specified.
    
    IMPORTANT: Before calling this tool, the browser must be running with remote debugging:
    Start the browser with: --remote-debugging-port=9222
    And be logged into Canva.
    
    Args:
        folder_path: Path to folder containing images (.png, .jpg, .jpeg, .webp)
        page_size: Page size in format "WIDTHxHEIGHT" (e.g., "8.625x8.75"). If not provided, uses config defaults.
        page_count: Initial number of pages (default: 1, pages are added dynamically as images are placed)
        margin_percent: Margin percentage per side (default: 8.0)
        outline_height_percent: Height of top outline box as percentage of page height (default: 6.0)
        blank_between: Add blank pages between images (default: True)
        dry_run: If True, simulate the process without actually creating the design (default: False)
    
    Returns:
        Dictionary with: success, design_url, design_id, total_images, successful, failed, 
        total_pages, blank_pages_added, message, errors, output_json_path
    
    Example:
        create_canva_design(
            folder_path="C:/images/book1",
            page_size="8.625x8.75",
            blank_between=True
        )
    """
    result = create_canva_design_core(
        folder_path=folder_path,
        page_size=page_size,
        page_count=page_count,
        margin_percent=margin_percent,
        outline_height_percent=outline_height_percent,
        blank_between=blank_between,
        dry_run=dry_run,
    )
    return result.model_dump()


# ============================================================================
# Browser Setup Tools (for orchestrators)
# ============================================================================

@tool
def check_canva_browser_status(port: int = None) -> dict:
    """
    Check if the browser is running with remote debugging enabled.
    
    This tool should be called before attempting to create a Canva design
    to ensure the browser is properly set up.
    
    Args:
        port: Remote debugging port (defaults to 9222)
    
    Returns:
        Dictionary with: is_running (bool), port (int), browser_type (str), 
        startup_command (str) if not running
    """
    from .browser_setup import check_browser_running, get_browser_startup_command
    from . import config
    
    if port is None:
        port = config.DEBUG_PORT
    
    is_running = check_browser_running(port)
    
    result = {
        "is_running": is_running,
        "port": port,
        "browser_type": config.BROWSER_TYPE,
    }
    
    if not is_running:
        result["startup_command"] = get_browser_startup_command()
        result["message"] = f"Browser is not running. Start it with: {result['startup_command']}"
    else:
        result["message"] = f"Browser is running on port {port}"
    
    return result


@tool
def get_canva_browser_setup_command() -> dict:
    """
    Get the command needed to start the browser with remote debugging.
    
    Use this tool to get instructions for setting up the browser before
    running Canva automation.
    
    Returns:
        Dictionary with: browser_type (str), port (int), startup_command (str),
        instructions (str)
    """
    from .browser_setup import get_browser_startup_command
    from . import config
    
    command = get_browser_startup_command()
    browser_name = config.BROWSER_TYPE.capitalize()
    
    return {
        "browser_type": config.BROWSER_TYPE,
        "port": config.DEBUG_PORT,
        "startup_command": command,
        "instructions": (
            f"1. Close all {browser_name} windows\n"
            f"2. Run: {command}\n"
            f"3. Log into Canva in the browser window\n"
            f"4. Keep the browser window open"
        ),
    }


# ============================================================================
# Convenience functions for direct Python usage
# ============================================================================

def get_canva_tool():
    """Get the main Canva design creation tool for use with LangChain agents."""
    return create_canva_design


def get_all_tools() -> list:
    """
    Get all Canva-related tools as a list.
    
    Returns:
        List of all available tools:
        - create_canva_design: Main tool to create designs
        - check_canva_browser_status: Check if browser is running
        - get_canva_browser_setup_command: Get browser setup instructions
    """
    return [
        create_canva_design,
        check_canva_browser_status,
        get_canva_browser_setup_command,
    ]

