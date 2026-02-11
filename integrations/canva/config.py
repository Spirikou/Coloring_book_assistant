"""
Central configuration for Canva integration (embedded in Coloring Book Assistant).
Uses the same browser approach as Pinterest agent - Brave browser with CDP connection.

Adjust these values instead of passing CLI flags each run.
"""

import os
from pathlib import Path

# ============================================================================
# BROWSER CONFIGURATION (Same approach as Pinterest agent)
# ============================================================================
# Choose which browser to use for automation: "chrome", "brave", "edge", or "chromium"
# Using Brave (recommended) avoids conflicts with your main Chrome browser
BROWSER_TYPE = "brave"  # Options: "chrome", "brave", "edge", "chromium"

# Remote debugging port (default: 9222)
# Make sure this port is not used by other applications
DEBUG_PORT = 9222

# Browser executable paths (auto-detected, but can be overridden)
# Windows defaults:
BROWSER_PATHS = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "brave": r"C:\Users\alexa\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "chromium": r"C:\Program Files\Chromium\Application\chrome.exe",
}

# Browser user data directories
# Windows defaults:
BROWSER_USER_DATA_DIRS = {
    "chrome": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
    "brave": os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data"),
    "edge": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data"),
    "chromium": os.path.expandvars(r"%LOCALAPPDATA%\Chromium\User Data"),
}

# Profile directory name
# "Default" for the main profile, or "Profile 1", "Profile 2", etc.
BROWSER_PROFILE = "Default"

# ============================================================================
# PATHS (default - workflow passes images_folder_path at runtime)
# ============================================================================
IMAGES_FOLDER: Path = Path(r"C:\Users\alexa\Downloads\coloring_book_1")

# ============================================================================
# CANVAS / LAYOUT
# ============================================================================
PAGE_WIDTH_IN: float = 8.625
PAGE_HEIGHT_IN: float = 8.75
PAGE_COUNT: int = 1  # Design starts with 1 page, pages are added dynamically as images are placed
MARGIN_PERCENT: float = 8.0
OUTLINE_HEIGHT_PERCENT: float = 6.0
BLANK_BETWEEN: bool = True  # leave a blank page after each placed image

# ============================================================================
# DEFAULTS (for workflow integration)
# ============================================================================
DEFAULT_PAGE_SIZE = "8.625x8.75"
DEFAULT_MARGIN_PERCENT = 8.0
DEFAULT_OUTLINE_HEIGHT_PERCENT = 6.0
DEFAULT_BLANK_BETWEEN = True

# ============================================================================
# BROWSER / SESSION
# ============================================================================
HEADLESS: bool = False
DRY_RUN: bool = False

# Cloudflare verification mode:
# "auto" = Try to automatically click Cloudflare (may not always work)
# "manual" = Pause and wait for you to manually complete Cloudflare verification
CLOUDFLARE_MODE: str = "manual"  # Recommended: "manual" for reliability

# Browser launch mode:
# True = Connect to your currently open browser window (opens new tab - preserves login)
#        Browser must be started with: --remote-debugging-port=9222
# False = Launch browser automatically with your profile (uses your login cookies)
#         This mode is less reliable and may have conflicts
CONNECT_EXISTING: bool = True  # Connect to existing browser (recommended - same as Pinterest agent)
REMOTE_DEBUG_URL: str = f"http://127.0.0.1:{DEBUG_PORT}"

# Legacy Chrome config (kept for backward compatibility, but use BROWSER_USER_DATA_DIRS instead)
CHROME_USER_DATA_DIR: Path = BROWSER_USER_DATA_DIRS.get("chrome", Path(r"C:\Users\alexa\AppData\Local\Google\Chrome\User Data"))
CHROME_PROFILE: str = BROWSER_PROFILE

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_browser_path() -> str:
    """Get the path to the configured browser executable, with auto-detection."""
    import os.path

    # Try the configured path first
    configured_path = BROWSER_PATHS.get(BROWSER_TYPE, BROWSER_PATHS["chrome"])
    if os.path.exists(configured_path):
        return configured_path

    # Auto-detect common locations
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
            r"C:\Users\alexa\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Users\alexa\AppData\Local\Programs\Brave-Browser\Application\brave.exe",
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

    # Try common paths for the selected browser
    for path in common_paths.get(BROWSER_TYPE, []):
        if os.path.exists(path):
            return path

    # Fallback to configured path (will raise error if not found)
    return configured_path


def get_browser_user_data_dir() -> str:
    """Get the user data directory for the configured browser."""
    return BROWSER_USER_DATA_DIRS.get(BROWSER_TYPE, BROWSER_USER_DATA_DIRS["chrome"])


def get_browser_startup_command() -> str:
    """Get the PowerShell command to start the browser with debugging."""
    browser_path = get_browser_path()
    user_data_dir = get_browser_user_data_dir()
    return f'& "{browser_path}" --remote-debugging-port={DEBUG_PORT} --user-data-dir="{user_data_dir}" --profile-directory={BROWSER_PROFILE}'
