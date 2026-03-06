"""Pipeline orchestrator - runs workflow steps sequentially in a subprocess."""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from typing import Any

from config import get_midjourney_config
from core.pipeline_templates import PIPELINE_STEPS, get_step_by_id


def _copy_mj_progress(mj_shared: dict, out: dict) -> None:
    """Copy MJ progress keys to output dict for UI display."""
    keys = [
        "publish_status", "publish_error",
        "uxd_action_status", "uxd_action_error",
        "download_status", "download_error",
        "batch_current_index", "batch_total", "batch_current_design_title",
    ]
    for k in keys:
        if k in mj_shared:
            try:
                v = mj_shared[k]
                out[k] = v
            except (TypeError, ValueError):
                pass


def _run_pipeline_process(
    steps: list[str],
    config: dict[str, Any],
    shared: dict,
) -> None:
    """
    Run pipeline steps sequentially. Updates shared dict with progress.
    Designed to run in a multiprocessing.Process (no Streamlit in this process).
    """
    shared["running"] = True
    shared["status"] = "running"
    shared["current_step_index"] = -1
    shared["current_step_id"] = ""
    shared["error"] = ""
    shared["design_package_path"] = config.get("design_package_path", "")

    design_package_path = config.get("design_package_path", "")
    user_request = config.get("user_request", "").strip()
    workflow_state = config.get("workflow_state")
    board_name = config.get("board_name", "")
    canva_config = config.get("canva_config", {}) or {}

    step_labels = {s["id"]: s["label"] for s in PIPELINE_STEPS}

    for i, step_id in enumerate(steps):
        shared["current_step_index"] = i
        shared["current_step_id"] = step_id
        shared["step_status"] = "running"
        shared["step_progress"] = {"phase": "start", "message": step_labels.get(step_id, step_id)}

        try:
            if step_id == "design":
                from features.design_generation.workflow import run_coloring_book_agent
                from core.persistence import create_design_package

                state = run_coloring_book_agent(user_request)
                path = create_design_package(state)
                state["design_package_path"] = path
                state["images_folder_path"] = path
                workflow_state = state
                design_package_path = path
                shared["design_package_path"] = path
                shared["workflow_state"] = _prepare_state_for_serialization(state)

            elif step_id == "image":
                if not workflow_state:
                    from core.persistence import load_design_package
                    loaded = load_design_package(design_package_path)
                    if not loaded:
                        raise ValueError(f"Could not load design package: {design_package_path}")
                    workflow_state = loaded

                prompts = workflow_state.get("midjourney_prompts", [])
                if not prompts:
                    raise ValueError("No Midjourney prompts in design package")

                output_folder = Path(design_package_path)
                output_folder.mkdir(parents=True, exist_ok=True)

                cfg = get_midjourney_config()
                button_coords = cfg.get("button_coordinates", {})
                browser_port = cfg.get("browser_debug_port", 9222)
                viewport = cfg.get("viewport") or {"width": 1920, "height": 1080}
                coord_vp = cfg.get("coordinates_viewport") or {"width": 1920, "height": 1080}

                from integrations.midjourney.automation.browser_utils import check_browser_connection
                browser_status = check_browser_connection()
                if not browser_status.get("connected", False):
                    raise ValueError("Browser not connected. Start browser with --remote-debugging-port=9222")

                from features.image_generation.midjourney_runner import run_automated_process

                manager = multiprocessing.Manager()
                mgr_stop = manager.dict()
                mgr_stop["stop"] = False
                mj_shared = manager.dict()
                mj_shared.update({
                    "publish_status": "idle",
                    "publish_error": "",
                    "uxd_action_status": "idle",
                    "uxd_action_error": "",
                    "download_status": "idle",
                    "download_error": "",
                    "downloaded_paths": [],
                })
                mj_publish = manager.dict()
                mj_uxd = manager.dict()
                mj_download = manager.dict()

                proc, _, _, _, mj_publish, mj_uxd, mj_download = run_automated_process(
                    prompts,
                    button_coords,
                    browser_port,
                    output_folder,
                    mgr_stop,
                    mj_shared,
                    mj_publish,
                    mj_uxd,
                    mj_download,
                    viewport=viewport,
                    coordinates_viewport=coord_vp,
                )

                while proc.is_alive():
                    prog = dict(shared.get("step_progress", {}))
                    _copy_mj_progress(mj_shared, prog)
                    shared["step_progress"] = prog
                    time.sleep(1)

                proc.join()

                if mj_shared.get("publish_status") == "error" or mj_shared.get("download_status") == "error":
                    err = mj_shared.get("publish_error") or mj_shared.get("uxd_action_error") or mj_shared.get("download_error", "Unknown error")
                    raise RuntimeError(err)

            elif step_id == "evaluate":
                from features.image_generation.agents.evaluator import (
                    evaluate_images_in_folder,
                    save_image_evaluations,
                )

                folder = Path(design_package_path)
                if not folder.exists():
                    raise ValueError(f"Design package folder not found: {design_package_path}")

                def on_progress(cur: int, total: int, name: str) -> None:
                    shared["step_progress"] = {"current": cur, "total": total, "filename": name}

                results = evaluate_images_in_folder(folder, on_progress=on_progress)
                save_image_evaluations(folder, results)

            elif step_id == "canva":
                from workflows.canva.designer import CanvaDesignWorkflow
                from integrations.midjourney.automation.browser_utils import check_browser_connection

                browser_status = check_browser_connection()
                if not browser_status.get("connected", False):
                    raise ValueError("Browser not connected. Start browser with --remote-debugging-port=9222")

                folder = design_package_path
                workflow = CanvaDesignWorkflow()

                def progress_cb(progress: dict) -> None:
                    shared["step_progress"] = dict(progress)

                workflow.create_design(
                    images_folder=folder,
                    page_size=canva_config.get("page_size", "A4"),
                    margin_percent=canva_config.get("margin_percent", 5.0),
                    outline_height_percent=canva_config.get("outline_height_percent"),
                    blank_between=canva_config.get("blank_between", False),
                    progress_callback=progress_cb,
                    selected_images=None,
                )

            elif step_id == "pinterest":
                from workflows.pinterest.publisher import PinterestPublishingWorkflow
                from integrations.midjourney.automation.browser_utils import check_browser_connection

                browser_status = check_browser_connection()
                if not browser_status.get("connected", False):
                    raise ValueError("Browser not connected. Start browser with --remote-debugging-port=9222")

                if not board_name:
                    raise ValueError("Pinterest board name is required")

                design_state = workflow_state or {}
                design_state["title"] = design_state.get("title", "")
                design_state["description"] = design_state.get("description", "")
                design_state["seo_keywords"] = design_state.get("seo_keywords", [])

                from utils.folder_monitor import get_images_in_folder
                all_in_folder = get_images_in_folder(design_package_path)
                has_book_config = (Path(design_package_path) / "book_config.json").exists()
                use_direct = has_book_config and len(all_in_folder) > 0

                workflow = PinterestPublishingWorkflow()
                folder_path = workflow.prepare_publishing_folder(
                    design_state=design_state,
                    images_folder=design_package_path,
                    selected_images=None,
                    use_folder_directly=use_direct,
                )

                def progress_cb(progress: dict) -> None:
                    shared["step_progress"] = dict(progress)

                workflow.publish_to_pinterest(
                    folder_path=folder_path,
                    board_name=board_name,
                    progress_callback=progress_cb,
                )

            shared["step_status"] = "completed"
            shared["workflow_state"] = _prepare_state_for_serialization(workflow_state) if workflow_state else {}

        except Exception as e:
            shared["status"] = "failed"
            shared["error"] = str(e)
            shared["step_status"] = "failed"
            shared["running"] = False
            return

    shared["status"] = "completed"
    shared["running"] = False
    shared["design_package_path"] = design_package_path


def _prepare_state_for_serialization(state: dict) -> dict:
    """Prepare workflow state for serialization (Manager.dict can only hold JSON-serializable)."""
    import json
    result = {}
    for k, v in state.items():
        try:
            json.dumps(v)
            result[k] = v
        except (TypeError, ValueError):
            if k not in ("messages",):
                result[k] = str(v)
    return result


def run_pipeline(
    steps: list[str],
    config: dict[str, Any],
) -> tuple[multiprocessing.Process, multiprocessing.managers.SyncManager, dict]:
    """
    Start pipeline in a subprocess. Returns (process, manager, shared_dict).
    Caller should poll shared_dict for progress and process.join() when done.
    """
    manager = multiprocessing.Manager()
    shared = manager.dict()

    config_serializable = {}
    for k, v in config.items():
        if k == "workflow_state" and isinstance(v, dict):
            config_serializable[k] = _prepare_state_for_serialization(v)
        elif isinstance(v, (str, int, float, bool, list, dict, type(None))):
            config_serializable[k] = v
        else:
            config_serializable[k] = str(v)

    proc = multiprocessing.Process(
        target=_run_pipeline_process,
        args=(steps, config_serializable, shared),
        daemon=True,
    )
    proc.start()

    return proc, manager, shared
