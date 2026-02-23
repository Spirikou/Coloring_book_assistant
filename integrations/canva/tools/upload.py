from pathlib import Path
from typing import List
import logging
import json

from playwright.sync_api import Page

logger = logging.getLogger(__name__)

# Timeouts for upload flow
UPLOAD_IMAGE_WAIT_MAX_MS = 15000  # Max wait for image to appear in panel (15s)
UPLOAD_IMAGE_POLL_INTERVAL_MS = 500  # Poll interval
COORDINATE_CLICK_RETRIES = 2  # Retries before falling back to selectors

# Load coordinates (merged file containing both design_modal and uploads_panel)
# Path(__file__).parent.parent = integrations/canva when in integrations/canva/tools/upload.py
COORDINATES_PATH = Path(__file__).parent.parent / "coordinates.json"
UPLOAD_COORDINATES_CONFIG = None

try:
    if COORDINATES_PATH.exists():
        with open(COORDINATES_PATH, 'r') as f:
            all_coordinates = json.load(f)
            # Extract uploads_panel section
            UPLOAD_COORDINATES_CONFIG = {"uploads_panel": all_coordinates.get("uploads_panel", {})}
        logger.debug("Loaded upload coordinates from coordinates.json")
    else:
        logger.debug("coordinates.json not found, will use fallback selectors")
except Exception as e:
    logger.debug(f"Could not load coordinates: {e}")


def open_uploads_panel(page: Page) -> None:
    """
    Open the Uploads panel (only needs to be done once).

    Args:
        page: Playwright page object
    """
    logger.info("Opening Uploads panel...")
    uploads_clicked = False

    # Strategy 1: Try coordinates first (original approach - was working before)
    if UPLOAD_COORDINATES_CONFIG and "uploads_panel" in UPLOAD_COORDINATES_CONFIG:
        uploads_coords = UPLOAD_COORDINATES_CONFIG["uploads_panel"].get("uploads_sidebar_button", {})
        if uploads_coords.get("x", 0) > 0 and uploads_coords.get("y", 0) > 0:
            try:
                page.mouse.click(uploads_coords["x"], uploads_coords["y"])
                page.wait_for_timeout(2000)  # Wait for upload panel to open
                uploads_clicked = True
                logger.info(f"✅ Clicked Uploads sidebar at ({uploads_coords['x']}, {uploads_coords['y']})")
            except Exception as e:
                logger.warning(f"Coordinate-based click failed: {e}, trying text selectors...")

    # Strategy 2: Fallback to text-based selectors if coordinates fail
    if not uploads_clicked:
        upload_selectors = [
            'button:has-text("Uploads")',
            '[data-testid*="upload"]',
            'button[aria-label*="Upload" i]',
            'button[aria-label*="upload" i]',
            'text=Uploads',
            '[role="button"]:has-text("Uploads")',
            'div[role="button"]:has-text("Uploads")',
            'button[title*="Upload" i]',
        ]

        for selector in upload_selectors:
            try:
                upload_button = page.locator(selector).first
                if upload_button.is_visible(timeout=2000):
                    upload_button.click()
                    page.wait_for_timeout(2000)  # Wait for upload panel to open
                    uploads_clicked = True
                    logger.info(f"✅ Clicked Uploads button using selector: {selector}")
                    break
            except:
                continue

    if not uploads_clicked:
        raise Exception("Could not click Uploads sidebar button")


def _dismiss_overlays(page: Page) -> None:
    """
    Dismiss common Canva overlays (Try Pro, template suggestions, etc.) that may block uploads.
    Call before upload steps to avoid clicks landing on wrong elements.
    """
    dismiss_selectors = [
        'button:has-text("Skip")',
        'button:has-text("Start from scratch")',
        'button:has-text("Blank")',
        'button:has-text("Start blank")',
        'button[aria-label*="Close" i]',
        'button[aria-label*="Dismiss" i]',
        '[data-testid*="skip"]',
        '[aria-label*="Skip" i]',
    ]
    for selector in dismiss_selectors:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=500):
                btn.click()
                page.wait_for_timeout(800)
                logger.debug(f"Dismissed overlay: {selector}")
                break
        except Exception:
            continue


