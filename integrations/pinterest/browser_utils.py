"""Browser connection utilities for Pinterest publishing.

Connection check delegates to core.browser_config. Use get_port_for_role("pinterest")
to obtain the port for the Pinterest slot when calling check_browser_connection(port).
"""

import subprocess
from typing import Any, Dict

try:
    from .config import get_browser_startup_command, DEBUG_PORT, BROWSER_TYPE
except ImportError:
    from integrations.pinterest.config import get_browser_startup_command, DEBUG_PORT, BROWSER_TYPE

from core.browser_config import check_browser_connection as _core_check_browser_connection
from core.browser_config import get_port_for_role


def check_browser_connection(port: int) -> Dict[str, Any]:
    """
    Check if browser is running with debugging port. Delegates to core.

    Args:
        port: Port to check (use get_port_for_role("pinterest") for the Pinterest slot).

    Returns:
        dict with: connected (bool), port (int), error (str | None)
    """
    return _core_check_browser_connection(port)


def launch_browser_with_debugging() -> Dict[str, Any]:
    """
    Automatically launch browser with debugging enabled.
    Launches on DEBUG_PORT from config; after launch we check that port.
    """
    import time

    try:
        command = get_browser_startup_command()
        subprocess.Popen(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        time.sleep(2)
        connection_status = check_browser_connection(DEBUG_PORT)

        if connection_status["connected"]:
            return {
                "success": True,
                "message": f"Browser launched successfully on port {DEBUG_PORT}",
                "command": command,
                "browser_type": BROWSER_TYPE,
            }
        return {
            "success": False,
            "message": f"Browser launched but connection check failed: {connection_status.get('error', 'Unknown error')}",
            "command": command,
            "browser_type": BROWSER_TYPE,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to launch browser: {str(e)}",
            "command": None,
            "browser_type": BROWSER_TYPE,
        }


def get_browser_status() -> Dict[str, Any]:
    """Get current browser connection status for the Pinterest slot."""
    port = get_port_for_role("pinterest")
    connection_status = check_browser_connection(port)
    return {
        **connection_status,
        "browser_type": BROWSER_TYPE,
        "debug_port": port,
    }

