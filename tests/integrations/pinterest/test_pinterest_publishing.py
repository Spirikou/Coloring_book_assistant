"""
Functional test script for Pinterest publishing workflow.
Tests the full publishing chain with minimal setup.
"""

import sys
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.integrations.pinterest.test_logger import TestLogger


def create_test_folder(logger: TestLogger) -> Path:
    """Create a test folder with sample JSON and images."""
    test_dir = project_root / "tests" / "integrations" / "pinterest" / "test_data"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped test folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_folder = test_dir / f"test_publish_{timestamp}"
    test_folder.mkdir(parents=True, exist_ok=True)
    
    logger.log_action("create_test_folder", f"Created test folder: {test_folder}", "success")
    
    # Create sample JSON config
    json_config = {
        "title": "Test Coloring Book",
        "description": "A test coloring book for debugging Pinterest publishing",
        "seo_keywords": ["coloring book", "test", "debug"]
    }
    
    json_file = test_folder / "book_config.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_config, f, indent=2, ensure_ascii=False)
    
    logger.log_action("create_json_config", f"Created JSON config: {json_file}", "success")
    
    # Create a dummy image file (or copy from existing if available)
    # For testing, we'll create a simple placeholder
    image_file = test_folder / "test_image.png"
    # Create a minimal valid PNG (1x1 pixel transparent PNG)
    minimal_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
    with open(image_file, "wb") as f:
        f.write(minimal_png)
    
    logger.log_action("create_test_image", f"Created test image: {image_file}", "success")
    
    return test_folder


def test_import_chain(logger: TestLogger):
    """Test the full import chain from adapter to pinterest_tool."""
    logger.log_action("test_import_chain", "Testing full import chain", "info")
    
    # Test importing adapter
    try:
        from integrations.pinterest.adapter import publish_pins_with_progress
        logger.log_action("import_adapter", "Successfully imported adapter", "success")
    except Exception as e:
        logger.log_error(e, "Failed to import adapter")
        return False
    
    # Test importing pinterest_tool
    try:
        from integrations.pinterest.pinterest_tool import publish_pinterest_pins_core
        logger.log_action("import_pinterest_tool", "Successfully imported pinterest_tool", "success")
    except Exception as e:
        logger.log_error(e, "Failed to import pinterest_tool")
        return False
    
    # Test importing pinterest_publisher_ocr
    try:
        from integrations.pinterest.pinterest_publisher_ocr import PinterestPublisher, find_json_file
        logger.log_action("import_publisher", "Successfully imported PinterestPublisher", "success")
    except Exception as e:
        logger.log_error(e, "Failed to import PinterestPublisher")
        return False
    
    # Test importing models
    try:
        from integrations.pinterest.models import BookConfig, ImageInfo
        logger.log_action("import_models", "Successfully imported models", "success")
    except Exception as e:
        logger.log_error(e, "Failed to import models")
        return False
    
    # Test importing content_generator
    try:
        from integrations.pinterest.content_generator import generate_pin_content
        logger.log_action("import_content_generator", "Successfully imported content_generator", "success")
    except Exception as e:
        logger.log_error(e, "Failed to import content_generator")
        return False
    
    # Test importing state_manager
    try:
        from integrations.pinterest.state_manager import StateManager
        logger.log_action("import_state_manager", "Successfully imported StateManager", "success")
    except Exception as e:
        logger.log_error(e, "Failed to import StateManager")
        return False
    
    return True


def test_pinterest_publisher_initialization(logger: TestLogger, test_folder: Path):
    """Test initializing PinterestPublisher."""
    logger.log_action("test_publisher_init", "Testing PinterestPublisher initialization", "info")
    
    try:
        from integrations.pinterest.pinterest_publisher_ocr import PinterestPublisher
        
        # Test initialization (without actually connecting to browser)
        publisher = PinterestPublisher(
            folder_path=str(test_folder),
            board_name="Test Board",
            dry_run=True,
            connect_existing=False
        )
        
        logger.log_action("publisher_init_success", "Successfully initialized PinterestPublisher", "success")
        logger.log_function_call("PinterestPublisher.__init__", {
            "folder_path": str(test_folder),
            "board_name": "Test Board",
            "dry_run": True
        }, "Publisher instance created")
        
        # Test that config was loaded
        if hasattr(publisher, 'config'):
            logger.log_action("config_loaded", f"Config loaded: {publisher.config.title}", "success")
        else:
            logger.log_action("config_not_loaded", "Config not found in publisher", "failure")
        
        return True
        
    except Exception as e:
        logger.log_error(e, "Failed to initialize PinterestPublisher")
        return False


