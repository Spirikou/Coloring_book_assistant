"""
Pinterest Pin Publisher - Robust keyboard-based approach.
Uses Tab navigation instead of fragile element selectors.
"""

import json
import logging
import time
import threading
import asyncio
from pathlib import Path
from typing import Optional

# Import workflow logger first
try:
    from .workflow_logger import get_workflow_logger
    workflow_logger = get_workflow_logger()
    workflow_logger.log("pinterest_publisher_ocr.py: Module loaded", "INFO")
except Exception as e:
    workflow_logger = None
    print(f"Warning: Could not initialize workflow logger in pinterest_publisher_ocr: {e}")

from playwright.sync_api import sync_playwright, BrowserContext, Page

# Log config import attempt
if workflow_logger:
    try:
        from .config import SUPPORTED_EXTENSIONS, DELAY_BETWEEN_PINS, BROWSER_TYPE, DEBUG_PORT, DESCRIPTION_PROCESSING_DELAY, MAX_DESCRIPTION_LENGTH
        workflow_logger.log_import("integrations.pinterest.config (relative)", True)
    except Exception as e:
        workflow_logger.log_import("integrations.pinterest.config (relative)", False, e)
        try:
            from integrations.pinterest.config import SUPPORTED_EXTENSIONS, DELAY_BETWEEN_PINS, BROWSER_TYPE, DEBUG_PORT, DESCRIPTION_PROCESSING_DELAY, MAX_DESCRIPTION_LENGTH
            workflow_logger.log_import("integrations.pinterest.config (absolute)", True)
        except Exception as e2:
            workflow_logger.log_import("integrations.pinterest.config (absolute)", False, e2)
            raise e  # Re-raise original error
else:
    try:
        from .config import SUPPORTED_EXTENSIONS, DELAY_BETWEEN_PINS, BROWSER_TYPE, DEBUG_PORT, DESCRIPTION_PROCESSING_DELAY, MAX_DESCRIPTION_LENGTH
    except ImportError:
        # Fallback for absolute import
        from integrations.pinterest.config import SUPPORTED_EXTENSIONS, DELAY_BETWEEN_PINS, BROWSER_TYPE, DEBUG_PORT, DESCRIPTION_PROCESSING_DELAY, MAX_DESCRIPTION_LENGTH

# Log other imports
if workflow_logger:
    try:
        from .models import BookConfig, ImageInfo
        workflow_logger.log_import("integrations.pinterest.models", True)
    except Exception as e:
        workflow_logger.log_import("integrations.pinterest.models", False, e)
        raise
    
    try:
        from .content_generator import generate_pin_content
        workflow_logger.log_import("integrations.pinterest.content_generator", True)
    except Exception as e:
        workflow_logger.log_import("integrations.pinterest.content_generator", False, e)
        raise
    
    try:
        from .state_manager import StateManager
        workflow_logger.log_import("integrations.pinterest.state_manager", True)
    except Exception as e:
        workflow_logger.log_import("integrations.pinterest.state_manager", False, e)
        raise
else:
    from .models import BookConfig, ImageInfo
    from .content_generator import generate_pin_content
    from .state_manager import StateManager

logger = logging.getLogger(__name__)

PIN_BUILDER_URL = "https://www.pinterest.com/pin-builder/"
UI_COORDS_FILE = "ui_coords.json"


