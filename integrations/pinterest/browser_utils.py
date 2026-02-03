"""Browser connection utilities for Pinterest publishing."""

import socket
import subprocess
from typing import Dict, Optional

try:
    from .config import get_browser_startup_command, DEBUG_PORT, BROWSER_TYPE
except ImportError:
    # Fallback for absolute import
    from integrations.pinterest.config import get_browser_startup_command, DEBUG_PORT, BROWSER_TYPE


def check_browser_connection(port: Optional[int] = None) -> Dict[str, any]:
    """
    Check if browser is running with debugging port.
    
    Args:
        port: Port to check (defaults to DEBUG_PORT from config)
        
    Returns:
        dict with: connected (bool), port (int), error (str)
    """
    if port is None:
        port = DEBUG_PORT
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            return {
                "connected": True,
                "port": port,
                "error": None
            }
        else:
            return {
                "connected": False,
                "port": port,
                "error": f"Port {port} is not accessible"
            }
    except Exception as e:
        return {
            "connected": False,
            "port": port,
            "error": str(e)
        }


def launch_browser_with_debugging() -> Dict[str, any]:
    """
    Automatically launch browser with debugging enabled.
    
    Returns:
        dict with: success (bool), message (str), command (str)
    """
    try:
        command = get_browser_startup_command()
        
        # Launch browser in background using PowerShell
        process = subprocess.Popen(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        # Wait a moment for browser to start
        import time
        time.sleep(2)
        
        # Check if connection is now available
        connection_status = check_browser_connection()
        
        if connection_status["connected"]:
            return {
                "success": True,
                "message": f"Browser launched successfully on port {DEBUG_PORT}",
                "command": command,
                "browser_type": BROWSER_TYPE
            }
        else:
            return {
                "success": False,
                "message": f"Browser launched but connection check failed: {connection_status.get('error', 'Unknown error')}",
                "command": command,
                "browser_type": BROWSER_TYPE
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to launch browser: {str(e)}",
            "command": None,
            "browser_type": BROWSER_TYPE
        }


def get_browser_status() -> Dict[str, any]:
    """
    Get current browser connection status.
    
    Returns:
        dict with connection status and browser info
    """
    connection_status = check_browser_connection()
    
    return {
        **connection_status,
        "browser_type": BROWSER_TYPE,
        "debug_port": DEBUG_PORT
    }

