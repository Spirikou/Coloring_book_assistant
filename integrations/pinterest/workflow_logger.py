"""
Workflow logger for Pinterest publishing - captures all actions and errors during live execution.
"""

import sys
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class WorkflowLogger:
    """Logger for live workflow execution."""
    
    def __init__(self):
        """Initialize logger with log file."""
        # Create logs directory
        log_dir = Path(__file__).parent.parent.parent / "tests" / "integrations" / "pinterest" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = log_dir / f"workflow_{timestamp}.log"
        
        # Open log file
        self.file_handle = open(self.log_file, 'w', encoding='utf-8')
        
        # Log initialization
        self.log("=" * 80)
        self.log("PINTEREST PUBLISHING WORKFLOW LOG")
        self.log("=" * 80)
        self.log_environment()
        self.log("=" * 80)
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Write to file
        self.file_handle.write(log_entry + "\n")
        self.file_handle.flush()
        
        # Also print to console
        print(log_entry)
    
    def log_action(self, action: str, details: Optional[Dict[str, Any]] = None):
        """Log an action with details."""
        message = f"ACTION: {action}"
        if details:
            for key, value in details.items():
                message += f"\n  {key}: {value}"
        self.log(message, "ACTION")
    
    def log_import(self, module: str, success: bool, error: Optional[Exception] = None):
        """Log an import attempt."""
        status = "SUCCESS" if success else "FAILED"
        message = f"IMPORT: {module} - {status}"
        if error:
            message += f"\n  Error: {error}\n  Traceback:\n{traceback.format_exc()}"
        self.log(message, "IMPORT")
    
    def log_function_call(self, function_name: str, params: Optional[Dict[str, Any]] = None):
        """Log a function call."""
        message = f"FUNCTION CALL: {function_name}"
        if params:
            for key, value in params.items():
                message += f"\n  {key}: {value}"
        self.log(message, "CALL")
    
    def log_error(self, error: Exception, context: Optional[str] = None):
        """Log an error with full traceback."""
        message = f"ERROR: {type(error).__name__}: {str(error)}"
        if context:
            message += f"\n  Context: {context}"
        message += f"\n  Traceback:\n{traceback.format_exc()}"
        self.log(message, "ERROR")
    
    def log_environment(self):
        """Log Python environment."""
        self.log("ENVIRONMENT:", "INFO")
        self.log(f"  Python Version: {sys.version}", "INFO")
        self.log(f"  Python Executable: {sys.executable}", "INFO")
        self.log(f"  Working Directory: {os.getcwd()}", "INFO")
        self.log(f"  Script Location: {Path(__file__).parent}", "INFO")
        self.log(f"  Sys Path (first 5):", "INFO")
        for i, path in enumerate(sys.path[:5]):
            self.log(f"    [{i}] {path}", "INFO")
    
    def close(self):
        """Close the log file."""
        self.log("=" * 80)
        self.log(f"Log file saved to: {self.log_file}", "INFO")
        self.log("=" * 80)
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None


# Global logger instance
_workflow_logger: Optional[WorkflowLogger] = None


def get_workflow_logger() -> WorkflowLogger:
    """Get or create the global workflow logger."""
    global _workflow_logger
    if _workflow_logger is None:
        _workflow_logger = WorkflowLogger()
    return _workflow_logger


def log_import_attempt(module: str):
    """Decorator/helper to log import attempts."""
    logger = get_workflow_logger()
    try:
        # Try to import
        __import__(module)
        logger.log_import(module, True)
        return True
    except Exception as e:
        logger.log_import(module, False, e)
        return False