def test_publish_pinterest_pins_core_dry_run(logger: TestLogger, test_folder: Path):
    """Test publish_pinterest_pins_core with dry_run=True."""
    logger.log_action("test_dry_run", "Testing publish_pinterest_pins_core with dry_run=True", "info")
    
    try:
        from integrations.pinterest.pinterest_tool import publish_pinterest_pins_core
        
        logger.log_function_call("publish_pinterest_pins_core", {
            "folder_path": str(test_folder),
            "board_name": "Test Board",
            "dry_run": True
        })
        
        result = publish_pinterest_pins_core(
            folder_path=str(test_folder),
            board_name="Test Board",
            dry_run=True
        )
        
        logger.log_action("dry_run_success", "Successfully executed dry_run", "success")
        logger.log_function_call("publish_pinterest_pins_core", {}, result)
        
        # Check result structure
        if hasattr(result, 'success'):
            logger.log_action("result_has_success", f"Result.success = {result.success}", "info")
        if hasattr(result, 'total_images'):
            logger.log_action("result_has_total", f"Result.total_images = {result.total_images}", "info")
        if hasattr(result, 'message'):
            logger.log_action("result_has_message", f"Result.message = {result.message}", "info")
        
        return True
        
    except Exception as e:
        logger.log_error(e, "Failed to execute publish_pinterest_pins_core")
        return False


def test_workflow_integration(logger: TestLogger, test_folder: Path):
    """Test the workflow integration."""
    logger.log_action("test_workflow", "Testing workflow integration", "info")
    
    try:
        from workflows.pinterest.publisher import PinterestPublishingWorkflow
        
        workflow = PinterestPublishingWorkflow()
        logger.log_action("workflow_created", "Successfully created PinterestPublishingWorkflow", "success")
        
        # Test prepare_publishing_folder
        design_state = {
            "title": "Test Book",
            "description": "Test description",
            "seo_keywords": ["test", "debug"]
        }
        
        logger.log_function_call("prepare_publishing_folder", {
            "design_state": design_state,
            "images_folder": str(test_folder)
        })
        
        output_folder = workflow.prepare_publishing_folder(
            design_state=design_state,
            images_folder=str(test_folder)
        )
        
        logger.log_action("folder_prepared", f"Prepared folder: {output_folder}", "success")
        
        # Verify folder contents
        output_path = Path(output_folder)
        if (output_path / "book_config.json").exists():
            logger.log_action("json_copied", "JSON config file found in output folder", "success")
        else:
            logger.log_action("json_missing", "JSON config file NOT found in output folder", "failure")
        
        # Check for images
        image_files = list(output_path.glob("*.png")) + list(output_path.glob("*.jpg"))
        if image_files:
            logger.log_action("images_copied", f"Found {len(image_files)} images in output folder", "success")
        else:
            logger.log_action("images_missing", "No images found in output folder", "failure")
        
        return True
        
    except Exception as e:
        logger.log_error(e, "Failed to test workflow integration")
        return False


def main():
    """Main test function."""
    with TestLogger("pinterest_publishing") as logger:
        logger.log_action("test_start", "Starting Pinterest publishing functional tests", "info")
        
        # Create test folder
        test_folder = create_test_folder(logger)
        
        # Test import chain
        if not test_import_chain(logger):
            logger.log_action("import_chain_failed", "Import chain test failed, stopping", "failure")
            return
        
        # Test publisher initialization
        if not test_pinterest_publisher_initialization(logger, test_folder):
            logger.log_action("publisher_init_failed", "Publisher initialization failed", "failure")
        
        # Test dry run
        if not test_publish_pinterest_pins_core_dry_run(logger, test_folder):
            logger.log_action("dry_run_failed", "Dry run test failed", "failure")
        
        # Test workflow integration
        if not test_workflow_integration(logger, test_folder):
            logger.log_action("workflow_test_failed", "Workflow integration test failed", "failure")
        
        logger.log_action("test_complete", "All functional tests completed", "info")


if __name__ == "__main__":
    main()

