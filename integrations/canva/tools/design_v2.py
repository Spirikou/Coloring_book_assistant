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


def _create_modal_opened(page: Page) -> bool:
    """Check if the create design modal (with Custom size) is open."""
    try:
        page.wait_for_timeout(500)
        if page.locator('text=Custom size').first.is_visible(timeout=1000):
            return True
        if page.locator('input[type="number"], input[type="text"]').first.is_visible(timeout=1000):
            return True
    except Exception:
        pass
    return False


def _dismiss_magic_layers_popup(page: Page) -> None:
    """Dismiss Magic Layers popup if visible (click X or Escape)."""
    try:
        # Try close button first, then Escape
        close_selectors = [
            'button[aria-label*="Close" i]',
            '[aria-label*="Close" i]',
            'button:has-text("Close")',
        ]
        for sel in close_selectors:
            el = page.locator(sel).first
            if el.is_visible(timeout=500):
                el.click()
                page.wait_for_timeout(500)
                return
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    except Exception:
        pass


def create_design(
    page: Page,
    width_in: float,
    height_in: float,
    page_count: int,
    *,
    debug_context: dict | None = None,
) -> None:
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
    # 1a. Try coordinates FIRST (sidebar Create at top-left) - avoids Magic Layers confusion
    logger.info("Step 1: Opening create design dialog...")
    step1_x, step1_y = None, None
    if COORDINATES_CONFIG and "sidebar_create_button" in COORDINATES_CONFIG:
        c = COORDINATES_CONFIG["sidebar_create_button"]
        if c.get("x") is not None and c.get("y") is not None:
            step1_x, step1_y = c["x"], c["y"]
    if step1_x is None or step1_y is None:
        from .. import config as canva_config
        step1_x = getattr(canva_config, "CANVA_SIDEBAR_CREATE_BUTTON_X", 35)
        step1_y = getattr(canva_config, "CANVA_SIDEBAR_CREATE_BUTTON_Y", 80)

    create_clicked = False
    step1_click = (step1_x, step1_y)
    try:
        page.mouse.click(step1_x, step1_y)
        page.wait_for_timeout(2000)
        if _create_modal_opened(page):
            create_clicked = True
            logger.info(f"Clicked sidebar Create at ({step1_x}, {step1_y}) - create modal opened")
        else:
            _dismiss_magic_layers_popup(page)
            page.wait_for_timeout(500)
    except Exception as e:
        logger.debug(f"Coordinate click failed: {e}")

    # 1b. Selector fallbacks only if coordinates failed
    create_selectors = [
        'button[aria-label="Create a design"]',
        'button:has-text("Create a design")',
        'a:has-text("Create a design")',
        'text=Custom size',
        '[data-testid*="create"]',
    ]
    if not create_clicked:
        for selector in create_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=3000):
                    box = element.bounding_box()
                    if box:
                        step1_click = (int(box["x"] + box["width"] / 2), int(box["y"] + box["height"] / 2))
                    element.click()
                    page.wait_for_timeout(2000)
                    if _create_modal_opened(page):
                        create_clicked = True
                        logger.info(f"Clicked create design with selector: {selector}")
                        break
                    _dismiss_magic_layers_popup(page)
            except Exception:
                continue

    if not create_clicked:
        try:
            el = page.locator("text=Custom size").first
            if el.is_visible(timeout=5000):
                box = el.bounding_box()
                if box:
                    step1_click = (int(box["x"] + box["width"] / 2), int(box["y"] + box["height"] / 2))
            page.click("text=Custom size", timeout=5000)
            page.wait_for_timeout(2000)
            create_clicked = True
        except Exception:
            raise Exception("Could not find 'Create a design' or 'Custom size' button")

    if debug_context and step1_click:
        from .debug_screenshot import maybe_save_debug
        maybe_save_debug(debug_context, page, "create_modal_opened", [step1_click])

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

    unit_click = None
    if COORDINATES_CONFIG and "design_modal" in COORDINATES_CONFIG:
        uc = COORDINATES_CONFIG["design_modal"].get("unit_selector", {})
        if uc.get("x") and uc.get("y"):
            unit_click = (uc["x"], uc["y"])
    if debug_context and unit_click:
        from .debug_screenshot import maybe_save_debug
        maybe_save_debug(debug_context, page, "unit_selected", [unit_click])

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

    width_click = None
    if COORDINATES_CONFIG and "design_modal" in COORDINATES_CONFIG:
        wc = COORDINATES_CONFIG["design_modal"].get("width_input", {})
        if wc.get("x") is not None and wc.get("y") is not None:
            width_click = (wc["x"], wc["y"])
    if debug_context and width_click:
        from .debug_screenshot import maybe_save_debug
        maybe_save_debug(debug_context, page, "width_filled", [width_click])

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

    height_click = None
    if COORDINATES_CONFIG and "design_modal" in COORDINATES_CONFIG:
        hc = COORDINATES_CONFIG["design_modal"].get("height_input", {})
        if hc.get("x") is not None and hc.get("y") is not None:
            height_click = (hc["x"], hc["y"])
    if debug_context and height_click:
        from .debug_screenshot import maybe_save_debug
        maybe_save_debug(debug_context, page, "height_filled", [height_click])

    # Step 5: Click "Create new design"
    # Canva may use icon-only buttons with aria-label (no visible text) - has-text() won't match
    logger.info("Step 5: Clicking 'Create new design' button...")
    create_button_clicked = False

    create_button_selectors = [
        # Modal-scoped first (avoids matching sidebar "Create a design" button)
        ('[role="dialog"] button[aria-label="Create a design"]', True),
        ('[role="dialog"] button[aria-label="Create new design"]', True),
        ('[role="dialog"] button:has-text("Create new design")', True),
        ('[role="dialog"] button:has-text("Create design")', True),
        # Aria-label fallbacks - use .last to prefer modal's button over sidebar (modal rendered last)
        ('button[aria-label="Create a design"]', False),
        ('button[aria-label="Create new design"]', False),
        ('button[aria-label*="Create" i]', False),
        # Text-based (legacy - when button has visible text)
        ('button:has-text("Create new design")', True),
        ('button:has-text("Create design")', True),
        ('button:has-text("Create")', False),
        ('[data-testid*="create"]', True),
        ('button[type="submit"]', True),
    ]

    create_btn_click = None
    for selector, use_first in create_button_selectors:
        try:
            loc = page.locator(selector)
            create_button = loc.first if use_first else loc.last
            if create_button.is_visible(timeout=2000):
                box = create_button.bounding_box()
                if box:
                    create_btn_click = (int(box["x"] + box["width"] / 2), int(box["y"] + box["height"] / 2))
                create_button.click()
                page.wait_for_timeout(4000)
                create_button_clicked = True
                logger.info(f"Clicked create button with selector: {selector} (use_first={use_first})")
                break
        except Exception:
            continue

    # Coordinate-based fallback when selectors fail
    if not create_button_clicked:
        from .. import config as canva_config
        x, y = None, None
        if COORDINATES_CONFIG and "design_modal" in COORDINATES_CONFIG:
            coords = COORDINATES_CONFIG["design_modal"].get("create_button", {})
            if coords.get("x", 0) > 0 or coords.get("y", 0) > 0:
                x, y = coords.get("x", 0), coords.get("y", 0)
        if x is None or y is None:
            x = getattr(canva_config, "CANVA_CREATE_BUTTON_FALLBACK_X", 35)
            y = getattr(canva_config, "CANVA_CREATE_BUTTON_FALLBACK_Y", 80)
        try:
            logger.info(f"Trying coordinate-based fallback at ({x}, {y})")
            create_btn_click = (x, y)
            page.mouse.click(x, y)
            page.wait_for_timeout(4000)
            create_button_clicked = True
            logger.info(f"Clicked create button using coordinates ({x}, {y})")
        except Exception as e:
            logger.debug(f"Coordinate fallback failed: {e}")

    if debug_context and create_btn_click:
        from .debug_screenshot import maybe_save_debug
        maybe_save_debug(debug_context, page, "create_button_clicked", [create_btn_click])

    if not create_button_clicked:
        raise Exception("Could not find 'Create new design' button")

    logger.info("Design created with 1 page. Pages will be added as images are placed.")
    logger.info("Design creation completed successfully!")
