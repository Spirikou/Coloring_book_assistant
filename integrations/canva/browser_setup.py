"""
Browser setup utilities for Canva integration.

Provides functions to check browser status and print setup instructions.
Since browser profiles are working well, we keep the manual setup approach
but provide utilities to help with verification and instructions.
"""

import socket
import logging
from typing import Optional

from . import config

logger = logging.getLogger(__name__)


def check_browser_running(port: int = None) -> bool:
    """
    Check if browser is running on the specified remote debugging port.

    Args:
        port: Remote debugging port (defaults to config.DEBUG_PORT)

    Returns:
        True if browser is running on the port, False otherwise
    """
    if port is None:
        port = config.DEBUG_PORT

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.debug(f"Error checking browser port: {e}")
        return False


def get_browser_startup_command() -> str:
    """
    Get the PowerShell command to start the browser with remote debugging.

    Returns:
        PowerShell command string to start browser with debugging enabled
    """
    return config.get_browser_startup_command()


def print_browser_setup_instructions() -> None:
    """
    Print detailed instructions for setting up the browser.

    This function provides clear instructions for starting the browser
    with remote debugging enabled, which is required for the agent to work.
    """
    browser_name = config.BROWSER_TYPE.capitalize()
    port = config.DEBUG_PORT

    print("\n" + "="*60)
    print(f"{browser_name} Browser Setup Instructions")
    print("="*60)
    print(f"\nThe Canva agent requires {browser_name} to be running with remote debugging enabled.")
    print(f"\nStep 1: Close all {browser_name} windows (if open)")
    print(f"Step 2: Start {browser_name} with the following command:\n")
    print(get_browser_startup_command())
    print("\nStep 3: Log into Canva in the browser window")
    print("Step 4: Keep the browser window open and run the agent")
    print("\nNote: The browser will remember your login (profile persistence)")
    print("="*60 + "\n")


def ensure_browser_running(port: int = None, print_instructions: bool = True) -> bool:
    """
    Check if browser is running and provide instructions if not.

    Args:
        port: Remote debugging port (defaults to config.DEBUG_PORT)
        print_instructions: If True, print setup instructions when browser is not running

    Returns:
        True if browser is running, False otherwise
    """
    if port is None:
        port = config.DEBUG_PORT

    is_running = check_browser_running(port)

    if not is_running and print_instructions:
        print_browser_setup_instructions()

    return is_running
