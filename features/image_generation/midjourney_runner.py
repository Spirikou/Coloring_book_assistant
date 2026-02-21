"""Thread runners for Midjourney Publish, Upscale/Vary, and Download.

Extracted from midjourney_agent app.py. Uses integrations.midjourney.

Process-based entry points (run_*_process) spawn a separate process to avoid Playwright
Sync API conflicts with Streamlit's asyncio loop.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from typing import Callable

from integrations.midjourney.config import get_file_config_overrides
from integrations.midjourney.utils.logging_config import logger

RATE_LIMIT_ERROR_PATTERNS = ("queue", "limit", "too many", "rate", "wait")


def _compute_finalization_wait_sec(
    cfg: dict,
    initial_queue: int | None,
    elapsed_sec: float,
    queue_drained: bool = True,
) -> float:
    """Compute finalization wait: extrapolate from queue drain or use fallback.
    Only extrapolates when queue_drained is True (queue actually reached 0).
    """
    processing_slots = cfg.get("processing_slots", 3)
    min_extrapolation_queue = cfg.get("min_extrapolation_queue", 4)
    fallback_sec = cfg.get("finalization_wait_sec", 100)
    min_wait = cfg.get("finalization_wait_min_sec", 30)
    max_wait = cfg.get("finalization_wait_max_sec", 180)

    if (
        queue_drained
        and initial_queue is not None
        and initial_queue >= min_extrapolation_queue
        and elapsed_sec > 0
    ):
        sec_per_item = elapsed_sec / initial_queue
        extrapolated = processing_slots * sec_per_item
        finalization_sec = max(min_wait, min(max_wait, extrapolated))
        logger.info(
            "[Queue TRACE] Extrapolated finalization: %d items in %.1fs -> %.1fs/item, wait %.1fs for %d slots",
            initial_queue,
            elapsed_sec,
            sec_per_item,
            finalization_sec,
            processing_slots,
        )
        return finalization_sec
    else:
        logger.info(
            "[Queue TRACE] Using fallback finalization: %.1fs (queue_drained=%s, queue=%s, elapsed=%.1fs)",
            fallback_sec,
            queue_drained,
            initial_queue,
            elapsed_sec or 0,
        )
        return fallback_sec


def run_publish_thread(
    prompts: list[str],
    button_coordinates: dict,
    browser_port: int,
    stop_flag: dict,
    progress_store: dict,
    status_store: dict,
    viewport: dict | None = None,
    coordinates_viewport: dict | None = None,
    debug_show_clicks: bool = False,
) -> None:
    """Submit prompts only. No upscale, vary, or download."""
    from integrations.midjourney.automation.midjourney_web_controller import (
        MidjourneyWebController,
    )

    status_store["publish_status"] = "running"
    status_store["publish_error"] = ""
    vp = viewport or {"width": 1920, "height": 1080}
    coord_vp = coordinates_viewport or {"width": 1920, "height": 1080}
    stop_check: Callable[[], bool] = lambda: stop_flag.get("stop", False)
    cfg = get_file_config_overrides()
    retry_pause = cfg.get("rate_limit_retry_pause_sec", 90)
    retry_max = cfg.get("rate_limit_retry_max", 3)
    queue_poll = cfg.get("queue_poll_interval_sec", 5)
    queue_max_wait = cfg.get("queue_drain_max_wait_sec", 600)
    queue_stuck_threshold = cfg.get("queue_stuck_threshold_sec", 120)
    queue_stuck_min_elapsed = cfg.get("queue_stuck_min_elapsed_sec", 180)
    queue_error_pause = cfg.get("queue_error_retry_pause_sec", retry_pause)

    for attempt in range(retry_max + 1):
        try:
            waits = cfg.get("waits", {})
            controller = MidjourneyWebController(
                debug_port=browser_port,
                dry_run=False,
                button_coordinates=button_coordinates,
                viewport=vp,
                coordinates_viewport=coord_vp,
                debug_show_clicks=debug_show_clicks,
                waits=waits,
            )
            controller.connect()
            controller.navigate_to_imagine()
            time.sleep(waits.get("after_navigate_sec", 2))

            total_prompts = len(prompts)
            total_images = total_prompts * 4
            num_batches = (total_prompts + 9) // 10
            progress_store["total_prompts"] = total_prompts
            progress_store["total_images"] = total_images
            progress_store["total_batches"] = num_batches
            progress_store["batch_total"] = num_batches
            sec_per_prompt = cfg.get("waits", {}).get("seconds_per_prompt_estimate", 40)
            total_wait_all = sum(
                min(10, total_prompts - b * 10) * sec_per_prompt
                for b in range(num_batches)
            )
            progress_store["total_wait_all"] = total_wait_all

            initial_queue: int | None = None
            elapsed_sec = 0.0
            queue_drained = False
            for batch_start in range(0, len(prompts), 10):
                if stop_check():
                    status_store["publish_status"] = "stopped"
                    controller.close()
                    return
                batch = prompts[batch_start : batch_start + 10]
                batch_idx = batch_start // 10
                progress_store["batch_current"] = batch_idx + 1
                progress_store["completed_batches"] = batch_idx

                if batch_start > 0 and controller.page:
                    controller.page.evaluate("window.scrollTo(0, 0)")
                    time.sleep(cfg.get("waits", {}).get("scroll_before_batch_sec", 1))
                progress_store["phase"] = "submit"
                progress_store["images_estimated"] = total_images

                for i, p in enumerate(batch):
                    if stop_check():
                        break
                    progress_store["submit_current"] = batch_start + i + 1
                    progress_store["submit_total"] = total_prompts
                    controller.submit_prompt(p)
                    time.sleep(cfg.get("waits", {}).get("between_prompts_sec", 0.5))

                if controller.has_queue_error():
                    logger.warning(
                        "Too many queued jobs, waiting %ds then draining queue (no resubmit)",
                        queue_error_pause,
                    )
                    time.sleep(queue_error_pause)

                def wait_progress_cb(count):
                    progress_store["phase"] = "wait"
                    progress_store["queue_count"] = count
                    if count is not None and count > 0:
                        progress_store["estimated_wait_min"] = count * cfg.get("waits", {}).get("seconds_per_prompt_estimate", 40) / 60

                progress_store["phase"] = "wait"
                progress_store["queue_count"] = None
                progress_store["images_estimated"] = total_images
                progress_store["batch_current"] = batch_idx + 1
                progress_store["batch_total"] = num_batches
                ready, initial_queue, elapsed_sec, queue_drained = controller.wait_until_queue_empty(
                    progress_callback=wait_progress_cb,
                    stop_check=stop_check,
                    poll_interval_sec=queue_poll,
                    max_wait_sec=queue_max_wait,
                    stuck_threshold_sec=queue_stuck_threshold,
                    stuck_min_elapsed_sec=queue_stuck_min_elapsed,
                )
                if not ready:
                    status_store["publish_status"] = "stopped"
                    controller.close()
                    return

                if batch_start + 10 < len(prompts) and not stop_check():
                    inter_batch_sec = _compute_finalization_wait_sec(
                        cfg, initial_queue, elapsed_sec, queue_drained
                    )
                    progress_store["phase"] = "finalize"
                    progress_store["elapsed"] = 0
                    progress_store["total"] = inter_batch_sec
                    progress_store["total_wait_all"] = progress_store.get("total_wait_all", 0) + inter_batch_sec
                    progress_store["estimated_wait_min"] = progress_store["total_wait_all"] / 60
                    start_f = time.time()
                    poll_sec = cfg.get("waits", {}).get("finalization_poll_sec", 1)
                    while (time.time() - start_f) < inter_batch_sec and not stop_check():
                        progress_store["elapsed"] = time.time() - start_f
                        progress_store["queue_count"] = controller.get_queue_count()
                        time.sleep(poll_sec)

            finalization_sec = _compute_finalization_wait_sec(
                cfg, initial_queue, elapsed_sec, queue_drained
            )
            if finalization_sec > 0 and not stop_check():
                progress_store["phase"] = "finalize"
                progress_store["elapsed"] = 0
                progress_store["total"] = finalization_sec
                progress_store["total_wait_all"] = progress_store.get("total_wait_all", 0) + finalization_sec
                progress_store["estimated_wait_min"] = progress_store["total_wait_all"] / 60
                start_f = time.time()
                poll_sec = cfg.get("waits", {}).get("finalization_poll_sec", 1)
                while (time.time() - start_f) < finalization_sec and not stop_check():
                    progress_store["elapsed"] = time.time() - start_f
                    progress_store["queue_count"] = controller.get_queue_count()
                    time.sleep(poll_sec)

            status_store["publish_status"] = "stopped" if stop_check() else "completed"
            controller.close()
            return
        except Exception as e:
            err_str = str(e).lower()
            if attempt < retry_max and any(p in err_str for p in RATE_LIMIT_ERROR_PATTERNS):
                logger.warning(
                    "Rate limit / queue error (%s), pausing %ds before retry %d/%d",
                    e, retry_pause, attempt + 1, retry_max,
                )
                time.sleep(retry_pause)
            else:
                status_store["publish_status"] = "error"
                try:
                    status_store["publish_error"] = str(e)
                except Exception:
                    pass
                raise


def run_uxd_action_thread(
    button_keys: list[str],
    count: int,
    output_folder: Path,
    button_coordinates: dict,
    browser_port: int,
    stop_flag: dict,
    total_new_images: int,
    progress_store: dict,
    status_store: dict,
    viewport: dict | None = None,
    coordinates_viewport: dict | None = None,
    debug_show_clicks: bool = False,
) -> None:
    """Run Upscale/Vary for first N images."""
    from integrations.midjourney.automation.midjourney_web_controller import (
        MidjourneyWebController,
    )

    status_store["uxd_action_status"] = "running"
    status_store["uxd_action_error"] = ""
    vp = viewport or {"width": 1920, "height": 1080}
    coord_vp = coordinates_viewport or {"width": 1920, "height": 1080}
    stop_check = lambda: stop_flag.get("stop", False)
    cfg = get_file_config_overrides()
    retry_pause = cfg.get("rate_limit_retry_pause_sec", 90)
    retry_max = cfg.get("rate_limit_retry_max", 3)
    queue_poll = cfg.get("queue_poll_interval_sec", 5)
    queue_max_wait = cfg.get("queue_drain_max_wait_sec", 600)
    queue_stuck_threshold = cfg.get("queue_stuck_threshold_sec", 120)
    queue_stuck_min_elapsed = cfg.get("queue_stuck_min_elapsed_sec", 180)

    for attempt in range(retry_max + 1):
        try:
            waits = cfg.get("waits", {})
            controller = MidjourneyWebController(
                debug_port=browser_port,
                dry_run=False,
                button_coordinates=button_coordinates,
                viewport=vp,
                coordinates_viewport=coord_vp,
                debug_show_clicks=debug_show_clicks,
                waits=waits,
            )
            controller.connect()
            controller.navigate_to_imagine()
            time.sleep(waits.get("after_navigate_sec", 2))

            num_batches = (count + 9) // 10
            progress_store["uxd_total_actions"] = count
            progress_store["uxd_total_batches"] = num_batches
            total_wait_all = total_new_images * 20
            progress_store["uxd_total_wait_all"] = total_wait_all

            last_processed_url: str | None = None
            initial_queue: int | None = None
            elapsed_sec = 0.0
            queue_drained = False
            for batch_start in range(0, count, 10):
                if stop_check():
                    status_store["uxd_action_status"] = "stopped"
                    controller.close()
                    return

                if batch_start > 0 and controller.page:
                    controller.page.evaluate("window.scrollTo(0, 0)")
                    time.sleep(cfg.get("waits", {}).get("scroll_before_batch_sec", 1))

                batch_size = min(10, count - batch_start)
                batch_num = batch_start // 10 + 1
                progress_store["uxd_batch_current"] = batch_num
                progress_store["phase"] = "click"
                progress_store["uxd_total_images"] = count

                def uxd_progress_cb(current: int, total: int) -> None:
                    progress_store["uxd_current_image"] = current
                    progress_store["uxd_total_images"] = total

                logger.info(
                    "[Upscale TRACE] Batch %d/%d: start_index=%d, batch_size=%d, resuming=%s, last_url=%s",
                    batch_num,
                    num_batches,
                    batch_start,
                    batch_size,
                    last_processed_url is not None,
                    (last_processed_url[:80] + "..." if last_processed_url and len(last_processed_url) > 80 else last_processed_url) or "None",
                )
                _, last_processed_url = controller.click_button_first_n(
                    button_keys, batch_size, output_folder, stem="ui_batch",
                    stop_check=stop_check,
                    start_index=batch_start,
                    last_processed_url=last_processed_url,
                    total_count=count,
                    progress_callback=uxd_progress_cb,
                )
                if last_processed_url:
                    logger.info(
                        "[Upscale TRACE] Batch %d done: last_processed_url=%s",
                        batch_num,
                        last_processed_url[:100] + ("..." if len(last_processed_url) > 100 else ""),
                    )
                if stop_check():
                    status_store["uxd_action_status"] = "stopped"
                    controller.close()
                    return

                def uxd_wait_progress_cb(c):
                    progress_store["phase"] = "wait"
                    progress_store["queue_count"] = c
                    if c is not None and c > 0:
                        progress_store["estimated_wait_min"] = c * cfg.get("waits", {}).get("seconds_per_upscale_estimate", 20) / 60

                progress_store["phase"] = "wait"
                progress_store["queue_count"] = None
                progress_store["images_estimated"] = total_new_images
                progress_store["uxd_batch_current"] = batch_start // 10 + 1
                progress_store["uxd_total_batches"] = num_batches
                ready, initial_queue, elapsed_sec, queue_drained = controller.wait_until_queue_empty(
                    progress_callback=uxd_wait_progress_cb,
                    stop_check=stop_check,
                    poll_interval_sec=queue_poll,
                    max_wait_sec=queue_max_wait,
                    stuck_threshold_sec=queue_stuck_threshold,
                    stuck_min_elapsed_sec=queue_stuck_min_elapsed,
                )
                if not ready:
                    status_store["uxd_action_status"] = "stopped"
                    controller.close()
                    return

                if batch_start + 10 < count and not stop_check():
                    inter_batch_sec = _compute_finalization_wait_sec(
                        cfg, initial_queue, elapsed_sec, queue_drained
                    )
                    progress_store["phase"] = "finalize"
                    progress_store["elapsed"] = 0
                    progress_store["total"] = inter_batch_sec
                    uxd_total = progress_store.get("uxd_total_wait_all", 0) + inter_batch_sec
                    progress_store["uxd_total_wait_all"] = uxd_total
                    progress_store["estimated_wait_min"] = uxd_total / 60
                    start_f = time.time()
                    poll_sec = cfg.get("waits", {}).get("finalization_poll_sec", 1)
                    while (time.time() - start_f) < inter_batch_sec and not stop_check():
                        progress_store["elapsed"] = time.time() - start_f
                        progress_store["queue_count"] = controller.get_queue_count()
                        time.sleep(poll_sec)

            finalization_sec = _compute_finalization_wait_sec(
                cfg, initial_queue, elapsed_sec, queue_drained
            )
            if finalization_sec > 0 and not stop_check():
                progress_store["phase"] = "finalize"
                progress_store["elapsed"] = 0
                progress_store["total"] = finalization_sec
                uxd_total = progress_store.get("uxd_total_wait_all", 0) + finalization_sec
                progress_store["uxd_total_wait_all"] = uxd_total
                progress_store["estimated_wait_min"] = uxd_total / 60
                start_f = time.time()
                poll_sec = cfg.get("waits", {}).get("finalization_poll_sec", 1)
                while (time.time() - start_f) < finalization_sec and not stop_check():
                    progress_store["elapsed"] = time.time() - start_f
                    progress_store["queue_count"] = controller.get_queue_count()
                    time.sleep(poll_sec)

            status_store["uxd_action_status"] = "stopped" if stop_check() else "completed"
            controller.close()
            return
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = any(p in err_str for p in RATE_LIMIT_ERROR_PATTERNS)
            if attempt < retry_max:
                pause = retry_pause if is_rate_limit else min(30, retry_pause // 3)
                logger.warning(
                    "Upscale/vary error (%s)%s, pausing %ds before retry %d/%d",
                    e,
                    " [rate limit]" if is_rate_limit else "",
                    pause, attempt + 1, retry_max,
                )
                time.sleep(pause)
            else:
                status_store["uxd_action_status"] = "error"
                try:
                    status_store["uxd_action_error"] = str(e)
                except Exception:
                    pass
                raise


def run_download_thread(
    count: int,
    output_folder: Path,
    button_coordinates: dict,
    browser_port: int,
    stop_flag: dict,
    progress_store: dict,
    status_store: dict,
    viewport: dict | None = None,
    coordinates_viewport: dict | None = None,
    debug_show_clicks: bool = False,
) -> None:
    """Run Download for first N images."""
    from integrations.midjourney.automation.midjourney_web_controller import (
        MidjourneyWebController,
    )

    status_store["download_status"] = "running"
    status_store["download_error"] = ""
    progress_store["current"] = 0
    progress_store["total"] = count
    vp = viewport or {"width": 1920, "height": 1080}
    coord_vp = coordinates_viewport or {"width": 1920, "height": 1080}
    stop_check = lambda: stop_flag.get("stop", False)
    cfg = get_file_config_overrides()
    retry_pause = cfg.get("rate_limit_retry_pause_sec", 90)
    retry_max = cfg.get("rate_limit_retry_max", 3)

    def on_progress(current: int, total: int) -> None:
        progress_store["current"] = current
        progress_store["total"] = total

    for attempt in range(retry_max + 1):
        try:
            waits = cfg.get("waits", {})
            controller = MidjourneyWebController(
                debug_port=browser_port,
                dry_run=False,
                button_coordinates=button_coordinates,
                viewport=vp,
                coordinates_viewport=coord_vp,
                debug_show_clicks=debug_show_clicks,
                waits=waits,
            )
            controller.connect()
            controller.navigate_to_imagine()
            time.sleep(waits.get("after_navigate_sec", 2))

            result, _ = controller.click_button_first_n(
                ["download"], count, output_folder, stem="ui_batch",
                stop_check=stop_check,
                progress_callback=on_progress,
            )
            status_store["download_status"] = "stopped" if stop_check() else "completed"
            status_store["downloaded_paths"] = list(result) if result else []
            controller.close()
            return
        except Exception as e:
            err_str = str(e).lower()
            if attempt < retry_max and any(p in err_str for p in RATE_LIMIT_ERROR_PATTERNS):
                logger.warning(
                    "Rate limit / queue error in download (%s), pausing %ds before retry %d/%d",
                    e, retry_pause, attempt + 1, retry_max,
                )
                time.sleep(retry_pause)
            else:
                status_store["download_status"] = "error"
                status_store["downloaded_paths"] = []
                try:
                    status_store["download_error"] = str(e)
                except Exception:
                    pass
                raise


def run_automated_thread(
    prompts: list[str],
    button_coordinates: dict,
    browser_port: int,
    output_folder: Path,
    stop_flag: dict,
    shared: dict,
    publish_progress: dict,
    uxd_progress: dict,
    download_progress: dict,
    viewport: dict | None = None,
    coordinates_viewport: dict | None = None,
    debug_show_clicks: bool = False,
) -> None:
    """Run full pipeline: Publish all → Upscale all → Download all."""
    try:
        stop_check = lambda: stop_flag.get("stop", False)
        num_prompts = len(prompts)
        num_images = num_prompts * 4

        shared["publish_status"] = "running"
        shared["publish_error"] = ""
        run_publish_thread(
            prompts,
            button_coordinates,
            browser_port,
            stop_flag,
            publish_progress,
            shared,
            viewport=viewport,
            coordinates_viewport=coordinates_viewport,
            debug_show_clicks=debug_show_clicks,
        )
        if stop_check():
            return
        shared["publish_status"] = "completed"

        button_keys = ["upscale_subtle"] if "upscale_subtle" in button_coordinates else (
            [k for k in ["upscale_creative", "upscale_subtle"] if k in button_coordinates]
        )
        if not button_keys:
            shared["uxd_action_status"] = "error"
            shared["uxd_action_error"] = "No upscale button coordinates configured"
            return
        shared["uxd_action_status"] = "running"
        shared["uxd_action_error"] = ""
        uxd_progress.clear()
        uxd_progress.update({"elapsed": 0, "total": 0, "phase": "click", "images_estimated": num_images})
        run_uxd_action_thread(
            button_keys,
            num_images,
            output_folder,
            button_coordinates,
            browser_port,
            stop_flag,
            num_images,
            uxd_progress,
            shared,
            viewport=viewport,
            coordinates_viewport=coordinates_viewport,
            debug_show_clicks=debug_show_clicks,
        )
        if stop_check():
            return
        shared["uxd_action_status"] = "completed"

        shared["download_status"] = "running"
        shared["download_error"] = ""
        download_progress.clear()
        download_progress.update({"current": 0, "total": num_images})
        run_download_thread(
            num_images,
            output_folder,
            button_coordinates,
            browser_port,
            stop_flag,
            download_progress,
            shared,
            viewport=viewport,
            coordinates_viewport=coordinates_viewport,
            debug_show_clicks=debug_show_clicks,
        )
    except Exception as e:
        logger.exception("Automated workflow failed: %s", e)
        shared["publish_status"] = "error"
        try:
            shared["publish_error"] = str(e)
        except Exception:
            pass


def run_batch_automated_thread(
    designs_with_folders: list[tuple[dict, Path, int]],
    button_coordinates: dict,
    browser_port: int,
    stop_flag: dict,
    shared: dict,
    publish_progress: dict,
    uxd_progress: dict,
    download_progress: dict,
    viewport: dict | None = None,
    coordinates_viewport: dict | None = None,
    debug_show_clicks: bool = False,
) -> None:
    """Run full automated pipeline for multiple designs sequentially. Each design uses its own subfolder.

    Args:
        designs_with_folders: List of (design_dict, output_folder_path, original_index).
            design_dict must have "midjourney_prompts" key.
        shared: Status dict; will be updated with batch_current_index, batch_total,
            batch_current_design_title, and batch_results (list of {design_index, folder_path}).
            For multiprocessing, shared["batch_results"] must be a manager.list().
    """
    if "batch_results" not in shared:
        shared["batch_results"] = []
    batch_results = shared["batch_results"]
    shared["batch_current_index"] = 0
    shared["batch_total"] = len(designs_with_folders)
    shared["batch_current_design_title"] = ""

    stop_check = lambda: stop_flag.get("stop", False)

    for i, (design, output_folder, original_index) in enumerate(designs_with_folders):
        if stop_check():
            break

        prompts = design.get("midjourney_prompts", [])
        if not prompts:
            continue

        title = design.get("title", "Untitled") or "Untitled"
        shared["batch_current_index"] = i + 1
        shared["batch_total"] = len(designs_with_folders)
        shared["batch_current_design_title"] = title

        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        try:
            run_automated_thread(
                prompts=prompts,
                button_coordinates=button_coordinates,
                browser_port=browser_port,
                output_folder=output_folder,
                stop_flag=stop_flag,
                shared=shared,
                publish_progress=publish_progress,
                uxd_progress=uxd_progress,
                download_progress=download_progress,
                viewport=viewport,
                coordinates_viewport=coordinates_viewport,
                debug_show_clicks=debug_show_clicks,
            )
        except Exception as e:
            logger.exception("Batch design %d failed: %s", i + 1, e)
            shared["publish_status"] = "error"
            shared["publish_error"] = str(e)
            return

        if stop_check():
            break

        batch_results.append({"design_index": original_index, "folder_path": str(output_folder)})

    shared["batch_current_design_title"] = ""
    if shared.get("publish_status") == "running":
        shared["publish_status"] = "completed"
    if shared.get("uxd_action_status") == "running":
        shared["uxd_action_status"] = "completed"
    if shared.get("download_status") == "running":
        shared["download_status"] = "completed"


def _copy_dict(dest: dict, src: dict) -> None:
    """Copy src into dest. For Manager dicts, use update to avoid pickling issues."""
    dest.clear()
    dest.update(dict(src))


def run_publish_process(
    prompts: list[str],
    button_coordinates: dict,
    browser_port: int,
    stop_flag: dict,
    progress_store: dict,
    status_store: dict,
    viewport: dict | None = None,
    coordinates_viewport: dict | None = None,
    debug_show_clicks: bool = False,
) -> tuple[multiprocessing.Process, multiprocessing.managers.SyncManager, dict, dict, dict]:
    """Run publish in a separate process. Returns (process, manager, stop_flag, progress_store, status_store)."""
    manager = multiprocessing.Manager()
    mgr_stop = manager.dict()
    mgr_stop["stop"] = stop_flag.get("stop", False)
    mgr_progress = manager.dict()
    _copy_dict(mgr_progress, progress_store)
    mgr_status = manager.dict()
    _copy_dict(mgr_status, status_store)

    proc = multiprocessing.Process(
        target=run_publish_thread,
        args=(
            prompts,
            button_coordinates,
            browser_port,
            mgr_stop,
            mgr_progress,
            mgr_status,
        ),
        kwargs={
            "viewport": viewport,
            "coordinates_viewport": coordinates_viewport,
            "debug_show_clicks": debug_show_clicks,
        },
        daemon=True,
    )
    proc.start()
    return proc, manager, mgr_stop, mgr_progress, mgr_status


def run_uxd_action_process(
    button_keys: list[str],
    count: int,
    output_folder: Path,
    button_coordinates: dict,
    browser_port: int,
    stop_flag: dict,
    total_new_images: int,
    progress_store: dict,
    status_store: dict,
    viewport: dict | None = None,
    coordinates_viewport: dict | None = None,
    debug_show_clicks: bool = False,
) -> tuple[multiprocessing.Process, multiprocessing.managers.SyncManager, dict, dict, dict]:
    """Run upscale/vary in a separate process. Returns (process, manager, stop_flag, progress_store, status_store)."""
    manager = multiprocessing.Manager()
    mgr_stop = manager.dict()
    mgr_stop["stop"] = stop_flag.get("stop", False)
    mgr_progress = manager.dict()
    _copy_dict(mgr_progress, progress_store)
    mgr_status = manager.dict()
    _copy_dict(mgr_status, status_store)

    proc = multiprocessing.Process(
        target=run_uxd_action_thread,
        args=(
            button_keys,
            count,
            output_folder,
            button_coordinates,
            browser_port,
            mgr_stop,
            total_new_images,
            mgr_progress,
            mgr_status,
        ),
        kwargs={
            "viewport": viewport,
            "coordinates_viewport": coordinates_viewport,
            "debug_show_clicks": debug_show_clicks,
        },
        daemon=True,
    )
    proc.start()
    return proc, manager, mgr_stop, mgr_progress, mgr_status


def run_download_process(
    count: int,
    output_folder: Path,
    button_coordinates: dict,
    browser_port: int,
    stop_flag: dict,
    progress_store: dict,
    status_store: dict,
    viewport: dict | None = None,
    coordinates_viewport: dict | None = None,
    debug_show_clicks: bool = False,
) -> tuple[multiprocessing.Process, multiprocessing.managers.SyncManager, dict, dict, dict]:
    """Run download in a separate process. Returns (process, manager, stop_flag, progress_store, status_store)."""
    manager = multiprocessing.Manager()
    mgr_stop = manager.dict()
    mgr_stop["stop"] = stop_flag.get("stop", False)
    mgr_progress = manager.dict()
    _copy_dict(mgr_progress, progress_store)
    mgr_status = manager.dict()
    _copy_dict(mgr_status, status_store)

    proc = multiprocessing.Process(
        target=run_download_thread,
        args=(
            count,
            output_folder,
            button_coordinates,
            browser_port,
            mgr_stop,
            mgr_progress,
            mgr_status,
        ),
        kwargs={
            "viewport": viewport,
            "coordinates_viewport": coordinates_viewport,
            "debug_show_clicks": debug_show_clicks,
        },
        daemon=True,
    )
    proc.start()
    return proc, manager, mgr_stop, mgr_progress, mgr_status


def run_automated_process(
    prompts: list[str],
    button_coordinates: dict,
    browser_port: int,
    output_folder: Path,
    stop_flag: dict,
    shared: dict,
    publish_progress: dict,
    uxd_progress: dict,
    download_progress: dict,
    viewport: dict | None = None,
    coordinates_viewport: dict | None = None,
    debug_show_clicks: bool = False,
) -> tuple[multiprocessing.Process, multiprocessing.managers.SyncManager, dict, dict, dict, dict, dict]:
    """Run full automated pipeline in a separate process. Returns (process, manager, stop_flag, shared, publish_progress, uxd_progress, download_progress)."""
    manager = multiprocessing.Manager()
    mgr_stop = manager.dict()
    mgr_stop["stop"] = stop_flag.get("stop", False)
    mgr_shared = manager.dict()
    _copy_dict(mgr_shared, shared)
    mgr_shared["batch_results"] = manager.list()
    mgr_publish = manager.dict()
    _copy_dict(mgr_publish, publish_progress)
    mgr_uxd = manager.dict()
    _copy_dict(mgr_uxd, uxd_progress)
    mgr_download = manager.dict()
    _copy_dict(mgr_download, download_progress)

    proc = multiprocessing.Process(
        target=run_automated_thread,
        args=(
            prompts,
            button_coordinates,
            browser_port,
            output_folder,
            mgr_stop,
            mgr_shared,
            mgr_publish,
            mgr_uxd,
            mgr_download,
        ),
        kwargs={
            "viewport": viewport,
            "coordinates_viewport": coordinates_viewport,
            "debug_show_clicks": debug_show_clicks,
        },
        daemon=True,
    )
    proc.start()
    return proc, manager, mgr_stop, mgr_shared, mgr_publish, mgr_uxd, mgr_download


def run_batch_automated_process(
    designs_with_folders: list[tuple[dict, Path, int]],
    button_coordinates: dict,
    browser_port: int,
    stop_flag: dict,
    shared: dict,
    publish_progress: dict,
    uxd_progress: dict,
    download_progress: dict,
    viewport: dict | None = None,
    coordinates_viewport: dict | None = None,
    debug_show_clicks: bool = False,
) -> tuple[multiprocessing.Process, multiprocessing.managers.SyncManager, dict, dict, dict, dict, dict]:
    """Run batch automated pipeline in a separate process. Returns (process, manager, stop_flag, shared, publish_progress, uxd_progress, download_progress)."""
    manager = multiprocessing.Manager()
    mgr_stop = manager.dict()
    mgr_stop["stop"] = stop_flag.get("stop", False)
    mgr_shared = manager.dict()
    _copy_dict(mgr_shared, shared)
    mgr_shared["batch_results"] = manager.list()
    mgr_publish = manager.dict()
    _copy_dict(mgr_publish, publish_progress)
    mgr_uxd = manager.dict()
    _copy_dict(mgr_uxd, uxd_progress)
    mgr_download = manager.dict()
    _copy_dict(mgr_download, download_progress)

    proc = multiprocessing.Process(
        target=run_batch_automated_thread,
        args=(
            designs_with_folders,
            button_coordinates,
            browser_port,
            mgr_stop,
            mgr_shared,
            mgr_publish,
            mgr_uxd,
            mgr_download,
        ),
        kwargs={
            "viewport": viewport,
            "coordinates_viewport": coordinates_viewport,
            "debug_show_clicks": debug_show_clicks,
        },
        daemon=True,
    )
    proc.start()
    return proc, manager, mgr_stop, mgr_shared, mgr_publish, mgr_uxd, mgr_download
