import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Any

from playwright.sync_api import sync_playwright

from . import config
# Use design_v2 (coordinate-based with fallbacks) - more robust
from .tools.design_v2 import create_design
from .tools.place import place_image_with_outline
from .tools.upload import upload_and_place_single_image
from .utils import _find_images


logger = logging.getLogger(__name__)


@dataclass
class CanvaPublisher:
    page_size: Tuple[float, float]
    page_count: int
    margin_percent: float
    outline_height_percent: float
    blank_between: bool
    headless: bool
    dry_run: bool
    connect_existing: bool
    remote_debug_url: str
    chrome_user_data_dir: Path | None = None
    chrome_profile: str | None = None
    cloudflare_mode: str = "auto"  # "auto" or "manual"
    
    def __post_init__(self):
        """Initialize instance variables for browser lifecycle."""
        # Instance variables for browser lifecycle (set by __enter__ / _launch_browser)
        self.playwright = None
        self.browser = None  # BrowserContext from launch_persistent_context or CDP
        self.page = None
        self.temp_profile_dir: str | None = None
        self.cdp_browser = None  # For connect_existing mode

    def __enter__(self):
        """Context manager entry - launch browser."""
        if not self.dry_run:
            self._launch_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close browser."""
        if not self.dry_run:
            self._close_browser()
    
    def _launch_browser(self) -> None:
        """Launch or connect to browser (Brave/Chrome/Edge) - same approach as Pinterest agent."""
        self.playwright = sync_playwright().start()
        
        # MODE 1: Connect to existing browser (exactly like Pinterest agent)
        if self.connect_existing:
            browser_name = config.BROWSER_TYPE.capitalize()
            logger.info(f"Connecting to existing {browser_name} on port {config.DEBUG_PORT}...")
            try:
                # Exact same pattern as Pinterest agent
                # Try localhost first (works for both IPv4 and IPv6), fallback to 127.0.0.1
                try:
                    self.cdp_browser = self.playwright.chromium.connect_over_cdp(f"http://localhost:{config.DEBUG_PORT}")
                except:
                    self.cdp_browser = self.playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{config.DEBUG_PORT}")
                contexts = self.cdp_browser.contexts
                if contexts:
                    self.browser = contexts[0]
                self.page = self.browser.new_page()
                logger.info(f"Connected to existing {browser_name}!")
                return
            except Exception as e:
                logger.error(f"Failed to connect: {e}")
                logger.error("")
                logger.error(f"Make sure {browser_name} is running with: --remote-debugging-port={config.DEBUG_PORT}")
                logger.error("")
                browser_path = config.get_browser_path()
                user_data_dir = config.get_browser_user_data_dir()
                logger.error(f"Start {browser_name} with:")
                logger.error(f'  & "{browser_path}" --remote-debugging-port={config.DEBUG_PORT} --user-data-dir="{user_data_dir}" --profile-directory={config.BROWSER_PROFILE}')
                logger.error("")
                logger.error("Or use the helper command:")
                logger.error(f"  {config.get_browser_startup_command()}")
                logger.error("")
                raise
        
        # MODE 2: Launch new browser with profile (fallback mode - not recommended)
        browser_name = config.BROWSER_TYPE.capitalize()
        logger.info(f"Launching {browser_name} with user profile...")
        logger.info(f"User data dir: {self.chrome_user_data_dir}")
        logger.info(f"Profile: {self.chrome_profile}")
        
        # Get browser executable path
        browser_path = config.get_browser_path()
        
        # Map browser type to Playwright channel (for built-in browsers)
        # For Brave and custom browsers, use executable_path instead
        channel_map = {
            "chrome": "chrome",
            "edge": "msedge",
            "chromium": None,  # Use executable_path
            "brave": None,  # Use executable_path
        }
        channel = channel_map.get(config.BROWSER_TYPE)
        executable_path = browser_path if channel is None else None
        
        # First, try to launch with the original profile
        try:
            launch_args = [f"--profile-directory={self.chrome_profile}"] if self.chrome_profile else []
            launch_args.extend([
                "--start-maximized",  # Maximize window on launch
                "--window-size=1920,1080",  # Set initial window size
            ])
            
            launch_kwargs = {
                "user_data_dir": str(self.chrome_user_data_dir),
                "headless": self.headless,
                "args": launch_args,
                "viewport": None,  # Use no_viewport to allow actual window sizing
                "timeout": 30000,
            }
            
            if channel:
                launch_kwargs["channel"] = channel
            else:
                launch_kwargs["executable_path"] = executable_path
            
            self.browser = self.playwright.chromium.launch_persistent_context(**launch_kwargs)
        except Exception as e:
            error_msg = str(e)
            if "Target page, context or browser has been closed" in error_msg or "exitCode=21" in error_msg:
                logger.warning("Direct profile access failed. Trying with copied profile...")
                
                # Copy the profile to a temp location
                original_profile = self.chrome_user_data_dir / self.chrome_profile
                browser_prefix = config.BROWSER_TYPE.lower()
                self.temp_profile_dir = tempfile.mkdtemp(prefix=f"canva_{browser_prefix}_")
                temp_profile = Path(self.temp_profile_dir) / self.chrome_profile
                
                logger.info(f"Copying profile to: {self.temp_profile_dir}")
                
                # Copy essential files (cookies, local storage for login)
                temp_profile.mkdir(parents=True, exist_ok=True)
                essential_files = [
                    "Cookies", "Cookies-journal",
                    "Login Data", "Login Data-journal", 
                    "Web Data", "Web Data-journal",
                    "Preferences", "Secure Preferences",
                ]
                essential_dirs = ["Local Storage", "Session Storage", "IndexedDB"]
                
                for filename in essential_files:
                    src = original_profile / filename
                    if src.exists():
                        shutil.copy2(src, temp_profile / filename)
                
                for dirname in essential_dirs:
                    src = original_profile / dirname
                    if src.exists():
                        shutil.copytree(src, temp_profile / dirname, dirs_exist_ok=True)
                
                # Try again with copied profile
                launch_args = [f"--profile-directory={self.chrome_profile}"] if self.chrome_profile else []
                launch_args.extend([
                    "--start-maximized",  # Maximize window on launch
                    "--window-size=1920,1080",  # Set initial window size
                ])
                
                launch_kwargs = {
                    "user_data_dir": self.temp_profile_dir,
                    "headless": self.headless,
                    "args": launch_args,
                    "viewport": None,  # Use no_viewport to allow actual window sizing
                    "timeout": 30000,
                }
                
                if channel:
                    launch_kwargs["channel"] = channel
                else:
                    launch_kwargs["executable_path"] = executable_path
                
                self.browser = self.playwright.chromium.launch_persistent_context(**launch_kwargs)
            else:
                raise
        
        # Use existing page or create new one
        if self.browser.pages:
            self.page = self.browser.pages[0]
        else:
            self.page = self.browser.new_page()
        
        logger.info("Browser launched successfully")
    
    def _close_browser(self) -> None:
        """Close browser and cleanup."""
        # Close page if we created it
        if self.page and self.connect_existing:
            try:
                self.page.close()
            except:
                pass
        
        # For CDP connection, don't close the browser (user's session)
        if self.cdp_browser:
            self.cdp_browser.close()
        elif self.browser and not self.connect_existing:
            self.browser.close()
        
        if self.playwright:
            self.playwright.stop()
        
        # Clean up temp profile directory if created
        if self.temp_profile_dir and Path(self.temp_profile_dir).exists():
            try:
                shutil.rmtree(self.temp_profile_dir)
                logger.debug(f"Cleaned up temp profile: {self.temp_profile_dir}")
            except Exception as e:
                logger.warning(f"Could not clean up temp profile: {e}")
        
        logger.info("Browser closed")
    
    def run(self, folder: Path) -> Dict[str, int]:
        # Initialize output tracking
        start_time = datetime.now(timezone.utc)
        output_data: Dict[str, Any] = {
            "agent": "canva_agent",
            "version": "1.0.0",
            "timestamp": {
                "start": start_time.isoformat(),
            },
            "input": {
                "folder": str(folder),
                "page_size": {"width_in": self.page_size[0], "height_in": self.page_size[1]},
                "page_count": self.page_count,
                "margin_percent": self.margin_percent,
                "outline_height_percent": self.outline_height_percent,
                "blank_between": self.blank_between,
                "browser_type": config.BROWSER_TYPE,
                "connect_existing": self.connect_existing,
            },
            "design": {},
            "images": [],
            "summary": {},
            "errors": [],
        }
        
        images = _find_images(folder)
        total = len(images)
        logger.info("Found %d images", total)
        # Log image names for debugging
        for i, img in enumerate(images, 1):
            logger.info(f"  {i}. {img.name}")

        if self.dry_run:
            logger.info("Dry run enabled; skipping browser automation.")
            end_time = datetime.now(timezone.utc)
            output_data["timestamp"]["end"] = end_time.isoformat()
            output_data["timestamp"]["duration_seconds"] = (end_time - start_time).total_seconds()
            output_data["summary"] = {"total_images": total, "successful": total, "failed": 0}
            self._write_output_json(folder, output_data)
            return {"total": total, "successful": total, "failed": 0}

        # Browser should already be launched via __enter__ / _launch_browser
        # Maximize the browser window
        try:
            # Get screen dimensions and maximize
            screen_size = self.page.evaluate("""() => {
                return {
                    width: window.screen.availWidth,
                    height: window.screen.availHeight
                };
            }""")
            self.page.set_viewport_size({"width": screen_size["width"], "height": screen_size["height"]})
            # Also try to maximize the window itself
            self.page.evaluate("window.moveTo(0, 0); window.resizeTo(screen.availWidth, screen.availHeight);")
        except Exception as e:
            logger.warning(f"Could not maximize window: {e}")
            # Fallback to large viewport
            self.page.set_viewport_size({"width": 1920, "height": 1080})
        
        # Navigate to Canva
        logger.info("Navigating to Canva...")
        self.page.goto("https://www.canva.com/")
        self.page.wait_for_load_state("networkidle", timeout=30000)
        
        # When connecting to existing browser, assume already logged in (same as Pinterest agent)
        # The new page inherits cookies from the existing browser session
        if self.connect_existing:
            browser_name = config.BROWSER_TYPE.capitalize()
            logger.info(f"Connected to existing {browser_name} - assuming already logged in (cookies preserved)")
            # Still check to be safe, but don't try to sign in
            if not self._is_already_logged_in():
                logger.warning(f"Not logged in detected, but using existing {browser_name} session.")
                logger.warning(f"If you need to sign in, do it manually in the {browser_name} window before running the agent.")
        else:
            # Only check and sign in when launching new browser
            if self._is_already_logged_in():
                logger.info("Already logged into Canva - skipping sign in flow")
            else:
                # Only try to sign in if we're not already logged in
                logger.info("Not logged in - attempting sign in...")
                self._handle_sign_in()

        # Step 1: Create design with 1 page (pages will be added dynamically)
        logger.info("Creating design with 1 page (pages will be added as images are placed)...")
        design_created_at = datetime.now(timezone.utc)
        create_design(self.page, self.page_size[0], self.page_size[1], page_count=1)
        
        # Wait for design to be created and new tab to open
        logger.info("Waiting for design editor to open in new tab...")
        self.page.wait_for_timeout(5000)  # Give time for new tab to open
        
        # Step 1.5: Switch to the new tab with the design editor
        logger.info("Switching to design editor tab...")
        all_pages = self.browser.pages
        logger.info(f"Found {len(all_pages)} tab(s)")
        
        # Find the new tab (usually the last one, or one with design editor URL)
        design_page = None
        design_url = None
        design_id = None
        for page in all_pages:
            try:
                url = page.url
                # Check if this is the design editor (usually contains /design/ or /editor/)
                if "/design/" in url or "/editor/" in url or "canva.com/design" in url:
                    design_page = page
                    design_url = url
                    logger.info(f"Found design editor tab: {url}")
                    # Extract design ID from URL (format: /design/DESIGN_ID/...)
                    try:
                        parts = url.split("/design/")
                        if len(parts) > 1:
                            design_id = parts[1].split("/")[0]
                    except:
                        pass
                    break
            except:
                continue
        
        # If no design editor found by URL, use the last opened tab
        if not design_page and len(all_pages) > 1:
            design_page = all_pages[-1]  # Last tab is usually the new one
            design_url = design_page.url
            logger.info(f"Using last tab (assuming it's the design editor): {design_url}")
        elif not design_page:
            design_page = self.page  # Fallback to current page
            design_url = self.page.url
            logger.warning("No new tab found, using current page")
        
        # Switch to the design editor tab
        if design_page != self.page:
            self.page = design_page
            self.page.bring_to_front()
            logger.info("✅ Switched to design editor tab")
        
        # Wait for design editor to fully load
        logger.info("Waiting for design editor to fully load...")
        try:
            # Wait for network to be idle (page fully loaded)
            self.page.wait_for_load_state("networkidle", timeout=10000)
        except:
            # If networkidle times out, just wait a bit
            pass
        self.page.wait_for_timeout(3000)  # Additional wait for UI to stabilize
        
        # Store design information in output
        output_data["design"] = {
            "url": design_url or "",
            "design_id": design_id or "",
            "created_at": design_created_at.isoformat(),
            "total_pages": 1,  # Will be updated as pages are added
        }
        
        # Take screenshot to show the current state
        try:
            screenshot_path = "canva_after_design_creation.png"
            self.page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"✅ Screenshot saved: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not take screenshot: {e}")
        
        # Additional wait after screenshot to ensure UI is stable
        # Sometimes Canva shows template suggestions or overlays that need to settle
        logger.info("Waiting for UI to stabilize after design creation...")
        self.page.wait_for_timeout(2000)  # Additional wait for any overlays to appear/disappear
        
        # Try to dismiss any template suggestions or overlays that might appear
        # Common selectors for "Skip" or "Start from scratch" buttons
        overlay_dismissed = False
        try:
            dismiss_selectors = [
                'button:has-text("Skip")',
                'button:has-text("Start from scratch")',
                'button:has-text("Blank")',
                'button:has-text("Start blank")',
                '[data-testid*="skip"]',
                '[aria-label*="Skip" i]',
                '[aria-label*="Start from scratch" i]',
                'button[aria-label*="Close" i]',
                'button[aria-label*="Dismiss" i]',
            ]
            for selector in dismiss_selectors:
                try:
                    dismiss_btn = self.page.locator(selector).first
                    if dismiss_btn.is_visible(timeout=1000):
                        dismiss_btn.click()
                        logger.info(f"✅ Dismissed overlay/template suggestion using: {selector}")
                        self.page.wait_for_timeout(1500)  # Wait after dismissing
                        overlay_dismissed = True
                        break
                except:
                    continue
        except Exception as e:
            logger.debug(f"Error checking for overlay: {e}")
        
        # If no overlay was found, click on the canvas to ensure focus and dismiss any potential overlays
        if not overlay_dismissed:
            try:
                # Click on a safe area of the canvas (center) to ensure focus
                # This helps dismiss any overlays that might be blocking interactions
                canvas_clicked = False
                canvas_selectors = [
                    '[data-testid*="canvas"]',
                    '[class*="canvas"]',
                    'div[role="main"]',
                ]
                for selector in canvas_selectors:
                    try:
                        canvas = self.page.locator(selector).first
                        if canvas.is_visible(timeout=1000):
                            # Click in the center of the canvas
                            box = canvas.bounding_box()
                            if box:
                                x = box["x"] + box["width"] / 2
                                y = box["y"] + box["height"] / 2
                                self.page.mouse.click(x, y)
                                logger.info("✅ Clicked on canvas to ensure focus")
                                self.page.wait_for_timeout(1000)
                                canvas_clicked = True
                                break
                    except:
                        continue
                
                # Fallback: Click in center of viewport if canvas not found
                if not canvas_clicked:
                    viewport = self.page.viewport_size
                    if viewport:
                        self.page.mouse.click(viewport["width"] / 2, viewport["height"] / 2)
                        logger.info("✅ Clicked center of viewport to ensure focus")
                        self.page.wait_for_timeout(1000)
            except Exception as e:
                logger.debug(f"Could not click canvas: {e}")
        
        # Final wait to ensure everything is stable before starting uploads
        self.page.wait_for_timeout(1000)

        # Step 2: Process images one by one - upload, place, add blank page
        logger.info(f"Step 2: Processing {len(images)} images one by one...")
        success = 0
        failed = 0
        current_page_index = 0  # Start with page 0 (first page)
        blank_pages_added = 0
        
        for i, img in enumerate(images):
            image_data: Dict[str, Any] = {
                "index": i,
                "filename": img.name,
                "path": str(img),
                "status": "pending",
                "page_number": current_page_index + 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "steps": [],
            }
            
            try:
                logger.info(f"Processing image {i+1}/{len(images)}: {img.name}")
                
                # Ensure page exists (create if needed). No thumbnail clicks - they cause miss-clicks.
                self._ensure_page_exists(current_page_index, i)
                
                # Upload and place the image (clicks Uploads button each time for safety)
                logger.info(f"Uploading and placing {img.name}...")
                upload_start = datetime.now(timezone.utc)
                upload_and_place_single_image(self.page, img)
                upload_end = datetime.now(timezone.utc)
                logger.info(f"✅ Uploaded and placed {img.name} on page {current_page_index + 1}")
                
                # Track successful steps
                image_data["steps"].append({
                    "step": "upload",
                    "timestamp": upload_start.isoformat(),
                    "status": "success",
                })
                image_data["steps"].append({
                    "step": "place",
                    "timestamp": upload_end.isoformat(),
                    "status": "success",
                })
                image_data["status"] = "success"
                success += 1
                
                # Add blank page after image (if not the last image and blank_between is enabled)
                if self.blank_between and i < len(images) - 1:
                    logger.info("Adding blank page after image...")
                    self._add_page()
                    blank_pages_added += 1
                    # After adding a page, the next image should go on the page after the blank one
                    # So we skip 2 pages: current (with image) + blank page = next image on page after blank
                    current_page_index += 2
                else:
                    # Move to next page for next image
                    current_page_index += 1
                    
            except Exception as exc:
                error_msg = str(exc)
                logger.error("Failed processing %s: %s", img.name, exc)
                image_data["status"] = "failed"
                image_data["error"] = error_msg
                image_data["steps"].append({
                    "step": "upload",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "failed",
                    "error": error_msg,
                })
                output_data["errors"].append({
                    "image": img.name,
                    "error": error_msg,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                failed += 1
                # Still increment page index to continue
                if self.blank_between and i < len(images) - 1:
                    current_page_index += 2
                else:
                    current_page_index += 1
            
            output_data["images"].append(image_data)

        # Update design total pages
        output_data["design"]["total_pages"] = current_page_index + 1
        
        # Finalize output
        end_time = datetime.now(timezone.utc)
        output_data["timestamp"]["end"] = end_time.isoformat()
        output_data["timestamp"]["duration_seconds"] = (end_time - start_time).total_seconds()
        output_data["summary"] = {
            "total_images": total,
            "successful": success,
            "failed": failed,
            "total_pages_created": current_page_index + 1,
            "blank_pages_added": blank_pages_added,
        }
        
        # Write output JSON
        self._write_output_json(folder, output_data)
        
        logger.info(f"Completed! Processed {success} images successfully, {failed} failed")
        return {"total": total, "successful": success, "failed": failed}

    def _is_already_logged_in(self) -> bool:
        """Check if user is already logged into Canva."""
        logger.info("Checking if already logged into Canva...")
        
        # Wait a bit for page to fully render
        self.page.wait_for_timeout(2000)
        
        # Check 1: Look for user menu/avatar/profile indicators
        try:
            user_indicators = [
                '[data-testid="user-menu"]',
                '[aria-label*="Account" i]',
                'button:has-text("Profile")',
                'img[alt*="Profile"]',
                'div[class*="avatar"]',
                'button[class*="user"]',
                '[data-testid*="avatar"]',
                'div[class*="profile"]',
            ]
            for indicator in user_indicators:
                try:
                    element = self.page.locator(indicator).first
                    if element.is_visible(timeout=2000):
                        logger.info(f"Logged in detected via: {indicator}")
                        return True
                except:
                    continue
        except:
            pass
        
        # Check 2: Look for Canva dashboard/homepage elements (only visible when logged in)
        try:
            dashboard_indicators = [
                'text=Create a design',
                'text=Templates',
                '[data-testid*="design"]',
                'button:has-text("Create")',
                'a[href*="/templates"]',
                'div[class*="homepage"]',
                'div[class*="dashboard"]',
            ]
            for indicator in dashboard_indicators:
                try:
                    element = self.page.locator(indicator).first
                    if element.is_visible(timeout=2000):
                        logger.info(f"Logged in detected via dashboard element: {indicator}")
                        return True
                except:
                    continue
        except:
            pass
        
        # Check 3: URL-based check - if we're NOT on login/signup, we might be logged in
        current_url = self.page.url
        if "canva.com" in current_url:
            if "/login" in current_url or "/signup" in current_url or "/sign-in" in current_url:
                logger.info("On login/signup page - not logged in")
                return False
            # If we're on canva.com but not login page, check for sign-in button
            try:
                sign_in_button = self.page.locator('button:has-text("Sign in"), a:has-text("Sign in"), button:has-text("Log in")').first
                if sign_in_button.is_visible(timeout=2000):
                    logger.info("Sign in button visible - not logged in")
                    return False
            except:
                pass
        
        # Check 4: Look for cookies/localStorage that indicate login
        try:
            cookies = self.page.context.cookies()
            for cookie in cookies:
                if "canva" in cookie.get("name", "").lower() and ("session" in cookie.get("name", "").lower() or "auth" in cookie.get("name", "").lower()):
                    logger.info("Found Canva session cookie - likely logged in")
                    return True
        except:
            pass
        
        logger.info("Could not confirm login status - will attempt sign in")
        return False
    
    def _handle_sign_in(self) -> None:
        """Check for sign in button, click Continue with Google, and handle Cloudflare verification."""
        logger.info("Proceeding with sign in flow...")
        
        # Try multiple selectors for sign in button
        sign_in_selectors = [
            'button:has-text("Sign in")',
            'a:has-text("Sign in")',
            'button:has-text("Log in")',
            'a:has-text("Log in")',
            '[data-testid="sign-in-button"]',
            '[data-testid="login-button"]',
            'button[aria-label*="Sign in" i]',
            'a[href*="login" i]',
            'a[href*="signin" i]',
        ]
        
        sign_in_clicked = False
        for selector in sign_in_selectors:
            try:
                sign_in_button = self.page.locator(selector).first
                if sign_in_button.is_visible(timeout=3000):
                    logger.info(f"Found sign in button with selector: {selector}")
                    sign_in_button.click()
                    self.page.wait_for_timeout(2000)
                    logger.info("Clicked sign in button")
                    sign_in_clicked = True
                    break
            except:
                continue
        
        if not sign_in_clicked:
            logger.info("No sign in button found - may already be logged in or page structure changed")
            return
        
        # Wait a bit for login page to load
        self.page.wait_for_timeout(2000)
        
        # Look for and click "Continue with Google" button
        logger.info("Looking for 'Continue with Google' button...")
        google_button_selectors = [
            'button:has-text("Continue with Google")',
            'button:has-text("Sign in with Google")',
            'button:has-text("Google")',
            '[data-testid="google-signin"]',
            'button[aria-label*="Google" i]',
            'a:has-text("Continue with Google")',
            'a:has-text("Sign in with Google")',
        ]
        
        google_clicked = False
        for selector in google_button_selectors:
            try:
                google_button = self.page.locator(selector).first
                if google_button.is_visible(timeout=5000):
                    logger.info(f"Found Google button with selector: {selector}")
                    google_button.click()
                    self.page.wait_for_timeout(3000)
                    logger.info("Clicked Continue with Google button")
                    google_clicked = True
                    break
            except:
                continue
        
        if not google_clicked:
            logger.warning("Could not find 'Continue with Google' button")
            return
        
        # Handle popup window if it appears (Google OAuth or Cloudflare)
        logger.info("Waiting for popup window to appear...")
        self.page.wait_for_timeout(3000)
        
        # Wait for popup with retries
        popup = None
        for attempt in range(5):
            all_pages = self.browser.pages
            logger.info(f"Checking for popup (attempt {attempt + 1}/5). Current pages: {len(all_pages)}")
            
            if len(all_pages) > 1:
                # Find the popup (not the original page)
                for p in all_pages:
                    if p != self.page:
                        popup = p
                        logger.info(f"Found popup window: {popup.url}")
                        break
                if popup:
                    break
            
            self.page.wait_for_timeout(2000)
        
        if popup:
            logger.info("Switching to popup window...")
            popup.bring_to_front()
            original_page = self.page
            self.page = popup
            
            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                logger.info(f"Popup loaded. URL: {self.page.url}")
            except:
                logger.warning("Popup load timeout, continuing anyway...")
        else:
            logger.info("No popup detected, Cloudflare might be on main page")
        
        # Handle Cloudflare verification - try multiple approaches
        logger.info("Looking for Cloudflare verification...")
        self.page.wait_for_timeout(3000)  # Give more time for Cloudflare to load
        
        # Debug: Log all iframes on the page
        try:
            all_iframes = self.page.locator('iframe').all()
            logger.info(f"Found {len(all_iframes)} iframe(s) on the page")
            for i, iframe in enumerate(all_iframes):
                try:
                    src = iframe.get_attribute('src') or 'no src'
                    title = iframe.get_attribute('title') or 'no title'
                    logger.info(f"  Iframe {i+1}: src={src[:100]}, title={title}")
                except:
                    pass
        except Exception as e:
            logger.debug(f"Could not list iframes: {e}")
        
        # Approach 1: Look for Cloudflare iframe first
        cloudflare_clicked = False
        
        # Try to find Cloudflare iframe with more specific selectors
        iframe_selectors = [
            'iframe[src*="challenges.cloudflare.com"]',
            'iframe[src*="cloudflare"]',
            'iframe[title*="Cloudflare"]',
            'iframe[title*="challenge"]',
            'iframe[title*="Widget"]',
            'iframe.cf-turnstile',
            'iframe[data-sitekey]',
            'iframe[id*="cf-"]',
            'iframe[class*="cf-"]',
            'iframe',  # Last resort: try any iframe
        ]
        
        for iframe_selector in iframe_selectors:
            try:
                logger.info(f"Trying iframe selector: {iframe_selector}")
                iframe = self.page.locator(iframe_selector).first
                if iframe.is_visible(timeout=5000):
                    logger.info("Found iframe!")
                    # Get iframe details for debugging
                    try:
                        src = iframe.get_attribute('src')
                        logger.info(f"  Iframe src: {src}")
                    except:
                        pass
                    
                    self.page.wait_for_timeout(3000)  # Wait longer for iframe to fully load
                    
                    # Try using frame_locator (newer Playwright API)
                    try:
                        logger.info("Trying frame_locator approach...")
                        frame_locator = self.page.frame_locator(iframe_selector).first
                        
                        # Look for checkbox using frame_locator
                        checkbox_in_frame = frame_locator.locator('input[type="checkbox"]').first
                        if checkbox_in_frame.is_visible(timeout=5000):
                            logger.info("Found checkbox using frame_locator, clicking...")
                            # Move mouse to checkbox first (more human-like)
                            checkbox_in_frame.hover()
                            self.page.wait_for_timeout(500)
                            checkbox_in_frame.click()
                            cloudflare_clicked = True
                            self.page.wait_for_timeout(3000)
                            break
                        
                        # Look for any clickable element in iframe
                        clickable = frame_locator.locator('label, span, div, button').first
                        if clickable.is_visible(timeout=3000):
                            logger.info("Found clickable element in iframe, clicking...")
                            clickable.hover()
                            self.page.wait_for_timeout(500)
                            clickable.click()
                            cloudflare_clicked = True
                            self.page.wait_for_timeout(3000)
                            break
                    except Exception as e:
                        logger.debug(f"frame_locator approach failed: {e}")
                    
                    # Fallback: Try content_frame approach
                    try:
                        logger.info("Trying content_frame approach...")
                        frame = iframe.content_frame()
                        if frame:
                            logger.info("Successfully accessed iframe content_frame")
                            
                            # Look for checkbox in iframe
                            checkbox_in_frame = frame.locator('input[type="checkbox"]').first
                            if checkbox_in_frame.is_visible(timeout=5000):
                                logger.info("Found checkbox in iframe, clicking...")
                                checkbox_in_frame.hover()
                                self.page.wait_for_timeout(500)
                                checkbox_in_frame.click()
                                cloudflare_clicked = True
                                self.page.wait_for_timeout(3000)
                                break
                            
                            # Look for any clickable element
                            all_clickable = frame.locator('label, span, div, button, [role="checkbox"]').all()
                            logger.info(f"Found {len(all_clickable)} clickable elements in iframe")
                            for elem in all_clickable[:5]:  # Try first 5
                                try:
                                    if elem.is_visible(timeout=1000):
                                        logger.info(f"Clicking element: {elem}")
                                        elem.hover()
                                        self.page.wait_for_timeout(300)
                                        elem.click()
                                        cloudflare_clicked = True
                                        self.page.wait_for_timeout(3000)
                                        break
                                except:
                                    continue
                            if cloudflare_clicked:
                                break
                    except Exception as e:
                        logger.warning(f"Could not access iframe content_frame: {e}")
                    
                    # Last resort: Try clicking the iframe container itself
                    if not cloudflare_clicked:
                        try:
                            logger.info("Trying to click iframe container directly...")
                            # Get bounding box and click center
                            box = iframe.bounding_box()
                            if box:
                                x = box['x'] + box['width'] / 2
                                y = box['y'] + box['height'] / 2
                                logger.info(f"Clicking iframe center at ({x}, {y})")
                                self.page.mouse.move(x, y)
                                self.page.wait_for_timeout(500)
                                self.page.mouse.click(x, y)
                                cloudflare_clicked = True
                                self.page.wait_for_timeout(3000)
                                break
                        except Exception as e:
                            logger.debug(f"Could not click iframe container: {e}")
            except Exception as e:
                logger.debug(f"Iframe selector {iframe_selector} failed: {e}")
                continue
        
        # Approach 2: Try JavaScript injection to click Cloudflare (bypasses iframe restrictions)
        if not cloudflare_clicked:
            logger.info("Trying JavaScript injection approach...")
            try:
                # Try to find and click using JavaScript (can sometimes bypass iframe restrictions)
                result = self.page.evaluate("""
                    () => {
                        // Look for Cloudflare checkbox in all iframes
                        const iframes = document.querySelectorAll('iframe');
                        for (let iframe of iframes) {
                            try {
                                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                                const checkbox = iframeDoc.querySelector('input[type="checkbox"]');
                                if (checkbox) {
                                    checkbox.click();
                                    return 'clicked checkbox in iframe';
                                }
                            } catch (e) {
                                // Cross-origin, can't access
                            }
                        }
                        // Look for checkbox on main page
                        const checkbox = document.querySelector('input[type="checkbox"][name*="turnstile"], input[type="checkbox"][name*="cf-"]');
                        if (checkbox) {
                            checkbox.click();
                            return 'clicked checkbox on page';
                        }
                        return 'not found';
                    }
                """)
                if result and 'clicked' in result:
                    logger.info(f"JavaScript injection succeeded: {result}")
                    cloudflare_clicked = True
                    self.page.wait_for_timeout(3000)
            except Exception as e:
                logger.debug(f"JavaScript injection failed: {e}")
        
        # Approach 3: Look for checkbox directly on page (not in iframe)
        if not cloudflare_clicked:
            logger.info("Trying to find Cloudflare checkbox directly on page...")
            checkbox_selectors = [
                'input[type="checkbox"][name*="turnstile"]',
                'input[type="checkbox"][name*="cf-"]',
                'input[type="checkbox"]:near(label:has-text("Verify"))',
                'input[type="checkbox"]:near(label:has-text("I\'m not a robot"))',
                'label:has-text("Verify"):near(input[type="checkbox"])',
                '.cf-turnstile input[type="checkbox"]',
                '[role="checkbox"]',
            ]
            
            for checkbox_selector in checkbox_selectors:
                try:
                    logger.info(f"Trying checkbox selector: {checkbox_selector}")
                    checkbox = self.page.locator(checkbox_selector).first
                    if checkbox.is_visible(timeout=3000):
                        logger.info("Found Cloudflare checkbox, clicking...")
                        checkbox.hover()
                        self.page.wait_for_timeout(300)
                        checkbox.click()
                        cloudflare_clicked = True
                        self.page.wait_for_timeout(3000)
                        break
                except Exception as e:
                    logger.debug(f"Checkbox selector {checkbox_selector} failed: {e}")
                    continue
        
        # Approach 4: Look for any clickable element with "Verify" text
        if not cloudflare_clicked:
            logger.info("Trying to find verify button/label...")
            verify_selectors = [
                'button:has-text("Verify")',
                'label:has-text("Verify")',
                'div:has-text("Verify"):has(input[type="checkbox"])',
                '[role="checkbox"]',
                'div[class*="verify"]',
                'span:has-text("Verify")',
            ]
            
            for verify_selector in verify_selectors:
                try:
                    verify_element = self.page.locator(verify_selector).first
                    if verify_element.is_visible(timeout=3000):
                        logger.info(f"Found verify element with selector: {verify_selector}, clicking...")
                        verify_element.hover()
                        self.page.wait_for_timeout(300)
                        verify_element.click()
                        cloudflare_clicked = True
                        self.page.wait_for_timeout(3000)
                        break
                except Exception as e:
                    logger.debug(f"Verify selector {verify_selector} failed: {e}")
                    continue
        
        # Approach 5: Take screenshot for debugging if still not clicked
        if not cloudflare_clicked:
            try:
                import tempfile
                screenshot_path = Path(tempfile.gettempdir()) / 'canva_cloudflare_debug.png'
                self.page.screenshot(path=str(screenshot_path), full_page=True)
                logger.warning(f"Cloudflare not found - screenshot saved to {screenshot_path} for debugging")
                logger.warning("Please check the screenshot to see what elements are visible on the page")
            except Exception as e:
                logger.debug(f"Could not take screenshot: {e}")
        
        if cloudflare_clicked:
            logger.info("Cloudflare verification clicked successfully!")
        else:
            if self.cloudflare_mode == "manual":
                logger.info("=" * 60)
                logger.info("MANUAL INTERVENTION REQUIRED")
                logger.info("=" * 60)
                logger.info("Cloudflare verification could not be automated.")
                logger.info("Please manually complete the Cloudflare verification in the browser.")
                logger.info("The script will wait for you to finish...")
                logger.info("=" * 60)
                
                # Wait for user to complete Cloudflare manually
                # Check every 2 seconds if we're past the Cloudflare page
                max_wait = 300  # 5 minutes max wait
                waited = 0
                while waited < max_wait:
                    self.page.wait_for_timeout(2000)
                    waited += 2
                    
                    # Check if we're past Cloudflare (URL changed or logged in)
                    current_url = self.page.url
                    if "challenges.cloudflare.com" not in current_url:
                        # Check if we're logged in now
                        try:
                            user_menu = self.page.locator('[data-testid="user-menu"], [aria-label*="Account" i]').first
                            if user_menu.is_visible(timeout=1000):
                                logger.info("Login detected! Continuing...")
                                break
                        except:
                            pass
                        
                        # If URL changed away from Cloudflare, assume it's done
                        if "canva.com" in current_url and "challenges" not in current_url:
                            logger.info("Cloudflare verification appears complete. Continuing...")
                            break
                    
                    # Every 30 seconds, remind user
                    if waited % 30 == 0:
                        logger.info(f"Still waiting... ({waited}/{max_wait} seconds)")
                
                if waited >= max_wait:
                    logger.warning("Timeout waiting for manual Cloudflare completion. Continuing anyway...")
            else:
                logger.warning("Could not find or click Cloudflare verification - may need manual intervention")
        
        # Wait for verification to complete
        logger.info("Waiting for Cloudflare verification to complete...")
        self.page.wait_for_timeout(5000)
        
        # Check if popup closed (authentication succeeded)
        current_pages = self.browser.pages
        if len(current_pages) == 1 and popup:
            logger.info("Popup closed, authentication likely succeeded")
            self.page = current_pages[0]
            self.page.bring_to_front()
        elif popup and popup in current_pages:
            logger.info("Popup still open, waiting a bit more...")
            self.page.wait_for_timeout(5000)
            # Check again
            final_pages = self.browser.pages
            if len(final_pages) == 1:
                logger.info("Popup closed after additional wait")
                self.page = final_pages[0]
                self.page.bring_to_front()
            else:
                logger.info("Keeping focus on popup window")
    
    def _write_output_json(self, folder: Path, output_data: Dict[str, Any]) -> None:
        """Write output JSON file to the input folder for multi-agent orchestration."""
        output_path = folder / "canva_output.json"
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Output JSON written to: {output_path}")
        except Exception as e:
            logger.error(f"Failed to write output JSON: {e}")
    
    def _ensure_page_exists(self, current_page_index: int, image_index: int) -> None:
        """
        Ensure the required page exists by adding pages if needed.
        No thumbnail clicks - avoids miss-clicking sidebar elements that break the Uploads button.
        Canva auto-switches to the newly created page.
        """
        if image_index > 0:
            self._add_page()
            self.page.wait_for_timeout(500)
    
    def _add_page(self) -> None:
        """
        Add a new blank page to the design.
        """
        add_page_selectors = [
            'button:has-text("Add page")',
            'button:has-text("Add a page")',
            '[data-testid*="add-page"]',
            'button[aria-label*="Add page" i]',
            'button[aria-label*="add page" i]',
        ]
        
        page_added = False
        for selector in add_page_selectors:
            try:
                add_page_button = self.page.locator(selector).first
                if add_page_button.is_visible(timeout=3000):
                    add_page_button.click()
                    self.page.wait_for_timeout(1000)  # Wait for page to be created
                    page_added = True
                    logger.debug("Added new page")
                    break
            except:
                continue
        
        if not page_added:
            raise Exception("Could not find 'Add page' button")

