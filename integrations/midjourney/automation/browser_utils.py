"""Browser connection utilities for Midjourney web automation.

Connection check delegates to core.browser_config. Use get_port_for_role("midjourney")
to obtain the port for the Midjourney slot when calling check_browser_connection(port).
"""

from __future__ import annotations

import subprocess
import time
from typing import Any

from core.browser_config import check_browser_connection as _core_check_browser_connection
from core.browser_config import get_port_for_role
from integrations.midjourney.automation.browser_config import (
    BROWSER_TYPE,
    get_browser_startup_command,
    get_browser_startup_command_for_port,
)


def check_browser_connection(port: int) -> dict[str, Any]:
    """Check if browser is running with debugging port. Delegates to core."""
    return _core_check_browser_connection(port)


def launch_browser_with_debugging() -> dict[str, Any]:
    """Launch browser with debugging enabled for the Midjourney slot."""
    port = get_port_for_role("midjourney")
    try:
        command = get_browser_startup_command()

        subprocess.Popen(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        time.sleep(2)
        connection_status = check_browser_connection(port)

        if connection_status["connected"]:
            return {
                "success": True,
                "message": f"Browser launched successfully on port {port}",
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


def launch_browser_for_port(port: int) -> dict[str, Any]:
    """Launch browser with debugging on the given port (e.g. for a Config tab slot).
    Uses a port-specific profile so multiple instances do not conflict.
    """
    if port <= 0 or port > 65535:
        return {
            "success": False,
            "message": f"Invalid port: {port}",
            "command": None,
            "browser_type": BROWSER_TYPE,
        }
    try:
        command = get_browser_startup_command_for_port(port)
        subprocess.Popen(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        time.sleep(2)
        connection_status = _core_check_browser_connection(port)
        if connection_status["connected"]:
            return {
                "success": True,
                "message": f"Browser launched on port {port}",
                "command": command,
                "browser_type": BROWSER_TYPE,
            }
        return {
            "success": False,
            "message": f"Browser started but connection check failed: {connection_status.get('error', 'Unknown error')}",
            "command": command,
            "browser_type": BROWSER_TYPE,
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "command": None,
            "browser_type": BROWSER_TYPE,
        }


def get_browser_status() -> dict[str, Any]:
    """Get current browser connection status for the Midjourney slot."""
    port = get_port_for_role("midjourney")
    connection_status = check_browser_connection(port)
    return {
        **connection_status,
        "browser_type": BROWSER_TYPE,
        "debug_port": port,
    }