def _is_in_streamlit_context(force_check: bool = False) -> bool:
    """
    Detect if running in Streamlit context using multiple methods.
    
    Args:
        force_check: If True, force Streamlit mode (from UI layer)
    
    Returns:
        True if in Streamlit context, False otherwise
    """
    if force_check:
        if workflow_logger:
            workflow_logger.log("Streamlit mode forced (force_check=True)", "INFO")
        logger.info("Streamlit mode forced (force_check=True)")
        return True
    
    # Method 1: Standard Streamlit runtime check
    try:
        import streamlit as st
        if hasattr(st.runtime, 'scriptrunner'):
            result = st.runtime.scriptrunner.is_streamlit_script_run_context()
            if result:
                if workflow_logger:
                    workflow_logger.log("Streamlit detected via method 1 (scriptrunner)", "INFO")
                logger.info("Streamlit detected via method 1 (scriptrunner)")
                return True
    except Exception as e:
        logger.debug(f"Streamlit detection method 1 failed: {e}")
    
    # Method 2: Check for streamlit in sys.modules and session_state
    try:
        import sys
        if 'streamlit' in sys.modules:
            import streamlit as st
            # Try accessing session_state
            try:
                _ = st.session_state
                if workflow_logger:
                    workflow_logger.log("Streamlit detected via method 2 (session_state)", "INFO")
                logger.info("Streamlit detected via method 2 (session_state)")
                return True
            except RuntimeError:
                # RuntimeError means we're not in script run context, but streamlit is loaded
                # This might still mean we're in Streamlit, just not in the right context
                pass
    except Exception as e:
        logger.debug(f"Streamlit detection method 2 failed: {e}")
    
    # Method 3: Check environment variable
    import os
    if os.environ.get('STREAMLIT_SERVER_PORT') or os.environ.get('STREAMLIT_SERVER_ADDRESS'):
        if workflow_logger:
            workflow_logger.log("Streamlit detected via method 3 (environment variable)", "INFO")
        logger.info("Streamlit detected via method 3 (environment variable)")
        return True
    
    logger.info("Streamlit not detected (all methods failed)")
    return False


def find_json_file(folder: Path) -> Optional[Path]:
    """Find the JSON config file in the folder."""
    json_files = list(folder.glob("*.json"))
    json_files = [f for f in json_files if f.name not in ("published_pins.json", UI_COORDS_FILE)]
    if not json_files:
        return None
    if len(json_files) == 1:
        return json_files[0]
    for f in json_files:
        if "coloring_book" in f.name.lower() or "book_config" in f.name.lower():
            return f
    return json_files[0]


