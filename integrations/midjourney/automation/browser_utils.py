"""Browser connection utilities for Midjourney web automation."""

from __future__ import annotations

import socket
import subprocess
import time
from typing import Any, Optional

from integrations.midjourney.automation.browser_config import (
    BROWSER_TYPE,
    DEBUG_PORT,
    get_browser_startup_command,
)


def check_browser_connection(port: Optional[int] = None) -> dict[str, Any]:
    """Check if browser is running with debugging port."""
    if port is None:
        port = DEBUG_PORT

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", port))
        sock.close()

        if result == 0:
            return {"connected": True, "port": port, "error": None}
        return {"connected": False, "port": port, "error": f"Port {port} is not accessible"}
    except Exception as e:
        return {"connected": False, "port": port, "error": str(e)}


def launch_browser_with_debugging() -> dict[str, Any]:
    """Launch browser with debugging enabled."""
    try:
        command = get_browser_startup_command()

        process = subprocess.Popen(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

        time.sleep(2)
        connection_status = check_browser_connection()

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


def get_browser_status() -> dict[str, Any]:
    """Get current browser connection status."""
    connection_status = check_browser_connection()
    return {
        **connection_status,
        "browser_type": BROWSER_TYPE,
        "debug_port": DEBUG_PORT,
    }
