"""
Centralized logging utility for Pinterest integration tests.
Provides structured logging with both console and file output.
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import traceback


class TestLogger:
    """Logger for test scripts with console and file output."""
    
    # ANSI color codes for console output
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'cyan': '\033[36m',
        'gray': '\033[90m',
    }
    
    def __init__(self, test_name: str = "pinterest_test"):
        """Initialize logger with test name."""
        self.test_name = test_name
        self.log_dir = Path(__file__).parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"{test_name}_{timestamp}.log"
        
        # Statistics
        self.actions = []
        self.success_count = 0
        self.failure_count = 0
        self.error_count = 0
        
        # Open log file
        self.file_handle = open(self.log_file, 'w', encoding='utf-8')
        
        # Log initialization
        self.log_environment()
        self.log_action("test_start", f"Starting {test_name}", "info")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close file and generate summary."""
        self.generate_summary()
        if self.file_handle:
            self.file_handle.close()
    
    def _write_log(self, level: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Write log entry to both console and file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format log entry
        log_entry = f"[{timestamp}] [{level}] {message}"
        if details:
            for key, value in details.items():
                if value is not None:
                    log_entry += f"\n  {key}: {value}"
        
        # Write to file
        self.file_handle.write(log_entry + "\n")
        self.file_handle.flush()
        
        # Write to console with colors
        if level == "ERROR":
            console_msg = f"{self.COLORS['red']}{log_entry}{self.COLORS['reset']}"
        elif level == "SUCCESS":
            console_msg = f"{self.COLORS['green']}{log_entry}{self.COLORS['reset']}"
        elif level == "WARNING":
            console_msg = f"{self.COLORS['yellow']}{log_entry}{self.COLORS['reset']}"
        elif level == "INFO":
            console_msg = f"{self.COLORS['cyan']}{log_entry}{self.COLORS['reset']}"
        else:
            console_msg = log_entry
        
        print(console_msg)
    
    def log_action(self, action_name: str, details: str, status: str = "info"):
        """Log an action with status."""
        action_entry = {
            "action": action_name,
            "details": details,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        self.actions.append(action_entry)
        
        level = "INFO"
        if status == "success":
            level = "SUCCESS"
            self.success_count += 1
        elif status == "failure":
            level = "ERROR"
            self.failure_count += 1
        
        log_details = {
            "Action": action_name,
            "Details": details,
            "Status": status
        }
        self._write_log(level, f"ACTION: {action_name}", log_details)
    
    def log_error(self, error: Exception, context: Optional[str] = None):
        """Log an error with full traceback."""
        self.error_count += 1
        error_msg = str(error)
        error_type = type(error).__name__
        tb = traceback.format_exc()
        
        log_details = {
            "Error Type": error_type,
            "Error Message": error_msg,
            "Context": context or "No additional context",
            "Traceback": tb
        }
        self._write_log("ERROR", f"ERROR: {error_type}", log_details)
        
        # Also log as action
        self.log_action("error_occurred", f"{error_type}: {error_msg}", "failure")
    
    def log_import_attempt(self, module: str, import_type: str, success: bool, error: Optional[Exception] = None):
        """Log an import attempt."""
        status = "success" if success else "failure"
        details = f"Attempting to import {module} using {import_type} import"
        
        log_details = {
            "Module": module,
            "Import Type": import_type,
            "Success": success
        }
        
        if error:
            log_details["Error"] = str(error)
            log_details["Error Type"] = type(error).__name__
            log_details["Traceback"] = traceback.format_exc()
            self.failure_count += 1
        else:
            self.success_count += 1
        
        level = "SUCCESS" if success else "ERROR"
        self._write_log(level, f"IMPORT: {module} ({import_type})", log_details)
        self.log_action("import_attempt", details, status)
    
    def log_environment(self):
        """Log Python environment information."""
        import sys
        import platform
        
        env_info = {
            "Python Version": sys.version,
            "Python Executable": sys.executable,
            "Platform": platform.platform(),
            "Working Directory": os.getcwd(),
            "Script Directory": str(Path(__file__).parent.parent.parent.parent),
            "Sys Path": sys.path[:10]  # First 10 entries
        }
        
        self._write_log("INFO", "ENVIRONMENT CHECK", env_info)
        self.log_action("environment_check", "Python environment information", "info")
    
    def log_function_call(self, function_name: str, params: Optional[Dict[str, Any]] = None, result: Optional[Any] = None):
        """Log a function call with parameters and result."""
        details = {
            "Function": function_name,
            "Parameters": params or {},
            "Result": str(result) if result is not None else "None"
        }
        self._write_log("INFO", f"FUNCTION CALL: {function_name}", details)
        self.log_action("function_call", f"Calling {function_name}", "info")
    
    def generate_summary(self):
        """Generate and log test summary."""
        total_actions = len(self.actions)
        total_tests = self.success_count + self.failure_count
        
        summary = {
            "Test Name": self.test_name,
            "Total Actions": total_actions,
            "Successful": self.success_count,
            "Failed": self.failure_count,
            "Errors": self.error_count,
            "Success Rate": f"{(self.success_count / total_tests * 100):.1f}%" if total_tests > 0 else "N/A",
            "Log File": str(self.log_file)
        }
        
        self._write_log("INFO", "TEST SUMMARY", summary)
        print(f"\n{self.COLORS['bold']}{'='*60}{self.COLORS['reset']}")
        print(f"{self.COLORS['bold']}Test Summary{self.COLORS['reset']}")
        print(f"{self.COLORS['bold']}{'='*60}{self.COLORS['reset']}")
        print(f"Total Actions: {total_actions}")
        print(f"{self.COLORS['green']}Successful: {self.success_count}{self.COLORS['reset']}")
        print(f"{self.COLORS['red']}Failed: {self.failure_count}{self.COLORS['reset']}")
        print(f"{self.COLORS['red']}Errors: {self.error_count}{self.COLORS['reset']}")
        if total_tests > 0:
            print(f"Success Rate: {summary['Success Rate']}")
        print(f"Log File: {self.log_file}")
        print(f"{self.COLORS['bold']}{'='*60}{self.COLORS['reset']}\n")
    
    def close(self):
        """Close the log file."""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None

