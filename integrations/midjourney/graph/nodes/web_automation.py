"""Web automation node for Midjourney.com."""

from __future__ import annotations

from pathlib import Path

from integrations.midjourney.automation.midjourney_web_controller import MidjourneyWebController
from integrations.midjourney.automation.browser_config import DEBUG_PORT
from integrations.midjourney.config import get_file_config_overrides
from integrations.midjourney.graph.state import AgentState
from integrations.midjourney.utils.logging_config import logger


def process_prompt_web(state: AgentState) -> AgentState:
    """Full web flow for one prompt: submit, wait for 4 images, upscale all, download all."""
    tasks = state["tasks"]
    current_index = state["current_index"]
    task = tasks[current_index]
    if task.get("status") == "failed":
        return state

    prompt = task["prompt"]
    attempt = task.get("attempt", 1)
    output_folder = Path(state.get("output_folder", "./output"))
    dry_run = state.get("dry_run", False)
    debug_port = state.get("browser_debug_port", DEBUG_PORT)

    logger.info("Node: process_prompt_web — %s", prompt[:60])

    button_coords = state.get("button_coordinates") or {}
    viewport = state.get("viewport") or {"width": 1920, "height": 1080}
    coordinates_viewport = state.get("coordinates_viewport") or {"width": 1920, "height": 1080}
    debug_show_clicks = state.get("debug_show_clicks", False)
    waits = get_file_config_overrides().get("waits", {})
    controller = MidjourneyWebController(
        debug_port=debug_port,
        dry_run=dry_run,
        button_coordinates=button_coords,
        viewport=viewport,
        coordinates_viewport=coordinates_viewport,
        debug_show_clicks=debug_show_clicks,
        waits=waits,
    )

    try:
        if not dry_run:
            controller.connect()
            if not state.get("navigated"):
                controller.navigate_to_imagine()
                state["navigated"] = True

            # Wait for queue to drain at batch boundaries (every 10 prompts)
            if current_index > 0 and current_index % 10 == 0 and len(tasks) > 10:
                cfg = get_file_config_overrides()
                queue_poll = cfg.get("queue_poll_interval_sec", 5)
                queue_max_wait = cfg.get("queue_drain_max_wait_sec", 600)
                stop_check = lambda: state.get("stop_requested", False)
                logger.info("Batch boundary: waiting for queue to drain before prompt %d", current_index + 1)
                controller.wait_until_queue_empty(
                    progress_callback=lambda _: None,
                    stop_check=stop_check,
                    poll_interval_sec=queue_poll,
                    max_wait_sec=queue_max_wait,
                )

        paths = controller.process_prompt(prompt, output_folder, attempt)

        if not dry_run:
            controller.close()

        task["images"] = [{"path": str(p), "upscale_index": i + 1} for i, p in enumerate(paths)]
        task["image_path"] = str(paths[0]) if paths else ""
        task["status"] = "accepted" if paths else "failed"
        if not paths and not dry_run:
            task["error"] = "No images downloaded"

        logger.info("Processed prompt: %d images saved", len(paths))
        return {**state, "tasks": state["tasks"]}
    except Exception as e:
        logger.error("process_prompt_web failed: %s", e)
        task["status"] = "failed"
        task["error"] = str(e)
        if not dry_run:
            try:
                controller.close()
            except Exception:
                pass
        return {**state, "tasks": state["tasks"]}
