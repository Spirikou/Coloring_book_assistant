"""
Pinterest Publisher - LangChain Tool Interface.

This module provides a LangChain-compatible tool for publishing pins to Pinterest.
It can be used by LangChain agents for automated social media publishing.
"""

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# Import workflow logger
try:
    from .workflow_logger import get_workflow_logger
    workflow_logger = get_workflow_logger()
    workflow_logger.log("pinterest_tool.py: Module loaded", "INFO")
except Exception as e:
    workflow_logger = None
    print(f"Warning: Could not initialize workflow logger in pinterest_tool: {e}")

# Log import attempts
if workflow_logger:
    try:
        workflow_logger.log_import("integrations.pinterest.pinterest_publisher_ocr", True)
    except Exception as e:
        workflow_logger.log_import("integrations.pinterest.pinterest_publisher_ocr", False, e)

from .pinterest_publisher_ocr import PinterestPublisher, find_json_file
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Schemas for structured input/output
# ============================================================================

class PinterestPublishInput(BaseModel):
    """Input schema for Pinterest pin publishing."""
    folder_path: str = Field(
        description="Path to folder containing images (.png, .jpg, .webp) and a JSON config file with title, description, and seo_keywords"
    )
    board_name: str = Field(
        description="Name of the Pinterest board to publish pins to (must match exactly)"
    )
    dry_run: bool = Field(
        default=False,
        description="If True, simulate the process without actually publishing"
    )


class PinterestPublishOutput(BaseModel):
    """Output schema for Pinterest pin publishing results."""
    success: bool = Field(description="Whether the operation completed successfully")
    total_images: int = Field(description="Total number of images found in folder")
    already_published: int = Field(description="Number of images already published (skipped)")
    published: int = Field(description="Number of images successfully published this run")
    failed: int = Field(description="Number of images that failed to publish")
    message: str = Field(description="Human-readable summary message")
    errors: list[str] = Field(default_factory=list, description="List of error messages if any")


# ============================================================================
# Core publishing function (can be called directly or via tool)
# ============================================================================

