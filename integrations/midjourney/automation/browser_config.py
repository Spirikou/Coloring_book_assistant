"""Browser configuration for Midjourney web automation.

Supports Chrome, Brave, Edge, and other Chromium-based browsers.
User must start browser with --remote-debugging-port=9222 and log in to Midjourney before running.
"""

import os
from pathlib import Path

from config import PROJECT_ROOT, get_midjourney_config

# Read from project config
_cfg = get_midjourney_config()
DEBUG_PORT = _cfg.get("browser_debug_port", 9222)
DEBUG_FOLDER = PROJECT_ROOT / "debug"

# ============================================================================
# BROWSER CONFIGURATION
# ============================================================================
BROWSER_TYPE = "brave"  # Options: "chrome", "brave", "edge", "chromium"

BROWSER_PATHS = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "brave": os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "chromium": r"C:\Program Files\Chromium\Application\chrome.exe",
}

BROWSER_USER_DATA_DIRS = {
    "chrome": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
    "brave": os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data"),
    "edge": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data"),
    "chromium": os.path.expandvars(r"%LOCALAPPDATA%\Chromium\User Data"),
}

# Separate profile for automation so "Launch Browser" always starts a new process
# that binds to the debug port (avoids being absorbed by an already-open browser).
BROWSER_AUTOMATION_USER_DATA_DIRS = {
    "chrome": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data-Automation"),
    "brave": os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data-Automation"),
    "edge": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data-Automation"),
    "chromium": os.path.expandvars(r"%LOCALAPPDATA%\Chromium\User Data-Automation"),
}

BROWSER_PROFILE = "Default"


def get_browser_path() -> str:
    """Get the path to the configured browser executable, with auto-detection."""
    configured_path = BROWSER_PATHS.get(BROWSER_TYPE, BROWSER_PATHS["chrome"])
    if os.path.exists(configured_path):
        return configured_path

    common_paths = {
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
        "brave": [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%APPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ],
        "edge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        "chromium": [
            r"C:\Program Files\Chromium\Application\chrome.exe",
            r"C:\Program Files (x86)\Chromium\Application\chrome.exe",
        ],
    }

    for path in common_paths.get(BROWSER_TYPE, []):
        if os.path.exists(path):
            return path

    return configured_path


def get_browser_user_data_dir() -> str:
    """Get the user data directory for the configured browser."""
    return BROWSER_USER_DATA_DIRS.get(BROWSER_TYPE, BROWSER_USER_DATA_DIRS["chrome"])


def get_browser_automation_user_data_dir() -> str:
    """Get the user data directory used when launching the browser for automation.
    Using a separate dir ensures the launched process is always a new instance that
    binds to the debug port, instead of being absorbed by an already-open browser.
    """
    return BROWSER_AUTOMATION_USER_DATA_DIRS.get(
        BROWSER_TYPE, BROWSER_AUTOMATION_USER_DATA_DIRS["chrome"]
    )


def get_browser_startup_command() -> str:
    """Get the PowerShell command to start the browser with debugging.
    Uses the automation profile so Launch Browser always gets a dedicated process.
    """
    browser_path = get_browser_path()
    user_data_dir = get_browser_automation_user_data_dir()
    return f'& "{browser_path}" --remote-debugging-port={DEBUG_PORT} --user-data-dir="{user_data_dir}" --profile-directory={BROWSER_PROFILE}'
