"""Playwright automation for Midjourney.com/imagine.

Connect via CDP to existing Brave browser. User must be logged in to Midjourney before starting.

Selectors may need updates if Midjourney changes their UI. Discover via browser DevTools.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import httpx

if TYPE_CHECKING:
    from playwright.sync_api import Locator

from integrations.midjourney.automation.browser_config import DEBUG_FOLDER, DEBUG_PORT
from integrations.midjourney.utils.image_utils import build_image_path
from integrations.midjourney.utils.logging_config import logger

# Selectors - update if Midjourney.com UI changes. Top 4 images = current generation.
SELECTORS = {
    "prompt_input": '[placeholder*="imagine" i], [placeholder*="what will you imagine" i], textarea[placeholder]',
    "submit_button": 'button[type="submit"], button:has-text("Submit"), button:has-text("Create"), [aria-label*="submit" i]',
    "image_grid": '[data-testid="image-grid"], .image-grid, [class*="grid"] img, img[src*="cdn.midjourney"]',
    "image_thumbnail": 'img[src*="cdn.midjourney.com"]',
    "progress_indicator": '[class*="progress"], [class*="loading"], [aria-busy="true"]',
    "context_menu": "#contextMenu",
    "upscale_subtle": 'button:has-text("Subtle")',
    "download_icon": '[aria-label*="download" i], button:has-text("Download"), a[download]',
    "detail_view": '[role="dialog"], [class*="modal"], [class*="lightbox"]',
    "back_button": 'button:has-text("Back"), button:has-text("Close"), [aria-label*="back" i], [aria-label*="close" i]',
    "queue_indicator": 'text=/\\d+\\s*queued\\s*jobs?/i',
    "queue_error": 'text=/Too many queued jobs/i',
}

DOWNLOAD_SELECTORS = [
    '[aria-label*="Download Image" i]',
    '[aria-label*="Download" i]',
    '[title*="Download Image" i]',
    '[title*="Download" i]',
    'a[download]',
    'button:has-text("Download")',
]

MIDJOURNEY_IMAGINE_URL = "https://www.midjourney.com/imagine"
WAIT_FOR_IMAGES_TIMEOUT_MS = 120_000  # 2 min
WAIT_FOR_UPSCALE_MS = 60_000  # 1 min
WAIT_BEFORE_UPSCALE_S = 90
WAIT_AFTER_UPSCALE_S = 90
CLICK_DELAY_MS = 500
WAIT_DETAIL_VIEW_READY_S = 2  # wait for detail view to fully load before clicking buttons
WAIT_AFTER_UPSCALE_CLICK_S = 1  # wait for upscale click to register before next image
WAIT_AFTER_ARROWRIGHT_S = 1  # wait for next image to load in detail view


class MidjourneyWebController:
    """Playwright-based controller for Midjourney.com web interface."""

    def __init__(
        self,
        debug_port: int = DEBUG_PORT,
        dry_run: bool = False,
        button_coordinates: dict[str, list[int]] | None = None,
        viewport: dict[str, int] | None = None,
        coordinates_viewport: dict[str, int] | None = None,
        debug_show_clicks: bool = False,
        waits: dict[str, int | float] | None = None,
    ) -> None:
        self.debug_port = debug_port
        self.dry_run = dry_run
        self.button_coordinates = button_coordinates or {}
        self.viewport = viewport or {"width": 1920, "height": 1080}
        self.coordinates_viewport = coordinates_viewport or {"width": 1920, "height": 1080}
        self.debug_show_clicks = debug_show_clicks
        self._waits = waits or {}
        self.playwright = None
        self.browser = None
        self.page = None

    def _w(self, key: str, default: int | float) -> int | float:
        """Get wait value from config, fallback to default."""
        return self._waits.get(key, default)

    def _show_click_overlay(self, x: int, y: int, label: str = "") -> None:
        """Inject a red circle at (x,y) for 1.5s. Only when debug_show_clicks is True."""
        if not self.debug_show_clicks or self.dry_run or not self.page:
            return
        self.page.evaluate(
            """
            ([x, y, label]) => {
                const el = document.createElement('div');
                el.id = 'mj-debug-click-overlay';
                el.style.cssText = `
                    position: fixed; left: ${x-25}px; top: ${y-25}px; width: 50px; height: 50px;
                    border: 3px solid red; border-radius: 50%; background: rgba(255,0,0,0.2);
                    pointer-events: none; z-index: 999999; box-shadow: 0 0 10px red;
                `;
                if (label) {
                    const lbl = document.createElement('span');
                    lbl.textContent = label;
                    lbl.style.cssText = 'position: absolute; bottom: -18px; left: 50%; transform: translateX(-50%); font-size: 11px; color: red; white-space: nowrap;';
                    el.appendChild(lbl);
                }
                document.body.appendChild(el);
                setTimeout(() => el.remove(), 1500);
            }
            """,
            [x, y, label],
        )
        time.sleep(self._w("click_overlay_sec", 1.5))

    def _scale_coord(self, x: int | float, y: int | float) -> tuple[int, int]:
        """Scale coordinates from coordinates_viewport to viewport."""
        ref_w = self.coordinates_viewport.get("width", 1920)
        ref_h = self.coordinates_viewport.get("height", 1080)
        tgt_w = self.viewport.get("width", 1920)
        tgt_h = self.viewport.get("height", 1080)
        if ref_w == tgt_w and ref_h == tgt_h:
            return int(x), int(y)
        return int(x * tgt_w / ref_w), int(y * tgt_h / ref_h)

    def connect(self) -> None:
        """Connect to existing browser via CDP."""
        if self.dry_run:
            logger.info("[DRY RUN] Would connect to browser on port %s", self.debug_port)
            return

        import asyncio
        import sys

        # Windows: ProactorEventLoop required for Playwright subprocess support.
        # SelectorEventLoop raises NotImplementedError on create_subprocess_exec.
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        from playwright.sync_api import sync_playwright

        self.playwright = sync_playwright().start()
        try:
            self.browser = self.playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{self.debug_port}"
            )
        except Exception:
            self.browser = self.playwright.chromium.connect_over_cdp(
                f"http://localhost:{self.debug_port}"
            )
        contexts = self.browser.contexts
        if contexts:
            ctx = contexts[0]
            self.page = ctx.new_page()
        else:
            self.page = self.browser.new_page()
        w = self.viewport.get("width", 1920)
        h = self.viewport.get("height", 1080)
        self.page.set_viewport_size({"width": w, "height": h})
        logger.info("Connected to browser on port %s (viewport %dx%d)", self.debug_port, w, h)

    def close(self) -> None:
        """Close browser connection."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.playwright = None
        self.browser = None
        self.page = None

    def capture_detail_view_screenshot(self, output_path: Path) -> Path:
        """Capture screenshot of detail view for coordinate discovery. Caller must have detail view open."""
        if self.dry_run:
            logger.info("[DRY RUN] Would capture screenshot to %s", output_path)
            return output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(output_path))
        logger.info("Screenshot saved to %s — use it to fill button_coordinates in config.json", output_path)
        return output_path

    def _get_image_url_from_detail_view(self, image_index: int = 0) -> str | None:
        """Extract the full-size image or download URL from the detail view. Returns None if not found.

        Scopes search to the detail view only (not the grid behind it). Uses image_index for carousels
        where multiple images exist in the DOM.
        """
        if self.dry_run or not self.page:
            return None
        detail = self.page.locator(SELECTORS["detail_view"]).first
        if detail.count() == 0:
            return None
        imgs = detail.locator('img[src*="cdn.midjourney.com"]')
        links = None
        for sel in DOWNLOAD_SELECTORS:
            loc = detail.locator(sel)
            if loc.count() > 0:
                links = loc
                break
        idx = min(image_index, imgs.count() - 1) if imgs.count() > 0 else 0
        if links and links.count() > 0:
            link_idx = min(image_index, links.count() - 1)
            try:
                href = links.nth(link_idx).get_attribute("href")
                if href and ("cdn.midjourney" in href or "midjourney.com" in href):
                    if href.startswith("/"):
                        return "https://www.midjourney.com" + href
                    return href
            except Exception:
                pass
        if imgs.count() > 0:
            try:
                src = imgs.nth(idx).get_attribute("src")
                if src:
                    return src
            except Exception:
                pass
        return None

    UUID_PATTERN = re.compile(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )
    JOBS_URL_PATTERN = re.compile(
        r"https?://(?:www\.)?midjourney\.com/jobs/[0-9a-fA-F-]+(?:\?index=\d+)?",
        re.I,
    )

    def _is_jobs_url(self, url: str) -> bool:
        """True if url is a Midjourney jobs page (e.g. https://www.midjourney.com/jobs/{uuid}?index=0)."""
        return bool(url and self.JOBS_URL_PATTERN.search(url))

    def _extract_job_id_from_url(self, url: str) -> str | None:
        """Extract Midjourney job ID (UUID) from a CDN or page URL. Returns None if not found."""
        if not url:
            return None
        match = self.UUID_PATTERN.search(url)
        return match.group(0) if match else None

    def _build_jobs_nav_url(self, url: str) -> str | None:
        """Build jobs URL for navigation. If url is already a jobs URL, return as-is.
        Else extract job_id from CDN/page URL and build jobs/{id}?index=0.
        """
        if not url:
            return None
        if self._is_jobs_url(url):
            return url
        job_id = self._extract_job_id_from_url(url)
        if not job_id:
            return None
        return f"https://www.midjourney.com/jobs/{job_id}?index=0"

    def _navigate_to_image_by_url(self, url: str) -> bool:
        """Navigate to Midjourney jobs page to open the image's detail view.

        Uses https://www.midjourney.com/jobs/{jobId}?index={n} (not imagine?jobId=).
        If url is already a jobs URL, uses it directly. Else extracts job_id from CDN URL.
        Retries once on failure. Returns True if detail view appears, False otherwise.
        """
        if self.dry_run or not self.page or not url:
            return False
        nav_url = self._build_jobs_nav_url(url)
        if not nav_url:
            logger.warning("Could not build jobs URL from: %s", url[:80])
            return False
        retry_delay = self._w("navigate_retry_delay_sec", 2)
        for attempt in range(2):
            try:
                timeout_ms = int(self._w("page_load_timeout_ms", 30000))
                self.page.goto(nav_url, wait_until="domcontentloaded", timeout=timeout_ms)
                time.sleep(self._w("after_navigate_sec", 2))
                detail = self.page.locator(SELECTORS["detail_view"]).first
                detail.wait_for(state="visible", timeout=10000)
                job_id = self._extract_job_id_from_url(nav_url) or "?"
                logger.info(
                    "Resumed via URL navigation (jobId=%s) -> %s",
                    job_id[:8] if job_id != "?" else job_id,
                    nav_url[:60],
                )
                return True
            except Exception as e:
                logger.warning(
                    "Navigate to image by URL failed%s: %s",
                    f" (attempt {attempt + 1}/2)" if attempt == 0 else "",
                    e,
                )
                if attempt == 0:
                    time.sleep(retry_delay)
        return False

    def _normalize_image_id(self, url: str) -> str:
        """Extract stable identifier for matching grid thumbnail vs detail URL.

        Midjourney CDN URLs may differ (e.g. query params for thumbnails).
        We normalize by removing query params and extracting the path.
        """
        if not url:
            return ""
        base = url.split("?")[0]
        match = re.search(r"cdn\.midjourney\.com([^?#]+)", base, re.I)
        if match:
            return match.group(1)
        match = re.search(r"midjourney\.com([^?#]+)", base, re.I)
        if match:
            return match.group(1)
        return base

    def _find_grid_image_by_url(self, url: str) -> tuple["Locator | None", str | None]:
        """Find grid image whose src matches url. Tries normalized path first, then job ID (UUID).
        Returns (locator, match_type) where match_type is 'url', 'job_id', or None.
        """
        if self.dry_run or not self.page or not url:
            return (None, None)
        imgs = self.page.locator(SELECTORS["image_thumbnail"])
        target_id = self._normalize_image_id(url)
        if target_id:
            for i in range(imgs.count()):
                try:
                    src = imgs.nth(i).get_attribute("src")
                    if src and self._normalize_image_id(src) == target_id:
                        return (imgs.nth(i), "url")
                except Exception:
                    continue
        job_id = self._extract_job_id_from_url(url)
        if job_id:
            for i in range(imgs.count()):
                try:
                    src = imgs.nth(i).get_attribute("src")
                    if src and job_id in src:
                        return (imgs.nth(i), "job_id")
                except Exception:
                    continue
        return (None, None)

    def _download_via_httpx(self, url: str, dest: Path, page=None) -> bool:
        """Download image from URL via httpx. Returns True on success.

        When page is provided, uses browser cookies and headers (Referer, User-Agent)
        to satisfy CDN requirements that block bare requests (403).
        """
        if self.dry_run:
            return False
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            headers = {
                "Referer": "https://www.midjourney.com/imagine",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            cookies: dict[str, str] = {}
            if page:
                try:
                    raw = page.context.cookies(
                        urls=["https://www.midjourney.com", "https://cdn.midjourney.com"]
                    )
                    cookies = {c["name"]: c["value"] for c in raw}
                except Exception:
                    pass
            timeout_sec = self._w("download_timeout_ms", 15000) / 1000
            with httpx.Client(timeout=timeout_sec, follow_redirects=True) as client:
                resp = client.get(url, headers=headers, cookies=cookies or None)
                resp.raise_for_status()
                dest.write_bytes(resp.content)
            logger.info("Downloaded via httpx to %s (%d bytes)", dest, dest.stat().st_size)
            return True
        except Exception as e:
            logger.warning("httpx download failed: %s", e)
            return False

    def _download_image(self, output_folder: Path, dest: Path, image_index: int = 0) -> bool:
        """Download current image: try URL extraction + httpx first, fall back to click + expect_download."""
        if self.dry_run:
            return False
        url = self._get_image_url_from_detail_view(image_index)
        if url and self._download_via_httpx(url, dest, self.page):
            return True
        for attempt in range(2):
            try:
                if hasattr(self.page.context, "set_default_download_path"):
                    self.page.context.set_default_download_path(str(output_folder))
                download_timeout_ms = int(self._w("download_timeout_ms", 15000))
                with self.page.expect_download(timeout=download_timeout_ms) as download_info:
                    self._click_download_button(output_folder)
                download = download_info.value
                download.save_as(str(dest))
                size = dest.stat().st_size if dest.exists() else 0
                if size < 100:
                    dest.unlink(missing_ok=True)
                    logger.warning("Download produced empty/truncated file (%d bytes)%s", size, ", retrying" if attempt == 0 else "")
                    if attempt == 0:
                        time.sleep(2)
                        continue
                    return False
                logger.info("Downloaded via browser to %s (%d bytes)", dest, size)
                return True
            except Exception as e:
                logger.warning("Download failed%s: %s", " (retrying)" if attempt == 0 else "", e)
                if attempt == 0:
                    time.sleep(2)
                    continue
                return False
        return False

    def _click_download_button(self, output_folder: Path) -> None:
        """Click download button: try selectors first, fall back to coordinates. Sets default download path when available (CDP contexts may not support it). Raises if no button found."""
        if self.dry_run:
            return
        if hasattr(self.page.context, "set_default_download_path"):
            self.page.context.set_default_download_path(str(output_folder))
        for sel in DOWNLOAD_SELECTORS:
            loc = self.page.locator(sel).first
            if loc.count() > 0:
                try:
                    loc.wait_for(state="visible", timeout=1000)
                    loc.click()
                    logger.info("Download via selector: %s", sel[:40])
                    return
                except Exception:
                    continue
        coords = self.button_coordinates.get("download")
        if coords and len(coords) >= 2 and not (coords[0] == 0 and coords[1] == 0):
            x, y = self._scale_coord(coords[0], coords[1])
            self._show_click_overlay(x, y, "download")
            self.page.mouse.click(x, y)
            logger.info("Download via coordinates %s,%s (scaled to %s,%s)", coords[0], coords[1], x, y)
            return
        raise ValueError("No download button found (selector or coordinates)")

    def navigate_to_imagine(self) -> None:
        """Navigate to Midjourney imagine page."""
        if self.dry_run:
            logger.info("[DRY RUN] Would navigate to %s", MIDJOURNEY_IMAGINE_URL)
            return
        timeout_ms = int(self._w("page_load_timeout_ms", 30000))
        self.page.goto(MIDJOURNEY_IMAGINE_URL, wait_until="domcontentloaded", timeout=timeout_ms)
        time.sleep(self._w("after_navigate_sec", 2))

    def get_queue_count(self) -> int | None:
        """Parse current queued jobs from the queue indicator ('X queued jobs').
        Returns the count if found. If the indicator is not visible or absent, treats as queue empty (0).
        Returns None only if the element exists but parsing fails.
        """
        if self.dry_run or not self.page:
            return 0
        try:
            loc = self.page.get_by_text(re.compile(r"\d+\s*queued\s*jobs?", re.I)).first
            if loc.count() == 0:
                return 0  # Element absent = queue empty, indicator hidden
            if not loc.is_visible():
                return 0
            text = loc.text_content() or ""
            match = re.search(r"(\d+)", text)
            return int(match.group(1)) if match else None
        except Exception:
            return None

    def has_queue_error(self) -> bool:
        """True if 'Too many queued jobs' error is visible."""
        if self.dry_run or not self.page:
            return False
        try:
            err = self.page.get_by_text("Too many queued jobs", exact=False).first
            return err.count() > 0 and err.is_visible()
        except Exception:
            return False

    def wait_until_queue_empty(
        self,
        progress_callback: Callable[[int | None], None],
        stop_check: Callable[[], bool],
        poll_interval_sec: float = 5,
        max_wait_sec: float = 600,
    ) -> bool:
        """Poll until queue count is 0 or element gone. Returns True when ready, False on timeout or stop.
        After 3 consecutive None from get_queue_count, treats as ready (selector may have changed).
        """
        if self.dry_run:
            progress_callback(0)
            return True
        start = time.time()
        none_count = 0
        NONE_FALLBACK_THRESHOLD = 3
        while (time.time() - start) < max_wait_sec:
            if stop_check():
                return False
            count = self.get_queue_count()
            progress_callback(count)
            if count == 0:
                logger.info("Queue empty after %.1fs", time.time() - start)
                return True
            if count is None:
                none_count += 1
                if none_count >= NONE_FALLBACK_THRESHOLD:
                    logger.info("Queue indicator unavailable after %d polls, assuming ready", none_count)
                    return True
            else:
                none_count = 0
            time.sleep(poll_interval_sec)
        logger.warning("wait_until_queue_empty timed out after %.1fs", max_wait_sec)
        return False

    def submit_prompt(self, prompt: str) -> None:
        """Enter prompt and submit."""
        if self.dry_run:
            logger.info("[DRY RUN] Would submit prompt: %s", prompt[:60])
            return

        input_el = self.page.locator(SELECTORS["prompt_input"]).first
        input_el.wait_for(state="visible", timeout=10000)
        input_el.scroll_into_view_if_needed()
        time.sleep(self._w("input_fill_delay_sec", 0.2))
        input_el.fill("")
        input_el.fill(prompt)
        time.sleep(self._w("input_submit_delay_sec", 0.3))

        submit = self.page.locator(SELECTORS["submit_button"]).first
        if submit.count() > 0:
            submit.click()
        else:
            self.page.keyboard.press("Control+Enter")
        logger.info("Submitted prompt: %s", prompt[:60])

    def wait_for_4_images(self, timeout_ms: int | None = None) -> bool:
        """Wait for generation to complete. Uses progress indicator (top left of first image) or fallback."""
        if self.dry_run:
            logger.info("[DRY RUN] Would wait for 4 images")
            time.sleep(1)
            return True

        if timeout_ms is None:
            timeout_ms = int(self._w("wait_for_images_timeout_sec", 120) * 1000)
        start = time.time()
        progress = self.page.locator(SELECTORS["progress_indicator"]).first

        try:
            progress.wait_for(state="visible", timeout=10000)
            logger.info("Progress indicator visible, waiting for generation to complete")
            progress.wait_for(state="hidden", timeout=timeout_ms)
            elapsed = time.time() - start
            logger.info("Generation complete after %.1fs", elapsed)
            return True
        except Exception:
            pass

        time.sleep(self._w("images_fallback_first_sec", 65))
        poll_sec = self._w("images_fallback_poll_sec", 5)
        while (time.time() - start) * 1000 < timeout_ms:
            imgs = self.page.locator(SELECTORS["image_thumbnail"])
            if imgs.count() >= 4:
                logger.info("Fallback: found %d images after %.1fs", imgs.count(), time.time() - start)
                return True
            time.sleep(poll_sec)
        logger.error("Timeout waiting for 4 images")
        return False

    def upscale_all_4(self, output_folder: Path | None = None) -> None:
        """Upscale each of top 4 images via coordinate-based clicks. Left-click first image → detail view → upscale_subtle × 4, ArrowRight between."""
        if self.dry_run:
            logger.info("[DRY RUN] Would upscale all 4 images")
            return

        imgs = self.page.locator(SELECTORS["image_thumbnail"])
        if imgs.count() < 4:
            logger.warning("Fewer than 4 images found for upscale")
            return

        coords = self.button_coordinates.get("upscale_subtle")
        if not coords or len(coords) < 2 or (coords[0] == 0 and coords[1] == 0):
            imgs.nth(0).click()
            time.sleep(2)
            detail = self.page.locator(SELECTORS["detail_view"]).first
            try:
                detail.wait_for(state="visible", timeout=5000)
            except Exception:
                pass
            out = (output_folder or DEBUG_FOLDER) / "detail_view_screenshot.png"
            self.capture_detail_view_screenshot(out)
            logger.warning(
                "button_coordinates.upscale_subtle not configured. Screenshot saved. "
                "Fill config.json with [x, y] and re-run."
            )
            self.page.keyboard.press("Escape")
            time.sleep(1)
            return

        try:
            imgs.nth(0).click()
            time.sleep(2)

            detail = self.page.locator(SELECTORS["detail_view"]).first
            detail.wait_for(state="visible", timeout=5000)
            time.sleep(self._w("detail_view_ready_sec", 2))

            x, y = self._scale_coord(coords[0], coords[1])
            for i in range(4):
                self.page.mouse.click(x, y)
                logger.info("Upscale Subtle for image %d (coords %d,%d)", i + 1, x, y)
                time.sleep(self._w("after_upscale_click_sec", 1))
                if i < 3:
                    self.page.keyboard.press("ArrowRight")
                    time.sleep(self._w("after_arrow_right_sec", 1))

            self.page.keyboard.press("Escape")
            time.sleep(1)
        except Exception as e:
            logger.error("Upscale flow failed: %s", e)

    def wait_for_upscaled(self, timeout_ms: int | None = None) -> None:
        """Wait for upscaled images to appear."""
        if self.dry_run:
            logger.info("[DRY RUN] Would wait for upscaled images")
            time.sleep(1)
            return
        time.sleep(self._w("wait_for_upscaled_sec", 15))
        # Could add polling for larger image elements if needed

    def upscale_first_n(self, count: int) -> None:
        """Upscale the first N images. Delegates to click_button_first_n."""
        self.click_button_first_n("upscale_subtle", count)

    def click_button_first_n(
        self,
        button_keys: str | list[str],
        count: int,
        output_folder: Path | None = None,
        stem: str = "ui_batch",
        stop_check: Callable[[], bool] | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
        start_index: int = 0,
        last_processed_url: str | None = None,
        keep_detail_view_open: bool = False,
        resume_from_detail_view: bool = False,
    ) -> tuple[list[Path] | None, str | None]:
        """Click Creation Actions button(s) for images. Returns (paths for download or None, last_processed_url).

        If last_processed_url is provided (for batch resume): tries navigate-to-URL first (jobs/{id}?index={n}).
        If that opens the detail view, ArrowRight once and continue. Else falls back to grid lookup by URL
        or job ID, then position-based (first image + start_index ArrowRight).

        Prefer storing page.url (jobs URL) when in detail view for reliable resume; falls back to image URL.

        keep_detail_view_open: if True, do not press Escape (caller needs to see queue). For upscale batches
        we always close so the queue is visible; download phase does not use this.
        """
        keys = [button_keys] if isinstance(button_keys, str) else list(button_keys)
        if not keys:
            return (None, None)

        if self.dry_run:
            logger.info("[DRY RUN] Would click %s for %d images", keys, count)
            return ([] if "download" in keys else None, None)

        for key in keys:
            coords = self.button_coordinates.get(key)
            if not coords or len(coords) < 2 or (coords[0] == 0 and coords[1] == 0):
                logger.warning("button_coordinates.%s not configured", key)
                return ([] if key == "download" else None, None)

        imgs = self.page.locator(SELECTORS["image_thumbnail"])
        if imgs.count() < 1 and not resume_from_detail_view:
            logger.warning("No images found")
            return ([] if "download" in keys else None, None)

        paths: list[Path] = [] if "download" in keys else []
        out_folder = output_folder or Path(".")
        last_url: str | None = None

        try:
            if last_processed_url:
                opened = self._navigate_to_image_by_url(last_processed_url)
                if opened:
                    detail = self.page.locator(SELECTORS["detail_view"]).first
                    time.sleep(self._w("detail_view_ready_sec", 2))
                    try:
                        detail.focus()
                    except Exception:
                        pass
                    self.page.keyboard.press("ArrowRight")
                    time.sleep(self._w("after_arrow_right_sec", 1))
                else:
                    img_loc, match_type = self._find_grid_image_by_url(last_processed_url)
                    if img_loc is not None:
                        logger.info(
                            "Resumed via grid lookup (matched by %s)",
                            match_type or "url",
                        )
                        img_loc.scroll_into_view_if_needed()
                        img_loc.click()
                        time.sleep(2)
                        detail = self.page.locator(SELECTORS["detail_view"]).first
                        detail.wait_for(state="visible", timeout=5000)
                        time.sleep(self._w("detail_view_ready_sec", 2))
                        try:
                            detail.focus()
                        except Exception:
                            pass
                        self.page.keyboard.press("ArrowRight")
                        time.sleep(self._w("after_arrow_right_sec", 1))
                    else:
                        logger.info(
                            "Resumed via position fallback (start_index=%d)",
                            start_index,
                        )
                        grid_order = str(
                            self._waits.get("grid_order", "newest_first")
                        ).lower()
                        total = imgs.count()
                        if grid_order == "oldest_first" and start_index < total:
                            imgs.nth(start_index).click()
                        elif grid_order == "newest_first" and total > 0:
                            idx = max(0, total - 1 - start_index)
                            imgs.nth(idx).click()
                        else:
                            imgs.nth(0).click()
                        time.sleep(2)
                        detail = self.page.locator(SELECTORS["detail_view"]).first
                        detail.wait_for(state="visible", timeout=5000)
                        time.sleep(self._w("detail_view_ready_sec", 2))
                        if grid_order not in ("oldest_first", "newest_first"):
                            for _ in range(start_index):
                                try:
                                    detail.focus()
                                except Exception:
                                    pass
                                self.page.keyboard.press("ArrowRight")
                                time.sleep(self._w("after_arrow_right_sec", 1))
            else:
                imgs.nth(0).click()
                time.sleep(2)
                detail = self.page.locator(SELECTORS["detail_view"]).first
                detail.wait_for(state="visible", timeout=5000)
                time.sleep(self._w("detail_view_ready_sec", 2))
                for _ in range(start_index):
                    try:
                        detail.focus()
                    except Exception:
                        pass
                    self.page.keyboard.press("ArrowRight")
                    time.sleep(self._w("after_arrow_right_sec", 1))

            prev_url: str | None = None
            for i in range(count):
                if stop_check and stop_check():
                    logger.info("Stopped by user at image %d/%d", i + 1, count)
                    break
                for button_key in keys:
                    if stop_check and stop_check():
                        break
                    coords = self.button_coordinates.get(button_key)
                    if not coords or len(coords) < 2:
                        continue
                    x, y = self._scale_coord(coords[0], coords[1])

                    if button_key == "download":
                        dest = build_image_path(out_folder, stem, 1, start_index + i + 1)
                        if i > 0 and prev_url:
                            for _ in range(8):
                                url = self._get_image_url_from_detail_view(0)
                                if url and url != prev_url:
                                    break
                                time.sleep(1)
                        if i > 0:
                            time.sleep(1)
                        if self._download_image(out_folder, dest, image_index=0):
                            paths.append(dest)
                            prev_url = self._get_image_url_from_detail_view(0)
                            logger.info("%s image %d/%d -> %s", button_key, i + 1, count, dest)
                        else:
                            logger.warning("Download failed for image %d", i + 1)
                        if progress_callback:
                            progress_callback(i + 1, count)
                    else:
                        for click_attempt in range(3):
                            try:
                                self._show_click_overlay(x, y, button_key)
                                self.page.mouse.click(x, y)
                                logger.info("%s image %d/%d%s", button_key, i + 1, count, f" (retry {click_attempt})" if click_attempt > 0 else "")
                                break
                            except Exception as e:
                                logger.warning("%s click failed for image %d%s: %s", button_key, i + 1, f" (attempt {click_attempt + 1}/3)" if click_attempt < 2 else "", e)
                                if click_attempt < 2:
                                    time.sleep(2)
                                else:
                                    raise

                    time.sleep(self._w("after_upscale_click_sec", 1))

                if i < count - 1:
                    try:
                        detail.focus()
                    except Exception:
                        pass
                    self.page.keyboard.press("ArrowRight")
                    time.sleep(self._w("after_arrow_right_sec", 1))
                    if "download" in keys:
                        time.sleep(1.5)
                        try:
                            img = detail.locator('img[src*="cdn.midjourney.com"]').first
                            img.wait_for(state="visible", timeout=5000)
                        except Exception:
                            pass

            page_url = self.page.url if self.page else ""
            last_url = (
                page_url
                if self._is_jobs_url(page_url)
                else self._get_image_url_from_detail_view(0)
            )
            if not keep_detail_view_open:
                self.page.keyboard.press("Escape")
                time.sleep(1)
            if "download" in keys and progress_callback:
                progress_callback(count, count)
        except Exception as e:
            logger.error("click_button_first_n (%s) failed: %s", keys, e)

        return (paths if "download" in keys else None, last_url)

    def download_first_n(
        self,
        count: int,
        output_folder: Path,
        stem: str = "ui_batch",
    ) -> list[Path]:
        """Download the first N images. Delegates to click_button_first_n."""
        result, _ = self.click_button_first_n("download", count, output_folder, stem)
        return result or []

    def download_upscaled_only(
        self,
        count: int,
        output_folder: Path,
        prompt: str,
        attempt: int = 1,
    ) -> list[Path]:
        """Scroll up, click first upscaled image, then download each via coordinate click + ArrowRight."""
        if self.dry_run:
            logger.info("[DRY RUN] Would download %d upscaled images to %s", count, output_folder)
            return [build_image_path(output_folder, prompt, attempt, i + 1) for i in range(count)]

        paths: list[Path] = []
        try:
            self.page.evaluate("window.scrollBy(0, -800)")
            time.sleep(1)

            imgs = self.page.locator(SELECTORS["image_thumbnail"])
            if imgs.count() < 1:
                logger.warning("No images found for download")
                return paths

            imgs.nth(0).click()
            time.sleep(2)

            detail = self.page.locator(SELECTORS["detail_view"]).first
            detail.wait_for(state="visible", timeout=5000)

            for i in range(count):
                dest = build_image_path(output_folder, prompt, attempt, i + 1)
                if self._download_image(output_folder, dest):
                    paths.append(dest)
                    logger.info("Downloaded upscale %d to %s", i + 1, dest)
                else:
                    logger.warning("Download failed for upscale %d", i + 1)

                if i < count - 1:
                    self.page.keyboard.press("ArrowRight")
                    time.sleep(1)

            self.page.keyboard.press("Escape")
            time.sleep(1)
        except Exception as e:
            logger.error("Download upscaled flow failed: %s", e)

        return paths

    def process_prompt(
        self,
        prompt: str,
        output_folder: Path,
        attempt: int = 1,
    ) -> list[Path]:
        """Full flow: submit, wait, upscale via coords, wait 90s, download upscales only."""
        self.submit_prompt(prompt)
        if not self.wait_for_4_images():
            return []
        if not self.dry_run:
            wait_before = int(self._w("wait_before_upscale_sec", 90))
            logger.info("Waiting %ds for new images before upscale", wait_before)
            time.sleep(wait_before)
        self.upscale_all_4(output_folder=output_folder)
        if not self.dry_run:
            wait_after = int(self._w("wait_after_upscale_sec", 90))
            logger.info("Waiting %ds for upscales to complete", wait_after)
            time.sleep(wait_after)
        return self.download_upscaled_only(
            count=4,
            output_folder=output_folder,
            prompt=prompt,
            attempt=attempt,
        )
