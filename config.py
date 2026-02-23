"""Centralized configuration for Coloring Book Assistant."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = Path(os.getenv("CB_OUTPUT_DIR", str(PROJECT_ROOT)))
# Use saved_designs at project root for backward compatibility
SAVED_DESIGNS_DIR = OUTPUT_DIR / "saved_designs"
PINTEREST_PUBLISH_DIR = OUTPUT_DIR / "pinterest_publish"
GENERATED_IMAGES_DIR = OUTPUT_DIR / "generated_images"
SAVED_DESIGN_PACKAGES_DIR = OUTPUT_DIR / "saved_design_packages"

# -----------------------------------------------------------------------------
# LLM Models (performance-optimized per task)
# Override via env: CB_DESIGN_EVALUATOR_MODEL, CB_CONTENT_MODEL, etc.
# -----------------------------------------------------------------------------
DESIGN_EVALUATOR_MODEL = os.getenv("CB_DESIGN_EVALUATOR_MODEL", "gpt-4.1-mini")
CONTENT_MODEL = os.getenv("CB_CONTENT_MODEL", "gpt-5-mini")
EXECUTOR_MODEL = os.getenv("CB_EXECUTOR_MODEL", "gpt-5-mini")
PINTEREST_MODEL = os.getenv("CB_PINTEREST_MODEL", "gpt-4.1-mini")
GUIDE_CHAT_MODEL = os.getenv("CB_GUIDE_CHAT_MODEL", "gpt-4.1-mini")
IMAGE_EVALUATOR_MODEL = os.getenv("CB_IMAGE_EVALUATOR_MODEL", "gpt-5-mini")

# Image quality evaluator persistence
IMAGE_EVALUATIONS_FILE = "image_evaluations.json"

# Midjourney config (integrated from midjourney_agent config.json)
# get_midjourney_config() returns flat dict with keys expected by integrations.midjourney
# Optional: config.json in project root can override (e.g. after running midjourney-agent setup)
MIDJOURNEY_CONFIG: dict[str, Any] = {
    "browser": {"type": "brave", "debug_port": 9222, "profile": "Default"},
    "automation": {"max_retries": 3, "generation_timeout": 300},
    "output": {"folder": None},  # Set at runtime to GENERATED_IMAGES_DIR
    "rate_limiting": {
        "prompts_per_minute": 10,
        "retry_pause_sec": 30,
        "retry_max": 3,
        "queue_poll_interval_sec": 5,
        "queue_drain_max_wait_sec": 600,
        "queue_stuck_threshold_sec": 0,  # Set 0 to disable; sec queue unchanged before assuming stuck
        "queue_stuck_min_elapsed_sec": 180,  # Min total wait before stuck can trigger (avoids slow-processing false positive)
        "queue_error_retry_pause_sec": 90,
        "finalization_wait_sec": 100,
        "processing_slots": 3,
        "min_extrapolation_queue": 4,
        "finalization_wait_min_sec": 30,
        "finalization_wait_max_sec": 180,
    },
    "waits": {
        "after_navigate_sec": 2,
        "between_prompts_sec": 0.5,
        "scroll_before_batch_sec": 1,
        "navigate_retry_delay_sec": 2,
        "finalization_poll_sec": 1,
        "ui_refresh_sec": 5,
        "wait_for_images_timeout_sec": 120,
        "wait_for_upscale_timeout_sec": 60,
        "wait_before_upscale_sec": 90,
        "wait_after_upscale_sec": 90,
        "detail_view_ready_sec": 2,
        "after_upscale_click_sec": 1,
        "after_arrow_right_sec": 1,
        "resume_arrow_right_wait_sec": 2.5,
        "wait_for_upscaled_sec": 15,
        "images_fallback_first_sec": 65,
        "images_fallback_poll_sec": 5,
        "page_load_timeout_ms": 30000,
        "download_timeout_ms": 15000,
        "click_overlay_sec": 1.5,
        "input_fill_delay_sec": 0.2,
        "input_submit_delay_sec": 0.3,
        "seconds_per_prompt_estimate": 60,
        "seconds_per_upscale_estimate": 30,
        "grid_order": "newest_first",
    },
    "checkpoint": {"enabled": False},
    "viewport": "auto",
    "coordinates_viewport": {"width": 1920, "height": 1080},
    "button_coordinates": {
        "download": [1688, 130],
        "vary_subtle": [1620, 720],
        "vary_strong": [1745, 720],
        "upscale_subtle": [1620, 770],
        "upscale_creative": [1745, 770],
    },
}


def _get_screen_resolution() -> dict[str, int]:
    """Detect primary screen resolution. Returns 1920x1080 on non-Windows or on failure."""
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            if w > 0 and h > 0:
                return {"width": w, "height": h}
        except Exception:
            pass
    return {"width": 1920, "height": 1080}


def _load_midjourney_overrides_from_json(config_path: Path) -> dict[str, Any]:
    """Extract overrides from config.json using same logic as midjourney load_config_from_json."""
    if not config_path.exists():
        return {}
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        return {}
    overrides: dict[str, Any] = {}
    output = data.get("output", {})
    browser = data.get("browser", {})
    automation = data.get("automation", {})
    rate = data.get("rate_limiting", {})
    if output and "folder" in output:
        overrides["output_folder"] = Path(output["folder"])
    if browser and "debug_port" in browser:
        overrides["browser_debug_port"] = int(browser["debug_port"])
    if automation:
        if "max_retries" in automation:
            overrides["max_retries"] = automation["max_retries"]
        if "generation_timeout" in automation:
            overrides["generation_timeout"] = float(automation["generation_timeout"])
    if rate:
        if "retry_pause_sec" in rate:
            overrides["rate_limit_retry_pause_sec"] = int(rate["retry_pause_sec"])
        if "retry_max" in rate:
            overrides["rate_limit_retry_max"] = int(rate["retry_max"])
        if "queue_poll_interval_sec" in rate:
            overrides["queue_poll_interval_sec"] = int(rate["queue_poll_interval_sec"])
        if "queue_drain_max_wait_sec" in rate:
            overrides["queue_drain_max_wait_sec"] = int(rate["queue_drain_max_wait_sec"])
        if "queue_stuck_threshold_sec" in rate:
            overrides["queue_stuck_threshold_sec"] = int(rate["queue_stuck_threshold_sec"])
        if "queue_stuck_min_elapsed_sec" in rate:
            overrides["queue_stuck_min_elapsed_sec"] = int(rate["queue_stuck_min_elapsed_sec"])
        if "queue_error_retry_pause_sec" in rate:
            overrides["queue_error_retry_pause_sec"] = int(rate["queue_error_retry_pause_sec"])
        if "finalization_wait_sec" in rate:
            overrides["finalization_wait_sec"] = int(rate["finalization_wait_sec"])
        if "processing_slots" in rate:
            overrides["processing_slots"] = int(rate["processing_slots"])
        if "min_extrapolation_queue" in rate:
            overrides["min_extrapolation_queue"] = int(rate["min_extrapolation_queue"])
        if "finalization_wait_min_sec" in rate:
            overrides["finalization_wait_min_sec"] = int(rate["finalization_wait_min_sec"])
        if "finalization_wait_max_sec" in rate:
            overrides["finalization_wait_max_sec"] = int(rate["finalization_wait_max_sec"])
    waits = data.get("waits", {})
    if waits and isinstance(waits, dict):
        overrides["waits"] = {k: v for k, v in waits.items() if v is not None}
    coords = data.get("button_coordinates", {})
    if coords and isinstance(coords, dict):
        overrides["button_coordinates"] = coords
    vp = data.get("viewport")
    if vp == "auto" or vp is None or not (isinstance(vp, dict) and "width" in vp and "height" in vp):
        overrides["viewport"] = _get_screen_resolution()
    elif isinstance(vp, dict) and "width" in vp and "height" in vp:
        overrides["viewport"] = {"width": int(vp["width"]), "height": int(vp["height"])}
    ref = data.get("coordinates_viewport", {})
    if ref and isinstance(ref, dict) and "width" in ref and "height" in ref:
        overrides["coordinates_viewport"] = {"width": int(ref["width"]), "height": int(ref["height"])}
    if data.get("debug_show_clicks") is True:
        overrides["debug_show_clicks"] = True
    return overrides


def get_midjourney_config(config_path: Path | None = None) -> dict[str, Any]:
    """Build Midjourney config from MIDJOURNEY_CONFIG, optionally merge from config.json.

    Returns flat dict with keys: output_folder, browser_debug_port, rate_limit_*,
    queue_*, finalization_wait_sec, waits, button_coordinates, viewport,
    coordinates_viewport, debug_show_clicks.
    """
    cfg = dict(MIDJOURNEY_CONFIG)
    cfg["output"] = dict(cfg.get("output", {}))
    cfg["output"]["folder"] = str(GENERATED_IMAGES_DIR)

    # Build base flat overrides
    base: dict[str, Any] = {
        "output_folder": Path(cfg["output"]["folder"]),
        "browser_debug_port": cfg["browser"].get("debug_port", 9222),
        "rate_limit_retry_pause_sec": cfg["rate_limiting"].get("retry_pause_sec", 90),
        "rate_limit_retry_max": cfg["rate_limiting"].get("retry_max", 3),
        "queue_poll_interval_sec": cfg["rate_limiting"].get("queue_poll_interval_sec", 5),
        "queue_drain_max_wait_sec": cfg["rate_limiting"].get("queue_drain_max_wait_sec", 600),
        "queue_stuck_threshold_sec": cfg["rate_limiting"].get("queue_stuck_threshold_sec", 120),
        "queue_stuck_min_elapsed_sec": cfg["rate_limiting"].get("queue_stuck_min_elapsed_sec", 180),
        "queue_error_retry_pause_sec": cfg["rate_limiting"].get("queue_error_retry_pause_sec", 90),
        "finalization_wait_sec": cfg["rate_limiting"].get("finalization_wait_sec", 30),
        "processing_slots": cfg["rate_limiting"].get("processing_slots", 3),
        "min_extrapolation_queue": cfg["rate_limiting"].get("min_extrapolation_queue", 4),
        "finalization_wait_min_sec": cfg["rate_limiting"].get("finalization_wait_min_sec", 30),
        "finalization_wait_max_sec": cfg["rate_limiting"].get("finalization_wait_max_sec", 180),
        "waits": dict(cfg.get("waits", {})),
        "button_coordinates": dict(cfg.get("button_coordinates", {})),
        "coordinates_viewport": dict(cfg.get("coordinates_viewport", {"width": 1920, "height": 1080})),
        "debug_show_clicks": False,
    }
    vp = cfg.get("viewport")
    if vp == "auto" or vp is None:
        base["viewport"] = _get_screen_resolution()
    elif isinstance(vp, dict):
        base["viewport"] = dict(vp)
    else:
        base["viewport"] = {"width": 1920, "height": 1080}

    # Merge from config.json if present
    if config_path is None:
        config_path = PROJECT_ROOT / "config.json"
    json_overrides = _load_midjourney_overrides_from_json(config_path)
    for k, v in json_overrides.items():
        if k == "waits" and isinstance(v, dict):
            base["waits"].update(v)
        else:
            base[k] = v

    return base
