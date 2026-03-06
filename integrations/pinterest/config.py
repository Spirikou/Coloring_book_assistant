"""
Configuration constants for Pinterest Pin Publisher.
Supports Chrome, Brave, Edge, and other Chromium-based browsers.
Set BROWSER_TYPE in this file to choose which browser to use.
"""

import os

# ============================================================================
# BROWSER CONFIGURATION
# ============================================================================
# Choose which browser to use for automation: "chrome", "brave", "edge", or "chromium"
# Using a separate browser (like Edge or Brave) avoids conflicts with your main Chrome
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

# Legacy Chrome config (kept for backward compatibility)
CHROME_USER_DATA_DIR = BROWSER_USER_DATA_DIRS.get("chrome", "")
CHROME_PROFILE = BROWSER_PROFILE

# ============================================================================
# IMAGE SETTINGS
# ============================================================================
# Supported image file extensions
SUPPORTED_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]

# ============================================================================
# TIMING CONFIGURATION
# ============================================================================
# Delay between publishing pins (seconds) - helps avoid rate limiting
# Reduced from 7 to 4 for faster batches (analysis: docs/PINTEREST_PUBLISHING_ANALYSIS_AND_IMPROVEMENT_PLAN.md)
DELAY_BETWEEN_PINS = 4

# Process timeout (seconds) - max time for multiprocessing publisher before termination
# 7200 = 2 hours, allows ~100+ images at ~60 sec/image
PROCESS_TIMEOUT = 7200

# Timeouts for various operations (milliseconds)
PAGE_LOAD_TIMEOUT = 15000
IMAGE_UPLOAD_TIMEOUT = 10000
PUBLISH_TIMEOUT = 15000

# Description processing delay (milliseconds)
# Wait after filling description to ensure Pinterest processes it before publishing
DESCRIPTION_PROCESSING_DELAY = 500  # Reduced from 1000; fast fill needs less

# Keyboard type delay (ms per character) for description when keyboard.type fallback is used
# Reduced from 10 to 1 for ~5 sec savings per 600-char description
KEYBOARD_TYPE_DELAY_MS = 1

# Maximum description length (limit to 600 to avoid bugs)
MAX_DESCRIPTION_LENGTH = 600

# ============================================================================
# OPENAI CONFIGURATION
# ============================================================================
# Uses PINTEREST_MODEL and temperature from main config
from config import PINTEREST_MODEL, PINTEREST_MODEL_TEMPERATURE
OPENAI_MODEL = PINTEREST_MODEL
OPENAI_TEMPERATURE = PINTEREST_MODEL_TEMPERATURE

# ============================================================================
# PINTEREST SELECTORS
# ============================================================================
# These selectors may need updating if Pinterest changes their UI
# Using data-test-id attributes when available for stability

SELECTORS = {
    # Pin builder form
    "pin_builder_form": '[data-test-id="pin-builder-form"]',
    
    # File upload
    "file_input": 'input[type="file"]',
    "image_preview": '[data-test-id="pin-draft-image-preview"]',
    
    # Text inputs
    "title_input": '[data-test-id="pin-draft-title"] textarea, [data-test-id="editor-with-mentions"] textarea, textarea[placeholder*="title" i]',
    "description_input": '[data-test-id="pin-draft-description"] textarea, [data-test-id="pin-draft-description"] [contenteditable], div[data-test-id="editor-with-mentions"]',
    
    # Alt text (may be in "More options" section)
    "more_options_button": 'button:has-text("More options"), [data-test-id="more-options-button"]',
    "alt_text_input": '[data-test-id="pin-draft-alt-text"] textarea, textarea[placeholder*="alt" i]',
    
    # Board selection
    "board_dropdown": '[data-test-id="board-dropdown-select-button"], button:has-text("Select"), [data-test-id="board-dropdown"]',
    "board_search": '[data-test-id="board-dropdown-search"] input, input[placeholder*="Search" i]',
    "board_option": '[data-test-id="board-dropdown-option"]',
    
    # Publish
    "publish_button": '[data-test-id="board-dropdown-save-button"], button:has-text("Publish"), [data-test-id="create-pin-button"]',
    
    # Success indicators
    "success_toast": 'text="Pin published", text="Saved to"',
}

# ============================================================================
# STATE FILE
# ============================================================================
STATE_FILE_NAME = "published_pins.json"


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