def publish_pinterest_pins_core(
    folder_path: str,
    board_name: str,
    dry_run: bool = False,
    force_streamlit_mode: bool = False,
) -> PinterestPublishOutput:
    """
    Core function to publish images from a folder to Pinterest as pins.
    
    This function handles all the logic and returns structured output.
    It catches all exceptions and returns them as part of the output.
    
    Args:
        folder_path: Path to folder containing images and a JSON config file
        board_name: Name of the Pinterest board to publish to
        dry_run: If True, simulate without actually publishing
    
    Returns:
        PinterestPublishOutput with results and any error messages
    """
    if workflow_logger:
        workflow_logger.log_function_call("publish_pinterest_pins_core", {
            "folder_path": folder_path,
            "board_name": board_name,
            "dry_run": dry_run
        })
    
    errors: list[str] = []
    
    # Validate folder exists
    folder = Path(folder_path)
    if not folder.exists():
        return PinterestPublishOutput(
            success=False,
            total_images=0,
            already_published=0,
            published=0,
            failed=0,
            message=f"Folder not found: {folder_path}",
            errors=[f"Folder not found: {folder_path}"]
        )
    
    if not folder.is_dir():
        return PinterestPublishOutput(
            success=False,
            total_images=0,
            already_published=0,
            published=0,
            failed=0,
            message=f"Path is not a directory: {folder_path}",
            errors=[f"Path is not a directory: {folder_path}"]
        )
    
    # Check for JSON config
    json_file = find_json_file(folder)
    if not json_file:
        return PinterestPublishOutput(
            success=False,
            total_images=0,
            already_published=0,
            published=0,
            failed=0,
            message=f"No JSON config file found in {folder_path}",
            errors=[f"No JSON config file found in {folder_path}. Expected a .json file with title, description, and seo_keywords."]
        )
    
    try:
        if workflow_logger:
            workflow_logger.log_action("creating_pinterest_publisher", {
                "folder_path": folder_path,
                "board_name": board_name,
                "dry_run": dry_run
            })
        
        with PinterestPublisher(
            folder_path=folder_path,
            board_name=board_name,
            dry_run=dry_run,
            connect_existing=True,  # Always use existing Chrome
            force_streamlit_mode=force_streamlit_mode,
        ) as publisher:
            
            if workflow_logger:
                workflow_logger.log_action("pinterest_publisher_created", {"success": True})
            # Get counts before publishing
            all_images = publisher.get_images()
            total_images = len(all_images)
            
            unpublished_before = [
                img for img in all_images 
                if not publisher.state_manager.is_published(img.filename)
            ]
            already_published = total_images - len(unpublished_before)
            
            # Publish
            results = publisher.publish_all()
            
            # Build output
            published = results.get("successful", 0)
            failed = results.get("failed", 0)
            
            if dry_run:
                message = f"[DRY RUN] Would publish {len(unpublished_before)} pins to '{board_name}'"
            elif failed == 0 and published > 0:
                message = f"Successfully published {published} pins to '{board_name}'"
            elif failed > 0:
                message = f"Published {published} pins, {failed} failed"
                errors.append(f"{failed} pins failed to publish")
            else:
                message = f"No new pins to publish. {already_published} already published."
            
            return PinterestPublishOutput(
                success=(failed == 0),
                total_images=total_images,
                already_published=already_published,
                published=published,
                failed=failed,
                message=message,
                errors=errors
            )
            
    except Exception as e:
        error_msg = str(e)
        
        if workflow_logger:
            workflow_logger.log_error(e, "publish_pinterest_pins_core")
        
        # Provide helpful error messages
        try:
            from .config import BROWSER_TYPE, DEBUG_PORT
        except ImportError:
            # Fallback for absolute import
            from integrations.pinterest.config import BROWSER_TYPE, DEBUG_PORT
        browser_name = BROWSER_TYPE.capitalize()
        if "connect" in error_msg.lower() or str(DEBUG_PORT) in error_msg:
            errors.append(f"Could not connect to {browser_name}. Make sure {browser_name} is running with: --remote-debugging-port={DEBUG_PORT}")
        else:
            errors.append(error_msg)
        
        return PinterestPublishOutput(
            success=False,
            total_images=0,
            already_published=0,
            published=0,
            failed=0,
            message=f"Error: {error_msg}",
            errors=errors
        )


# ============================================================================
# LangChain Tool
# ============================================================================

@tool
def publish_pinterest_pins(
    folder_path: str,
    board_name: str,
    dry_run: bool = False,
) -> dict:
    """
    Publish images from a folder to Pinterest as pins.
    
    Each image in the folder will be published as a separate pin to the specified board.
    The folder must contain a JSON config file with: title, description, and seo_keywords.
    Pin titles are automatically generated using GPT-4o-mini based on image filenames.
    
    IMPORTANT: Before calling this tool, Chrome must be running with remote debugging:
    Start Chrome with: --remote-debugging-port=9222
    And be logged into Pinterest.
    
    Args:
        folder_path: Path to folder containing images (.png, .jpg, .webp) and a JSON config file
        board_name: Name of the Pinterest board to publish to (must match exactly)
        dry_run: If True, simulate the process without actually publishing (default: False)
    
    Returns:
        Dictionary with: success, total_images, published, failed, message, errors
    
    Example:
        publish_pinterest_pins(
            folder_path="C:/coloring_books/book1",
            board_name="Coloring Books",
            dry_run=False
        )
    """
    result = publish_pinterest_pins_core(folder_path, board_name, dry_run)
    return result.model_dump()


# ============================================================================
# Convenience functions for direct Python usage
# ============================================================================

def get_pinterest_tool():
    """Get the Pinterest publishing tool for use with LangChain agents."""
    return publish_pinterest_pins


def get_all_tools() -> list:
    """Get all Pinterest-related tools as a list."""
    return [publish_pinterest_pins]