def _wait_for_uploaded_image(page: Page, image_path: Path) -> bool:
    """
    Wait for the uploaded image to appear in the Uploads panel (ready to click).
    Returns True if image became visible, False if timeout.
    """
    elapsed = 0
    selectors = [
        f'img[alt*="{image_path.name}"]',
        f'img[title*="{image_path.name}"]',
        f'img[alt*="{image_path.stem}"]',
    ]
    while elapsed < UPLOAD_IMAGE_WAIT_MAX_MS:
        for sel in selectors:
            try:
                img = page.locator(sel).first
                if img.is_visible(timeout=500):
                    logger.info(f"Image visible after {elapsed}ms")
                    return True
            except Exception:
                continue
        page.wait_for_timeout(UPLOAD_IMAGE_POLL_INTERVAL_MS)
        elapsed += UPLOAD_IMAGE_POLL_INTERVAL_MS
    logger.warning(f"Image not visible after {UPLOAD_IMAGE_WAIT_MAX_MS}ms, continuing anyway")
    return False


def upload_and_place_single_image(page: Page, image_path: Path) -> None:
    """
    Upload a single image and place it on the canvas.

    Simple workflow:
    1. Click Uploads button (coordinates) - ensures panel is open
    2. Click Upload files button (coordinates)
    3. Select and upload the image
    4. Wait 5 seconds for upload
    5. Click on the uploaded image to place it (coordinates)

    Args:
        page: Playwright page object
        image_path: Path to the image file to upload
    """
    logger.info(f"Uploading and placing image: {image_path.name}")

    # Step 0: Dismiss any overlays that might block clicks
    _dismiss_overlays(page)

    # Step 1: Click Uploads sidebar button (with retries)
    logger.info("Step 1: Clicking Uploads sidebar button...")
    uploads_clicked = False

    for attempt in range(COORDINATE_CLICK_RETRIES + 1):
        if UPLOAD_COORDINATES_CONFIG and "uploads_panel" in UPLOAD_COORDINATES_CONFIG:
            uploads_coords = UPLOAD_COORDINATES_CONFIG["uploads_panel"].get("uploads_sidebar_button", {})
            if uploads_coords.get("x", 0) > 0 and uploads_coords.get("y", 0) > 0:
                try:
                    page.mouse.click(uploads_coords["x"], uploads_coords["y"])
                    page.wait_for_timeout(2000)
                    uploads_clicked = True
                    logger.info(f"✅ Clicked Uploads sidebar at ({uploads_coords['x']}, {uploads_coords['y']})")
                    break
                except Exception as e:
                    if attempt < COORDINATE_CLICK_RETRIES:
                        logger.warning(f"Retry {attempt + 1}: {e}")
                        page.wait_for_timeout(500)
                    else:
                        logger.warning(f"Coordinate click failed: {e}, trying text selectors...")

    # Strategy 2: Fallback to text-based selectors if coordinates fail
    if not uploads_clicked:
        upload_selectors = [
            'button:has-text("Uploads")',
            '[data-testid*="upload"]',
            'button[aria-label*="Upload" i]',
            'button[aria-label*="upload" i]',
            'text=Uploads',
            '[role="button"]:has-text("Uploads")',
            'div[role="button"]:has-text("Uploads")',
            'button[title*="Upload" i]',
        ]

        for selector in upload_selectors:
            try:
                upload_button = page.locator(selector).first
                if upload_button.is_visible(timeout=2000):
                    upload_button.click()
                    page.wait_for_timeout(2000)  # Wait for upload panel to open
                    uploads_clicked = True
                    logger.info(f"✅ Clicked Uploads button using selector: {selector}")
                    break
            except:
                continue

    if not uploads_clicked:
        raise Exception("Could not click Uploads sidebar button")

    # Step 2: Click Upload files button (with retries)
    _dismiss_overlays(page)
    logger.info("Step 2: Clicking Upload files button...")
    upload_files_clicked = False

    for attempt in range(COORDINATE_CLICK_RETRIES + 1):
        if UPLOAD_COORDINATES_CONFIG and "uploads_panel" in UPLOAD_COORDINATES_CONFIG:
            upload_files_coords = UPLOAD_COORDINATES_CONFIG["uploads_panel"].get("upload_files_button", {})
            if upload_files_coords.get("x", 0) > 0 and upload_files_coords.get("y", 0) > 0:
                try:
                    page.mouse.click(upload_files_coords["x"], upload_files_coords["y"])
                    page.wait_for_timeout(1000)
                    upload_files_clicked = True
                    logger.info(f"✅ Clicked Upload files button at ({upload_files_coords['x']}, {upload_files_coords['y']})")
                    break
                except Exception as e:
                    if attempt < COORDINATE_CLICK_RETRIES:
                        logger.warning(f"Retry {attempt + 1} Upload files: {e}")
                        page.wait_for_timeout(500)
                    else:
                        logger.error(f"Failed to click Upload files button: {e}")

    if not upload_files_clicked:
        # Fallback to text-based selector
        try:
            upload_files_btn = page.locator('button:has-text("Upload files"), button:has-text("Upload")').first
            if upload_files_btn.is_visible(timeout=3000):
                upload_files_btn.click()
                page.wait_for_timeout(1000)
                upload_files_clicked = True
                logger.info("✅ Clicked Upload files button using text selector")
        except:
            pass

    if not upload_files_clicked:
        raise Exception("Could not click Upload files button")

    # Step 3: Select and upload the image
    logger.info(f"Step 3: Selecting image: {image_path.name}...")
    try:
        # Find the file input (should be available after clicking upload button)
        file_input = page.locator('input[type="file"]').first

        if file_input.count() > 0:
            file_input.set_input_files([str(image_path)])
            logger.info(f"✅ Selected image: {image_path.name}")
        else:
            raise Exception("File input not found after clicking Upload files button")
    except Exception as e:
        logger.error(f"Failed to select image: {e}")
        raise

    # Step 4: Wait for image to appear in uploads panel (ready to click)
    logger.info("Step 4: Waiting for image to appear in uploads panel...")
    _wait_for_uploaded_image(page, image_path)
    page.wait_for_timeout(1000)  # Brief extra wait for UI to settle

    # Step 5: Click on the uploaded image to place it (coordinates first, then selectors)
    _dismiss_overlays(page)
    logger.info("Step 5: Clicking on uploaded image to place it...")
    image_placed = False

    for attempt in range(COORDINATE_CLICK_RETRIES + 1):
        if UPLOAD_COORDINATES_CONFIG and "uploads_panel" in UPLOAD_COORDINATES_CONFIG:
            image_click_coords = UPLOAD_COORDINATES_CONFIG["uploads_panel"].get("uploaded_image_click", {})
            if image_click_coords.get("x", 0) > 0 and image_click_coords.get("y", 0) > 0:
                try:
                    page.mouse.click(image_click_coords["x"], image_click_coords["y"])
                    page.wait_for_timeout(1000)
                    image_placed = True
                    logger.info(f"✅ Clicked on uploaded image at ({image_click_coords['x']}, {image_click_coords['y']})")
                    break
                except Exception as e:
                    if attempt < COORDINATE_CLICK_RETRIES:
                        logger.warning(f"Retry {attempt + 1} image click: {e}")
                        page.wait_for_timeout(500)
                    else:
                        logger.debug(f"Coordinate click failed: {e}, trying selectors...")

    if not image_placed:
        # Fallback: try to find the image by name or recent upload
        try:
            # Try to find the most recently uploaded image
            image_selectors = [
                f'img[alt*="{image_path.name}"]',
                f'img[title*="{image_path.name}"]',
                'img[alt*="upload"]',
                'img:last-of-type',  # Last image in uploads
            ]

            for selector in image_selectors:
                try:
                    image_element = page.locator(selector).first
                    if image_element.is_visible(timeout=2000):
                        image_element.click()
                        page.wait_for_timeout(1000)
                        image_placed = True
                        logger.info(f"✅ Clicked on uploaded image using selector: {selector}")
                        break
                except:
                    continue
        except:
            pass

    if not image_placed:
        logger.warning("Could not click on uploaded image - it may have been placed automatically")

    logger.info(f"✅ Completed upload and placement for: {image_path.name}")