class PinterestPublisher:
    """Publishes pins to Pinterest using robust element finding."""
    
    def __init__(
        self,
        folder_path: str,
        board_name: str,
        dry_run: bool = False,
        connect_existing: bool = False,
        force_streamlit_mode: bool = False,
    ):
        self.folder = Path(folder_path)
        self.board_name = board_name
        self.dry_run = dry_run
        self.connect_existing = connect_existing
        self.force_streamlit_mode = force_streamlit_mode
        
        # Find and load JSON config
        json_file = find_json_file(self.folder)
        if not json_file:
            raise FileNotFoundError(f"No JSON config file found in {folder_path}")
        
        logger.info(f"Loading config from: {json_file.name}")
        self.config = BookConfig.from_json_file(str(json_file), board_name)
        
        self.state_manager = StateManager(folder_path)
        
        self.playwright = None
        self.browser: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.cdp_browser = None
    
    def __enter__(self):
        if not self.dry_run:
            self._launch_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.dry_run:
            self._close_browser()
    
    def _launch_browser(self) -> None:
        """Launch or connect to Chromium-based browser (Chrome, Brave, Edge, etc.)."""
        if self.connect_existing:
            browser_name = BROWSER_TYPE.capitalize()
            logger.info(f"Connecting to existing {browser_name} on port {DEBUG_PORT}...")
            if workflow_logger:
                workflow_logger.log(f"Starting browser connection to {browser_name} on port {DEBUG_PORT}", "INFO")
            
            # Check if we're in Streamlit
            logger.info("Checking Streamlit context...")
            in_streamlit = _is_in_streamlit_context(force_check=self.force_streamlit_mode)
            
            logger.info(f"Streamlit detection result: {in_streamlit} (force_mode={self.force_streamlit_mode})")
            if workflow_logger:
                workflow_logger.log_action("streamlit_detection", {
                    "detected": in_streamlit,
                    "force_mode": self.force_streamlit_mode
                })
            
            if in_streamlit:
                logger.info("Using threaded Playwright initialization (Streamlit detected)")
                if workflow_logger:
                    workflow_logger.log("Using threaded Playwright path", "INFO")
                playwright_result = {}
                playwright_error = {}
                
                def run_playwright():
                    try:
                        # Create a completely new event loop in this thread
                        # On Windows, use ProactorEventLoop which supports subprocess creation
                        # This is critical - Streamlit's event loop doesn't support subprocess creation
                        logger.info("Thread: Creating new event loop...")
                        if workflow_logger:
                            workflow_logger.log("Thread: Creating new event loop to avoid Streamlit's event loop", "INFO")
                        
                        import sys
                        if sys.platform == 'win32':
                            # On Windows, ProactorEventLoop supports subprocess creation
                            new_loop = asyncio.ProactorEventLoop()
                            logger.info("Thread: Using ProactorEventLoop (Windows)")
                        else:
                            # On Unix, use default event loop
                            new_loop = asyncio.new_event_loop()
                            logger.info("Thread: Using new event loop (Unix)")
                        
                        asyncio.set_event_loop(new_loop)
                        
                        logger.info("Thread: Event loop set, starting Playwright...")
                        if workflow_logger:
                            workflow_logger.log("Thread: Event loop set, starting Playwright initialization", "INFO")
                        
                        playwright_result['playwright'] = sync_playwright().start()
                        playwright = playwright_result['playwright']
                        
                        # Try localhost first (works for both IPv4 and IPv6), fallback to 127.0.0.1
                        try:
                            logger.info(f"Thread: Connecting to browser via localhost:{DEBUG_PORT}")
                            cdp_browser = playwright.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")
                        except Exception as e1:
                            logger.info(f"Thread: localhost failed, trying 127.0.0.1:{DEBUG_PORT} - {e1}")
                            cdp_browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}")
                        
                        contexts = cdp_browser.contexts
                        logger.info(f"Thread: Found {len(contexts)} browser contexts")
                        if contexts:
                            browser = contexts[0]
                        else:
                            logger.info("Thread: No existing contexts, creating new context")
                            browser = cdp_browser.new_context()
                        
                        page = browser.new_page()
                        logger.info(f"Thread: Page created, URL: {page.url}")
                        if workflow_logger:
                            workflow_logger.log(f"Thread: Page created successfully, URL: {page.url}", "INFO")
                        
                        playwright_result['cdp_browser'] = cdp_browser
                        playwright_result['browser'] = browser
                        playwright_result['page'] = page
                        logger.info("Thread: Playwright initialization completed successfully")
                        if workflow_logger:
                            workflow_logger.log("Thread: Playwright initialization completed successfully", "INFO")
                    except Exception as e:
                        import traceback
                        error_trace = traceback.format_exc()
                        logger.error(f"Thread error: {e}\n{error_trace}")
                        if workflow_logger:
                            workflow_logger.log_error(e, "run_playwright_thread")
                        playwright_error['error'] = e
                        playwright_error['traceback'] = error_trace
                    finally:
                        # Note: We don't close the loop here because Playwright needs it to stay alive
                        # The loop will be cleaned up when the thread ends
                        pass
                
                thread = threading.Thread(target=run_playwright, daemon=False)
                thread.start()
                thread.join(timeout=30)  # 30 second timeout
                
                if thread.is_alive():
                    raise Exception(f"Timeout connecting to {browser_name}. Make sure it's running with --remote-debugging-port={DEBUG_PORT}")
                
                if 'error' in playwright_error:
                    error = playwright_error['error']
                    traceback_str = playwright_error.get('traceback', '')
                    logger.error(f"Thread failed to connect: {error}")
                    if traceback_str:
                        logger.error(f"Traceback: {traceback_str}")
                    if workflow_logger:
                        workflow_logger.log_error(error, "browser_connection_thread")
                    raise error
                
                if 'playwright' not in playwright_result:
                    error_msg = f"Failed to initialize Playwright connection to {browser_name}"
                    logger.error(error_msg)
                    if workflow_logger:
                        workflow_logger.log_error(Exception(error_msg), "browser_connection_thread")
                    raise Exception(error_msg)
                
                self.playwright = playwright_result['playwright']
                self.cdp_browser = playwright_result['cdp_browser']
                self.browser = playwright_result['browser']
                self.page = playwright_result['page']
                
                # Verify page is valid
                if self.page:
                    page_url = self.page.url
                    logger.info(f"Connected to existing {browser_name}! Page URL: {page_url}")
                    if workflow_logger:
                        workflow_logger.log(f"Browser connected successfully. Page URL: {page_url}", "INFO")
                else:
                    logger.warning("Page object is None after connection")
                    if workflow_logger:
                        workflow_logger.log("WARNING: Page object is None after connection", "WARNING")
                
                return
            else:
                # Normal execution (not in Streamlit)
                logger.info("Using direct Playwright initialization (not in Streamlit)")
                if workflow_logger:
                    workflow_logger.log("Using direct Playwright path (not in Streamlit)", "INFO")
                self.playwright = sync_playwright().start()
                try:
                    # Try localhost first (works for both IPv4 and IPv6), fallback to 127.0.0.1
                    try:
                        self.cdp_browser = self.playwright.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")
                    except:
                        self.cdp_browser = self.playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}")
                    contexts = self.cdp_browser.contexts
                    if contexts:
                        self.browser = contexts[0]
                    self.page = self.browser.new_page()
                    page_url = self.page.url if self.page else "unknown"
                    logger.info(f"Connected to existing {browser_name}! Page URL: {page_url}")
                    if workflow_logger:
                        workflow_logger.log(f"Browser connected (direct path). Page URL: {page_url}", "INFO")
                    return
                except Exception as e:
                    logger.error(f"Failed to connect: {e}")
                    if workflow_logger:
                        workflow_logger.log_error(e, "browser_connection_direct")
                    raise
        
        raise Exception("Please use --connect mode with an existing browser window")
    
    def _close_browser(self) -> None:
        """Close browser."""
        if self.page and self.connect_existing:
            try:
                self.page.close()
            except:
                pass
        if self.cdp_browser:
            self.cdp_browser.close()
        elif self.browser and not self.connect_existing:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser closed")
    
    def get_images(self) -> list[ImageInfo]:
        """Get list of images in folder."""
        seen_paths = set()
        images = []
        for ext in SUPPORTED_EXTENSIONS:
            for path in self.folder.glob(f"*{ext}"):
                path_lower = str(path).lower()
                if path_lower not in seen_paths and "calibration" not in path.name.lower():
                    seen_paths.add(path_lower)
                    images.append(ImageInfo.from_path(str(path)))
        images.sort(key=lambda x: x.filename.lower())
        return images
    
    def publish_all(self) -> dict:
        """
        Publish all unpublished images.
        
        Returns:
            dict with keys: total, successful, failed, errors
        """
        all_images = self.get_images()
        total = len(all_images)
        logger.info(f"Found {total} images")
        
        unpublished = [
            img for img in all_images 
            if not self.state_manager.is_published(img.filename)
        ]
        logger.info(f"{len(unpublished)} images to publish")
        
        if not unpublished:
            logger.info("No new images to publish!")
            return {
                "total": total,
                "successful": 0,
                "failed": 0,
                "errors": []
            }
        
        if self.dry_run:
            for img in unpublished:
                content = generate_pin_content(img.keywords, self.config)
                logger.info(f"[DRY RUN] {img.filename}: {content.title}")
            return {
                "total": total,
                "successful": len(unpublished),
                "failed": 0,
                "errors": []
            }
        
        results = {"successful": 0, "failed": 0, "errors": []}
        
        for i, image_info in enumerate(unpublished):
            logger.info(f"PIN {i+1}/{len(unpublished)}: {image_info.filename}")
            
            try:
                success = self._publish_single_pin(image_info)
                if success:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                error_msg = f"{image_info.filename}: {str(e)}"
                logger.error(f"Error: {error_msg}")
                self.state_manager.record_failure(image_info.filename, str(e))
                results["failed"] += 1
                results["errors"].append(error_msg)
            
            if i < len(unpublished) - 1:
                logger.info(f"Waiting {DELAY_BETWEEN_PINS} seconds...")
                self.page.wait_for_timeout(DELAY_BETWEEN_PINS * 1000)
        
        results["total"] = total
        return results
    
    def _publish_single_pin(self, image_info: ImageInfo) -> bool:
        """Publish a single pin using robust element finding."""
        
        # Generate title
        content = generate_pin_content(image_info.keywords, self.config)
        logger.info(f"Generated title: {content.title[:50]}...")
        
        # Step 1: Navigate to pin-builder
        logger.info("Step 1: Navigate to pin-builder")
        if workflow_logger:
            workflow_logger.log(f"Navigating to pin-builder: {PIN_BUILDER_URL}", "INFO")
        self.page.goto(PIN_BUILDER_URL)
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(2000)
        
        # Verify navigation succeeded
        current_url = self.page.url
        page_title = self.page.title()
        logger.info(f"Navigation complete. URL: {current_url}, Title: {page_title}")
        if workflow_logger:
            workflow_logger.log(f"Navigation to pin-builder complete. URL: {current_url}, Title: {page_title}", "INFO")
        
        # Step 2: Upload image
        logger.info("Step 2: Upload image")
        file_input = self.page.locator('input[type="file"]').first
        file_input.set_input_files(image_info.path)
        self.page.wait_for_timeout(3000)
        
        # Step 3: Fill title
        logger.info("Step 3: Fill title")
        self._fill_title(content.title[:100])
        
        # Step 4: Fill description
        logger.info("Step 4: Fill description")
        # Limit to 600 characters to avoid bugs
        description = self.config.description[:600] if len(self.config.description) > 600 else self.config.description
        self._fill_description(description)
        
        # Wait for Pinterest to process the description before proceeding
        logger.info(f"Waiting {DESCRIPTION_PROCESSING_DELAY}ms for description to be processed...")
        self.page.wait_for_timeout(DESCRIPTION_PROCESSING_DELAY)
        
        # Step 5: Select board (if not already selected)
        logger.info("Step 5: Check/Select board")
        self._ensure_board_selected()
        
        # Step 6: Click Publish
        logger.info("Step 6: Publish")
        self._click_publish()
        
        # Step 7: Handle post-publish
        logger.info("Step 7: Close popup")
        self._close_popup()
        
        # Record success
        self.state_manager.record_success(image_info.filename, content.title)
        logger.info(f"SUCCESS: {image_info.filename}")
        
        return True
    
    def _fill_title(self, title: str) -> None:
        """Fill the title field using multiple strategies."""
        
        # Strategy 1: Find any textarea or input (MOST RELIABLE - moved to first based on terminal logs)
        try:
            inputs = self.page.locator('textarea, input[type="text"]').first
            if inputs.is_visible(timeout=500):
                inputs.click()
                self.page.wait_for_timeout(100)
                inputs.fill(title)
                logger.info("Title filled via input/textarea")
                return
        except Exception as e:
            logger.debug(f"Strategy 1 failed: {e}")
        
        # Strategy 2: Find by visible placeholder text
        try:
            title_area = self.page.get_by_text("Add your title", exact=False).first
            if title_area.is_visible(timeout=500):
                # Find the actual input/textarea near the text
                input_field = title_area.locator('..').locator('textarea, input[type="text"]').first
                if input_field.is_visible(timeout=500):
                    input_field.click()
                    self.page.wait_for_timeout(100)
                    input_field.fill(title)
                    logger.info("Title filled via text locator")
                    return
        except Exception as e:
            logger.debug(f"Strategy 2 failed: {e}")
        
        # Strategy 3: Find contenteditable div (fallback - can be unreliable as it may find description field)
        try:
            editors = self.page.locator('[contenteditable="true"]').first
            if editors.is_visible(timeout=500):
                editors.click()
                self.page.wait_for_timeout(100)
                # For contenteditable, use evaluate to set text directly (more reliable than fill)
                editors.evaluate(f"element => {{ element.textContent = ''; element.textContent = {json.dumps(title)}; }}")
                # Trigger input event to notify Pinterest
                editors.evaluate("element => element.dispatchEvent(new Event('input', { bubbles: true }))")
                logger.info("Title filled via contenteditable")
                return
        except Exception as e:
            logger.debug(f"Strategy 3 failed: {e}")
        
        logger.warning("Could not find title field with any strategy")
    
    def _fill_description(self, description: str) -> None:
        """Fill the description field using keyboard.type (reverted for reliability)."""
        
        # Limit description to 600 characters to avoid bugs
        if len(description) > 600:
            description = description[:600]
            logger.info(f"Description truncated to 600 characters")
        
        # Strategy 1: Find by visible text
        try:
            desc_area = self.page.get_by_text("Tell everyone what your Pin is about", exact=False).first
            if desc_area.is_visible(timeout=500):
                desc_area.click()
                self.page.wait_for_timeout(300)
                self.page.keyboard.type(description, delay=10)
                logger.info("Description filled via text locator")
                return
        except Exception as e:
            logger.debug(f"Strategy 1 failed: {e}")
        
        # Strategy 2: Use Tab from title to get to description
        try:
            self.page.keyboard.press("Tab")
            self.page.wait_for_timeout(300)
            self.page.keyboard.type(description, delay=10)
            logger.info("Description filled via Tab navigation")
            return
        except Exception as e:
            logger.debug(f"Strategy 2 failed: {e}")
        
        # Strategy 3: Find second contenteditable
        try:
            desc_editor = self.page.locator('[contenteditable="true"]').nth(1)
            if desc_editor.is_visible(timeout=500):
                desc_editor.click()
                self.page.wait_for_timeout(300)
                self.page.keyboard.type(description, delay=10)
                logger.info("Description filled via second contenteditable")
                return
        except Exception as e:
            logger.debug(f"Strategy 3 failed: {e}")
        
        logger.warning("Could not find description field with any strategy")
    
    def _ensure_board_selected(self) -> None:
        """Make sure a board is selected, select one if not."""
        
        # Check if board is already selected (look for board name or dropdown showing selection)
        try:
            # If the board name is visible, it's already selected
            board_visible = self.page.get_by_text(self.board_name, exact=False)
            if board_visible.count() > 0:
                logger.info(f"Board '{self.board_name}' already visible/selected")
                return
        except:
            pass
        
        # Try to open board selector
        try:
            # Look for dropdown button
            selectors_to_try = [
                'button:has-text("Select")',
                '[data-test-id="board-dropdown"]',
                '[aria-label*="board" i]',
                'button:has-text("Choose")',
            ]
            
            for selector in selectors_to_try:
                try:
                    dropdown = self.page.locator(selector).first
                    if dropdown.is_visible(timeout=1000):
                        dropdown.click()
                        self.page.wait_for_timeout(1000)
                        break
                except:
                    continue
            
            # Now search/select the board
            # Try to find search input
            try:
                search = self.page.locator('input[type="text"], input[placeholder*="Search" i]').first
                if search.is_visible(timeout=1000):
                    search.fill(self.board_name)
                    self.page.wait_for_timeout(1000)
            except:
                pass
            
            # Click on board option
            board_option = self.page.get_by_text(self.board_name, exact=False).first
            board_option.click(timeout=3000)
            logger.info(f"Selected board: {self.board_name}")
            self.page.wait_for_timeout(500)
            
        except Exception as e:
            logger.warning(f"Board selection issue: {e}")
    
    def _click_publish(self) -> None:
        """Click the Publish button."""
        
        selectors_to_try = [
            'button:has-text("Publish")',
            '[data-test-id*="publish" i]',
            'button[type="submit"]',
        ]
        
        for selector in selectors_to_try:
            try:
                btn = self.page.locator(selector).first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    logger.info(f"Clicked publish via: {selector}")
                    self.page.wait_for_timeout(3000)
                    return
            except:
                continue
        
        # Last resort: find by role
        try:
            publish_btn = self.page.get_by_role("button", name="Publish")
            publish_btn.click(timeout=2000)
            logger.info("Clicked publish via role")
            self.page.wait_for_timeout(3000)
            return
        except:
            pass
        
        raise Exception("Could not find Publish button")
    
    def _close_popup(self) -> None:
        """Close any popup after publishing."""
        self.page.wait_for_timeout(2000)
        
        # Try multiple methods to close popup
        
        # Method 1: Press Escape
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(500)
        
        # Method 2: Click any close button
        try:
            close_btns = self.page.locator('button[aria-label*="close" i], button[aria-label*="dismiss" i], [data-test-id*="close"]')
            if close_btns.count() > 0:
                close_btns.first.click()
                self.page.wait_for_timeout(500)
        except:
            pass
        
        # Method 3: Click outside modal
        try:
            self.page.mouse.click(10, 10)
            self.page.wait_for_timeout(500)
        except:
            pass


def publish_pins(
    folder_path: str,
    board_name: str,
    headless: bool = False,
    dry_run: bool = False,
    connect_existing: bool = False,
) -> dict:
    """Main entry point."""
    logger.info(f"Publishing pins from: {folder_path}")
    logger.info(f"Board: {board_name}")
    
    with PinterestPublisher(folder_path, board_name, dry_run, connect_existing) as publisher:
        return publisher.publish_all()
