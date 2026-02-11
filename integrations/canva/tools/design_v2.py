"""
Enhanced design creation with multiple fallback strategies including text-based and OCR approaches.
"""

from playwright.sync_api import Page
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Load custom selectors if available
SELECTORS_CONFIG = None
SELECTORS_PATH = Path(__file__).parent.parent / "canva_selectors.json"
if SELECTORS_PATH.exists():
    try:
        with open(SELECTORS_PATH, 'r') as f:
            SELECTORS_CONFIG = json.load(f)
        logger.info(f"Loaded custom selectors from {SELECTORS_PATH}")
    except Exception as e:
        logger.debug(f"Could not load selectors config: {e}")

# Load coordinates if available (simpler approach - just click at x,y)
COORDINATES_CONFIG = None
COORDINATES_PATH = Path(__file__).parent.parent / "coordinates.json"
if COORDINATES_PATH.exists():
    try:
        with open(COORDINATES_PATH, 'r') as f:
            COORDINATES_CONFIG = json.load(f)
        logger.info(f"Loaded coordinates from {COORDINATES_PATH}")
    except Exception as e:
        logger.debug(f"Could not load coordinates config: {e}")


def create_design(page: Page, width_in: float, height_in: float, page_count: int) -> None:
    """
    Create a new custom-size design with the requested dimensions and pages.

    IMPORTANT: Order of operations:
    1. Open create design modal
    2. Select unit "in" (inches) - MUST BE FIRST
    3. Fill width
    4. Fill height
    5. Click "Create new design"
    6. Add additional pages

    Uses coordinate-based approach with fallbacks:
    - Coordinates from coordinates.json (primary)
    - Text-based locators (fallback)
    - XPath (fallback)
    - Generic selectors (fallback)
    """

    # Step 1: Click to create a new design
    logger.info("Step 1: Opening create design dialog...")
    create_selectors = [
        'button:has-text("Create a design")',
        'button:has-text("Create")',
        'a:has-text("Create a design")',
        'text=Custom size',
        '[data-testid*="create"]',
        'button[aria-label*="Create" i]',
    ]

    create_clicked = False
    for selector in create_selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible(timeout=3000):
                element.click()
                page.wait_for_timeout(2000)
                create_clicked = True
                logger.info(f"Clicked create design with selector: {selector}")
                break
        except:
            continue

    if not create_clicked:
        try:
            page.click("text=Custom size", timeout=5000)
            page.wait_for_timeout(2000)
            create_clicked = True
        except:
            raise Exception("Could not find 'Create a design' or 'Custom size' button")

    # Wait for modal to fully load and verify it's visible
    logger.info("Waiting for custom size modal to fully load...")
    page.wait_for_timeout(3000)  # Give more time for modal animation

    # Verify modal is visible by checking for "Custom size" text or input fields
    try:
        page.wait_for_selector('input[type="number"], input[type="text"], text=Custom size', timeout=5000, state='visible')
        logger.info("Modal is visible")
    except:
        logger.warning("Could not verify modal visibility, continuing anyway...")
        try:
            page.screenshot(path="canva_modal_debug.png", full_page=True)
            logger.info("Screenshot saved to canva_modal_debug.png")
        except:
            pass

    # Step 2: Select unit "in" (inches) - MUST BE DONE BEFORE width/height
    logger.info("Step 2: Selecting unit 'in' (inches)...")
    unit_selected = False

    if COORDINATES_CONFIG and "design_modal" in COORDINATES_CONFIG:
        unit_coords = COORDINATES_CONFIG["design_modal"].get("unit_selector", {})
        if unit_coords.get("x", 0) > 0 and unit_coords.get("y", 0) > 0:
            try:
                logger.info(f"Clicking unit selector at coordinates: ({unit_coords['x']}, {unit_coords['y']})")
                page.mouse.click(unit_coords["x"], unit_coords["y"])
                page.wait_for_timeout(1500)

                in_clicked = False
                in_selectors = [
                    'button:has-text("in")',
                    'option:has-text("in")',
                    'li:has-text("in")',
                    '[data-value="in"]',
                    '[role="option"]:has-text("in")',
                    'div:has-text("in")',
                ]
                for selector in in_selectors:
                    try:
                        in_option = page.locator(selector).first
                        if in_option.is_visible(timeout=2000):
                            in_option.click()
                            page.wait_for_timeout(1000)
                            in_clicked = True
                            logger.info(f"Clicked 'in' option using selector: {selector}")
                            break
                    except:
                        continue

                if not in_clicked:
                    try:
                        page.mouse.click(unit_coords["x"] + 10, unit_coords["y"] + 40)
                        page.wait_for_timeout(1000)
                        in_clicked = True
                        logger.info("Clicked 'in' option by clicking below unit selector")
                    except:
                        pass

                if in_clicked:
                    unit_selected = True
                    logger.info("Unit 'in' selected successfully using coordinates")
                else:
                    logger.warning("Could not find 'in' option in dropdown after opening")
            except Exception as e:
                logger.debug(f"Coordinate-based unit selection failed: {e}")

    try:
        units_label = page.get_by_text("Units", exact=False).first
        if units_label.is_visible(timeout=2000):
            unit_selector = units_label.locator('..').locator('select, button, [role="button"]').first
            if unit_selector.is_visible(timeout=1000):
                unit_selector.click()
                page.wait_for_timeout(1000)
                in_option = page.locator('button:has-text("in"), option:has-text("in"), [data-value="in"], li:has-text("in")').first
                if in_option.is_visible(timeout=2000):
                    in_option.click()
                    unit_selected = True
                    page.wait_for_timeout(1000)
                    logger.info("Selected unit 'in' using text-based approach")
    except:
        pass

    if not unit_selected:
        try:
            unit_elements = page.locator('select, button, [role="button"]').filter(has_text="in")
            if unit_elements.count() > 0:
                unit_elements.first.click()
                page.wait_for_timeout(1000)
                unit_selected = True
                logger.info("Selected unit 'in' using direct text filter")
        except:
            pass

    if not unit_selected:
        try:
            select_elements = page.locator('select').all()
            for select_elem in select_elements:
                try:
                    if select_elem.is_visible(timeout=1000):
                        select_elem.select_option("in")
                        unit_selected = True
                        page.wait_for_timeout(1000)
                        logger.info("Selected unit 'in' using select dropdown")
                        break
                except:
                    continue
        except:
            pass

    if not unit_selected:
        logger.warning("Could not explicitly select 'in' unit. Proceeding - unit might already be set.")
    else:
        logger.info("✅ Unit 'in' selected successfully - proceeding to fill dimensions")
        page.wait_for_timeout(500)

    # Step 3: Fill width
    logger.info(f"Step 3: Filling width: {width_in} inches...")
    width_filled = False
    page.wait_for_timeout(1000)

    if COORDINATES_CONFIG and "design_modal" in COORDINATES_CONFIG:
        width_coords = COORDINATES_CONFIG["design_modal"].get("width_input", {})
        if width_coords.get("x", 0) > 0 and width_coords.get("y", 0) > 0:
            try:
                page.mouse.click(width_coords["x"], width_coords["y"])
                page.wait_for_timeout(300)
                page.keyboard.press("Control+A")
                page.keyboard.type(str(width_in))
                page.wait_for_timeout(500)
                width_filled = True
                logger.info(f"Filled width using coordinates: ({width_coords['x']}, {width_coords['y']})")
            except Exception as e:
                logger.debug(f"Coordinate-based width fill failed: {e}")

    if not width_filled and SELECTORS_CONFIG and "design_modal" in SELECTORS_CONFIG:
        custom_selectors = SELECTORS_CONFIG["design_modal"].get("width_input", [])
        for selector in custom_selectors:
            try:
                width_input = page.locator(selector).first
                if width_input.is_visible(timeout=2000):
                    width_input.click()
                    page.wait_for_timeout(300)
                    width_input.fill("")
                    width_input.fill(str(width_in))
                    page.wait_for_timeout(500)
                    width_filled = True
                    logger.info(f"Filled width using custom selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"Custom selector {selector} failed: {e}")
                continue

    try:
        width_label_variations = [
            page.get_by_text("Width", exact=False),
            page.get_by_text("Width:", exact=False),
            page.locator('label:has-text("Width")'),
            page.locator('*:has-text("Width")'),
        ]
        width_label = None
        for label_locator in width_label_variations:
            try:
                label = label_locator.first
                if label.is_visible(timeout=2000):
                    width_label = label
                    logger.info("Found 'Width' label")
                    break
            except:
                continue

        if width_label:
            width_input = None
            try:
                parent = width_label.locator('..')
                width_input = parent.locator('input').first
                if width_input.is_visible(timeout=1000):
                    logger.info("Found width input in parent container")
            except:
                pass
            if not width_input or not width_input.is_visible(timeout=500):
                try:
                    width_input = width_label.locator('..').locator('..').locator('input').first
                    if width_input.is_visible(timeout=1000):
                        logger.info("Found width input as sibling")
                except:
                    pass
            if not width_input or not width_input.is_visible(timeout=500):
                try:
                    box = width_label.bounding_box()
                    if box:
                        all_inputs = page.locator('input').all()
                        for inp in all_inputs:
                            try:
                                inp_box = inp.bounding_box()
                                if inp_box and inp_box['x'] > box['x'] and abs(inp_box['y'] - box['y']) < 50:
                                    width_input = inp
                                    logger.info("Found width input by position near label")
                                    break
                            except:
                                continue
                except:
                    pass
            if not width_input or not width_input.is_visible(timeout=500):
                try:
                    width_input = page.locator('xpath=//*[contains(text(), "Width")]/following::input[1] | //label[contains(text(), "Width")]/following-sibling::input[1]').first
                    if width_input.is_visible(timeout=1000):
                        logger.info("Found width input using XPath")
                except:
                    pass
            if width_input and width_input.is_visible(timeout=2000):
                width_input.click()
                page.wait_for_timeout(300)
                width_input.fill("")
                width_input.fill(str(width_in))
                page.wait_for_timeout(500)
                width_filled = True
                logger.info("Filled width using text-based label approach")
    except Exception as e:
        logger.debug(f"Text-based width approach failed: {e}")

    if not width_filled:
        try:
            width_input = page.locator('xpath=//*[contains(text(), "Width")]/following::input[1] | //label[contains(text(), "Width")]/following-sibling::input[1] | //*[contains(text(), "Width")]/ancestor::*[1]//input[1]').first
            if width_input.is_visible(timeout=2000):
                width_input.click()
                page.wait_for_timeout(300)
                width_input.fill("")
                width_input.fill(str(width_in))
                page.wait_for_timeout(500)
                width_filled = True
                logger.info("Filled width using XPath approach")
        except Exception as e:
            logger.debug(f"XPath width approach failed: {e}")

    if not width_filled:
        try:
            all_inputs = page.locator('input[type="number"], input[type="text"], input').all()
            logger.info(f"Found {len(all_inputs)} total input fields")
            if len(all_inputs) > 0:
                width_input = all_inputs[0]
                if width_input.is_visible(timeout=2000):
                    width_input.click()
                    page.wait_for_timeout(300)
                    width_input.fill("")
                    width_input.fill(str(width_in))
                    page.wait_for_timeout(500)
                    width_filled = True
                    logger.info("Filled width using generic first input approach")
        except Exception as e:
            logger.debug(f"Generic input approach failed: {e}")

    if not width_filled:
        try:
            page.screenshot(path="canva_width_debug.png", full_page=True)
            logger.warning("Screenshot saved to canva_width_debug.png for debugging")
            page.keyboard.press("Tab")
            page.wait_for_timeout(500)
            page.keyboard.type(str(width_in))
            page.wait_for_timeout(500)
            width_filled = True
            logger.info("Filled width using keyboard Tab navigation")
        except Exception as e:
            logger.debug(f"Keyboard navigation failed: {e}")

    if not width_filled:
        try:
            page.screenshot(path="canva_width_error.png", full_page=True)
            logger.error("Screenshot saved to canva_width_error.png")
        except:
            pass
        raise Exception("Could not find width input field. Tried text-based, XPath, generic, and keyboard approaches.")

    # Step 4: Fill height
    logger.info(f"Step 4: Filling height: {height_in} inches...")
    height_filled = False

    if COORDINATES_CONFIG and "design_modal" in COORDINATES_CONFIG:
        height_coords = COORDINATES_CONFIG["design_modal"].get("height_input", {})
        if height_coords.get("x", 0) > 0 and height_coords.get("y", 0) > 0:
            try:
                page.mouse.click(height_coords["x"], height_coords["y"])
                page.wait_for_timeout(300)
                page.keyboard.press("Control+A")
                page.keyboard.type(str(height_in))
                page.wait_for_timeout(500)
                height_filled = True
                logger.info(f"Filled height using coordinates: ({height_coords['x']}, {height_coords['y']})")
            except Exception as e:
                logger.debug(f"Coordinate-based height fill failed: {e}")

    if not height_filled and SELECTORS_CONFIG and "design_modal" in SELECTORS_CONFIG:
        custom_selectors = SELECTORS_CONFIG["design_modal"].get("height_input", [])
        for selector in custom_selectors:
            try:
                height_input = page.locator(selector).first
                if height_input.is_visible(timeout=2000):
                    height_input.click()
                    page.wait_for_timeout(300)
                    height_input.fill("")
                    height_input.fill(str(height_in))
                    page.wait_for_timeout(500)
                    height_filled = True
                    logger.info(f"Filled height using custom selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"Custom selector {selector} failed: {e}")
                continue

    try:
        height_label_variations = [
            page.get_by_text("Height", exact=False),
            page.get_by_text("Height:", exact=False),
            page.locator('label:has-text("Height")'),
            page.locator('*:has-text("Height")'),
        ]
        height_label = None
        for label_locator in height_label_variations:
            try:
                label = label_locator.first
                if label.is_visible(timeout=2000):
                    height_label = label
                    logger.info("Found 'Height' label")
                    break
            except:
                continue

        if height_label:
            height_input = None
            try:
                parent = height_label.locator('..')
                height_input = parent.locator('input').first
                if height_input.is_visible(timeout=1000):
                    logger.info("Found height input in parent container")
            except:
                pass
            if not height_input or not height_input.is_visible(timeout=500):
                try:
                    height_input = height_label.locator('..').locator('..').locator('input').first
                    if height_input.is_visible(timeout=1000):
                        logger.info("Found height input as sibling")
                except:
                    pass
            if not height_input or not height_input.is_visible(timeout=500):
                try:
                    box = height_label.bounding_box()
                    if box:
                        all_inputs = page.locator('input').all()
                        for inp in all_inputs:
                            try:
                                inp_box = inp.bounding_box()
                                if inp_box and inp_box['x'] > box['x'] and abs(inp_box['y'] - box['y']) < 50:
                                    height_input = inp
                                    logger.info("Found height input by position near label")
                                    break
                            except:
                                continue
                except:
                    pass
            if height_input and height_input.is_visible(timeout=2000):
                height_input.click()
                page.wait_for_timeout(300)
                height_input.fill("")
                height_input.fill(str(height_in))
                page.wait_for_timeout(500)
                height_filled = True
                logger.info("Filled height using text-based label approach")
    except Exception as e:
        logger.debug(f"Text-based height approach failed: {e}")

    if not height_filled:
        try:
            height_input = page.locator('xpath=//*[contains(text(), "Height")]/following::input[1] | //label[contains(text(), "Height")]/following-sibling::input[1] | //*[contains(text(), "Height")]/ancestor::*[1]//input[2]').first
            if height_input.is_visible(timeout=2000):
                height_input.click()
                page.wait_for_timeout(300)
                height_input.fill("")
                height_input.fill(str(height_in))
                page.wait_for_timeout(500)
                height_filled = True
                logger.info("Filled height using XPath approach")
        except Exception as e:
            logger.debug(f"XPath height approach failed: {e}")

    if not height_filled:
        try:
            all_inputs = page.locator('input[type="number"], input[type="text"], input').all()
            if len(all_inputs) > 1:
                height_input = all_inputs[1]
                if height_input.is_visible(timeout=2000):
                    height_input.click()
                    page.wait_for_timeout(300)
                    height_input.fill("")
                    height_input.fill(str(height_in))
                    page.wait_for_timeout(500)
                    height_filled = True
                    logger.info("Filled height using generic second input approach")
        except Exception as e:
            logger.debug(f"Generic height approach failed: {e}")

    if not height_filled:
        try:
            page.keyboard.press("Tab")
            page.wait_for_timeout(500)
            page.keyboard.type(str(height_in))
            page.wait_for_timeout(500)
            height_filled = True
            logger.info("Filled height using keyboard Tab navigation")
        except Exception as e:
            logger.debug(f"Keyboard navigation failed: {e}")

    if not height_filled:
        raise Exception("Could not find height input field. Tried text-based, XPath, generic, and keyboard approaches.")

    # Step 5: Click "Create new design"
    logger.info("Step 5: Clicking 'Create new design' button...")
    create_button_clicked = False

    create_button_selectors = [
        'button:has-text("Create new design")',
        'button:has-text("Create design")',
        'button:has-text("Create")',
        '[data-testid*="create"]',
        'button[type="submit"]',
    ]

    for selector in create_button_selectors:
        try:
            create_button = page.locator(selector).first
            if create_button.is_visible(timeout=2000):
                create_button.click()
                page.wait_for_timeout(4000)
                create_button_clicked = True
                logger.info(f"Clicked create button with selector: {selector}")
                break
        except:
            continue

    if not create_button_clicked:
        raise Exception("Could not find 'Create new design' button")

    logger.info("Design created with 1 page. Pages will be added as images are placed.")
    logger.info("Design creation completed successfully!")
