"""
State manager for tracking published pins and enabling resume capability.
"""

import json
import logging
from pathlib import Path
from typing import Optional

try:
    from .config import STATE_FILE_NAME
except ImportError:
    # Fallback for absolute import
    from integrations.pinterest.config import STATE_FILE_NAME

from .models import PublishResult

logger = logging.getLogger(__name__)


class StateManager:
    """Manages state of published pins to enable resume and prevent duplicates."""
    
    def __init__(self, image_folder: str):
        """
        Initialize state manager.
        
        Args:
            image_folder: Path to folder containing images. State file will be
                          created in this folder.
        """
        self.image_folder = Path(image_folder)
        self.state_file = self.image_folder / STATE_FILE_NAME
        self.state: dict[str, dict] = {}
        self._load_state()
    
    def _load_state(self) -> None:
        """Load existing state from file if it exists."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
                logger.info(f"Loaded state with {len(self.state)} published pins")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse state file: {e}. Starting fresh.")
                self.state = {}
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}. Starting fresh.")
                self.state = {}
        else:
            logger.info("No existing state file found. Starting fresh.")
            self.state = {}
    
    def _save_state(self) -> None:
        """Save current state to file."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def is_published(self, filename: str) -> bool:
        """
        Check if an image has already been successfully published.
        
        Args:
            filename: Image filename to check
            
        Returns:
            True if already published successfully, False otherwise
        """
        if filename in self.state:
            return self.state[filename].get("status") == "success"
        return False
    
    def get_status(self, filename: str) -> Optional[dict]:
        """
        Get the publish status for an image.
        
        Args:
            filename: Image filename
            
        Returns:
            Status dict or None if not in state
        """
        return self.state.get(filename)
    
    def record_result(self, result: PublishResult) -> None:
        """
        Record the result of a publish attempt.
        
        Args:
            result: PublishResult object with outcome details
        """
        self.state[result.image_filename] = result.to_dict()
        self._save_state()
        
        status = "SUCCESS" if result.success else "FAILED"
        logger.info(f"Recorded {status} for {result.image_filename}")
    
    def record_success(self, filename: str, title: str) -> None:
        """
        Convenience method to record a successful publish.
        
        Args:
            filename: Image filename
            title: Title used for the pin
        """
        result = PublishResult(
            image_path="",
            image_filename=filename,
            success=True,
            title=title,
        )
        self.record_result(result)
    
    def record_failure(self, filename: str, error: str) -> None:
        """
        Convenience method to record a failed publish.
        
        Args:
            filename: Image filename
            error: Error message describing the failure
        """
        result = PublishResult(
            image_path="",
            image_filename=filename,
            success=False,
            error=error,
        )
        self.record_result(result)
    
    def get_summary(self) -> dict:
        """
        Get summary statistics of publish state.
        
        Returns:
            Dict with counts of successful, failed, and total pins
        """
        successful = sum(1 for v in self.state.values() if v.get("status") == "success")
        failed = sum(1 for v in self.state.values() if v.get("status") == "failed")
        return {
            "total": len(self.state),
            "successful": successful,
            "failed": failed,
        }
    
    def get_unpublished_images(self, all_images: list[str]) -> list[str]:
        """
        Filter list of images to only those not yet successfully published.
        
        Args:
            all_images: List of image filenames
            
        Returns:
            List of filenames that haven't been successfully published
        """
        return [img for img in all_images if not self.is_published(img)]
    
    def clear_failures(self) -> int:
        """
        Clear all failed entries so they can be retried.
        
        Returns:
            Number of entries cleared
        """
        failed_keys = [k for k, v in self.state.items() if v.get("status") == "failed"]
        for key in failed_keys:
            del self.state[key]
        self._save_state()
        logger.info(f"Cleared {len(failed_keys)} failed entries")
        return len(failed_keys)

