"""Orchestration tab - run pipeline workflows with templates and progress visualization."""

from __future__ import annotations

import streamlit as st
from pathlib import Path

from core.browser_config import check_browser_connection, get_port_for_role
from core.pipeline_templates import (
    PIPELINE_STEPS,
    TEMPLATES,
    get_template_steps,
    get_step_by_id,
    validate_pipeline,
)
from core.pipeline_runner import run_pipeline
from core.jobs import has_running_image_job
from core.persistence import list_design_packages, load_design_package


def _init_orchestrator_state() -> None:
    """Initialize session state for orchestration tab."""
    defaults = {
        "orchestrator_pipeline": [],
        "orchestrator_template": "",
        "orchestrator_config": {},
        "orchestrator_process": None,
        "orchestrator_shared": None,
        "orchestrator_manager": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _get_template_options() -> list[str]:
    """Get template names for dropdown, including custom templates if available."""
    options = [n for n in TEMPLATES.keys() if n != "Empty"]
    try:
        from core.pipeline_persistence import list_custom_templates
        custom = list_custom_templates()
        if custom:
            options.extend([f"[Custom] {t['name']}" for t in custom])
    except ImportError:
        pass
    return options


def _resolve_template_steps(template_name: str) -> list[str]:
    """Resolve template name to step list. Handles custom templates."""
    if template_name.startswith("[Custom] "):
        name = template_name.replace("[Custom] ", "")
        try:
            from core.pipeline_persistence import load_custom_template
            return load_custom_template(name) or []
        except ImportError:
            return []
    return get_template_steps(template_name)


@st.fragment
def render_orchestration_tab() -> None:
    """Render the Orchestration tab with template selector, step list, and run controls. Fragment so tab stays stable when other tabs rerun."""
    _init_orchestrator_state()

    st.header("Pipeline Orchestration")
    st.caption(
        "Run workflows sequentially. Start from a template, then add or remove steps as needed."
    )

    pipeline = st.session_state.get("orchestrator_pipeline", [])
    workflow_state = st.session_state.get("workflow_state")
    design_package_path = (workflow_state or {}).get("design_package_path", "")

    # --- Template selector ---
    st.caption("**Start from template**")
    col_tpl, col_apply = st.columns([3, 1])
    with col_tpl:
        template_options = _get_template_options()
        selected_template = st.selectbox(
            "Start from template",
            options=template_options,
            key="orchestrator_template_select",
            index=0 if template_options else 0,
            label_visibility="collapsed",
        )
    with col_apply:
        apply_clicked = st.button("Apply", key="orchestrator_apply_btn", use_container_width=True)
    if apply_clicked:
        steps = _resolve_template_steps(selected_template)
        st.session_state.orchestrator_pipeline = steps
        st.session_state.orchestrator_template = selected_template
        st.rerun()
    if st.session_state.get("orchestrator_template"):
        st.caption(f"Current: **{st.session_state.orchestrator_template}**")

    # --- Step list (two columns) ---
    st.subheader("Pipeline steps")
    st.caption("Check the steps to include. Order is fixed.")

    mid = (len(PIPELINE_STEPS) + 1) // 2
    left_steps, right_steps = PIPELINE_STEPS[:mid], PIPELINE_STEPS[mid:]
    new_pipeline = []
    col_left, col_right = st.columns(2)
    with col_left:
        for step_def in left_steps:
            step_id = step_def["id"]
            default = step_id in pipeline
            checked = st.checkbox(
                step_def["label"],
                value=default,
                key=f"orchestrator_step_{step_id}",
                help=step_def.get("description", ""),
            )
            if checked:
                new_pipeline.append(step_id)
    with col_right:
        for step_def in right_steps:
            step_id = step_def["id"]
            default = step_id in pipeline
            checked = st.checkbox(
                step_def["label"],
                value=default,
                key=f"orchestrator_step_{step_id}",
                help=step_def.get("description", ""),
            )
            if checked:
                new_pipeline.append(step_id)
    # Preserve step order (left column first, then right)
    order = [s["id"] for s in PIPELINE_STEPS]
    new_pipeline = [s for s in order if s in new_pipeline]

    if new_pipeline != pipeline:
        st.session_state.orchestrator_pipeline = new_pipeline

    pipeline = st.session_state.orchestrator_pipeline

    # --- Design package selector (when image or downstream) ---
    needs_design_package = any(
        get_step_by_id(s) and get_step_by_id(s).get("requires_design_package")
        for s in pipeline
    )
    design_first = pipeline and pipeline[0] == "design" if pipeline else False

    if needs_design_package:
        st.subheader("Design package")
        packages = list_design_packages()
        if not packages:
            st.warning("No design packages found. Create one in the Design Generation tab first.")
        else:
            st.caption("**Design package**")
            options = ["— Select —"] + [f"{p['title']} ({p['image_count']} imgs)" for p in packages]
            col_sel, col_load = st.columns([4, 1])
            with col_sel:
                selected_idx = st.selectbox(
                    "Design package",
                    options=options,
                    key="orchestrator_design_pkg_select",
                    label_visibility="collapsed",
                )
            with col_load:
                load_clicked = st.button("Load package", key="orchestrator_load_pkg_btn", use_container_width=True)
            if selected_idx and selected_idx != "— Select —":
                idx = options.index(selected_idx) - 1
                pkg = packages[idx]
                design_package_path = pkg["path"]
                st.session_state.orchestrator_design_package_path = design_package_path
                if load_clicked:
                    loaded = load_design_package(pkg["path"])
                    if loaded:
                        st.session_state.workflow_state = loaded
                        st.success("Package loaded.")
                        st.rerun()
            else:
                design_package_path = st.session_state.get("orchestrator_design_package_path", "")

        if not design_package_path and (workflow_state or {}).get("design_package_path"):
            design_package_path = (workflow_state or {}).get("design_package_path", "")

    # --- Design input (when design in pipeline) ---
    if "design" in pipeline:
        st.subheader("Design input")
        user_request = st.text_area(
            "Design idea",
            value=st.session_state.get("orchestrator_user_request", ""),
            placeholder="e.g. forest animals for adults with mandala patterns",
            key="orchestrator_user_request",
            height=80,
        )
    else:
        user_request = ""

    # --- Per-step config (one row when both Canva + Pinterest) ---
    if "canva" in pipeline or "pinterest" in pipeline:
        with st.expander("Step configuration", expanded=False):
            config = st.session_state.get("orchestrator_config", {})
            canva_config = config.get("canva_config", {})
            if "canva" in pipeline and "pinterest" in pipeline:
                col_ps, col_m, col_o, col_blank, col_board = st.columns([2, 1, 1, 1, 2])
                with col_ps:
                    canva_config["page_size"] = st.text_input(
                        "Page size",
                        value=canva_config.get("page_size", "8.625x8.75"),
                        key="orchestrator_canva_page_size",
                    )
                with col_m:
                    canva_config["margin_percent"] = st.number_input(
                        "Margin %",
                        min_value=0.0,
                        max_value=50.0,
                        value=float(canva_config.get("margin_percent", 8.0)),
                        key="orchestrator_canva_margin",
                    )
                with col_o:
                    canva_config["outline_height_percent"] = st.number_input(
                        "Outline %",
                        min_value=0.0,
                        max_value=50.0,
                        value=float(canva_config.get("outline_height_percent", 6.0)),
                        key="orchestrator_canva_outline",
                    )
                with col_blank:
                    canva_config["blank_between"] = st.checkbox(
                        "Blank between",
                        value=canva_config.get("blank_between", True),
                        key="orchestrator_canva_blank",
                    )
                with col_board:
                    config["board_name"] = st.text_input(
                        "Pinterest board",
                        value=config.get("board_name", ""),
                        key="orchestrator_pinterest_board",
                        placeholder="e.g. Coloring Books",
                    )
            elif "canva" in pipeline:
                col_ps, col_m, col_o, col_blank = st.columns([2, 1, 1, 1])
                with col_ps:
                    canva_config["page_size"] = st.text_input(
                        "Page size",
                        value=canva_config.get("page_size", "8.625x8.75"),
                        key="orchestrator_canva_page_size",
                    )
                with col_m:
                    canva_config["margin_percent"] = st.number_input(
                        "Margin %",
                        min_value=0.0,
                        max_value=50.0,
                        value=float(canva_config.get("margin_percent", 8.0)),
                        key="orchestrator_canva_margin",
                    )
                with col_o:
                    canva_config["outline_height_percent"] = st.number_input(
                        "Outline %",
                        min_value=0.0,
                        max_value=50.0,
                        value=float(canva_config.get("outline_height_percent", 6.0)),
                        key="orchestrator_canva_outline",
                    )
                with col_blank:
                    canva_config["blank_between"] = st.checkbox(
                        "Blank between",
                        value=canva_config.get("blank_between", True),
                        key="orchestrator_canva_blank",
                    )
            else:
                config["board_name"] = st.text_input(
                    "Pinterest board",
                    value=config.get("board_name", ""),
                    key="orchestrator_pinterest_board",
                    placeholder="e.g. Coloring Books",
                )
            config["canva_config"] = canva_config
            st.session_state.orchestrator_config = config

    config = st.session_state.get("orchestrator_config", {})
    board_name = config.get("board_name", "")

    # --- Validation ---
    has_design_pkg = bool(
        design_package_path
        or st.session_state.get("orchestrator_design_package_path")
        or (workflow_state or {}).get("design_package_path")
    )
    errors = validate_pipeline(
        pipeline,
        has_design_package=has_design_pkg,
        has_user_request=bool(user_request.strip()),
        has_board_name=bool(board_name.strip()),
    )

    # --- Run / Progress ---
    process = st.session_state.get("orchestrator_process")
    shared = st.session_state.get("orchestrator_shared")
    running = process is not None and shared is not None and shared.get("running", False)

    if running and process and process.is_alive():
        _render_progress(shared, pipeline)
        if st.button("Refresh status", key="orchestrator_refresh_btn"):
            st.rerun()
        st.stop()

    if process and not process.is_alive() and shared:
        status = shared.get("status", "")
        if status == "completed":
            st.success("Pipeline completed successfully!")
            pkg_path = shared.get("design_package_path", "")
            if pkg_path:
                loaded = load_design_package(pkg_path)
                if loaded:
                    st.session_state.workflow_state = loaded
        elif status == "failed":
            st.error(f"Pipeline failed: {shared.get('error', 'Unknown error')}")
        st.session_state.orchestrator_process = None
        st.session_state.orchestrator_shared = None
        st.session_state.orchestrator_manager = None
        if st.button("Dismiss", key="orchestrator_dismiss_btn"):
            st.rerun()
        st.stop()

    # --- Run button + status on one row ---
    can_run = (
        len(pipeline) > 0
        and len(errors) == 0
        and not running
    )

    col_run, col_status = st.columns([2, 3])
    with col_run:
        run_clicked = st.button("Run pipeline", type="primary", disabled=not can_run, key="orchestrator_run_btn", use_container_width=True)
    with col_status:
        if not can_run:
            if running:
                st.caption("Pipeline is running. Wait or refresh status.")
            elif errors:
                st.caption(f"{len(errors)} error(s) — fix above to enable Run.")
            elif not pipeline:
                st.caption("Add at least one step above to enable Run.")
            else:
                st.caption("Complete requirements above to enable Run.")
        else:
            st.caption("Ready — click Run pipeline to start.")
    if errors:
        with st.expander("Pipeline errors", expanded=True):
            for err in errors:
                st.error(err)
            st.caption("Fix the issues above (e.g. add a design package, enter design idea, or set board name in Step configuration) and try again.")

    if run_clicked:
        # Enforce global serialization for image generation jobs.
        if "image" in pipeline and has_running_image_job():
            st.error(
                "An image generation job is already running. "
                "Please wait for it to complete before starting another pipeline with an Image step."
            )
            st.stop()

        needs_browser = any(s in pipeline for s in ["image", "canva", "pinterest"])
        if needs_browser:
            role_to_step = {"midjourney": "image", "canva": "canva", "pinterest": "pinterest"}
            missing = []
            for role, step_id in role_to_step.items():
                if step_id not in pipeline:
                    continue
                port = get_port_for_role(role)
                status = check_browser_connection(port)
                if not status.get("connected", False):
                    missing.append(f"{role} (port {port})")
            if missing:
                st.error(
                    "Browser not connected for: "
                    + ", ".join(missing)
                    + ". Start browser(s) with remote debugging on the configured ports (Config tab)."
                )
                st.stop()

        effective_pkg_path = (
            design_package_path
            or st.session_state.get("orchestrator_design_package_path", "")
            or (workflow_state or {}).get("design_package_path", "")
        )
        run_config = {
            "user_request": user_request.strip(),
            "design_package_path": effective_pkg_path,
            "workflow_state": workflow_state,
            "board_name": board_name.strip(),
            "canva_config": config.get("canva_config", {}),
        }

        proc, manager, shared_dict = run_pipeline(pipeline, run_config)
        st.session_state.orchestrator_process = proc
        st.session_state.orchestrator_manager = manager
        st.session_state.orchestrator_shared = shared_dict
        st.rerun()

    # --- Save as template (name + button on one row) ---
    if pipeline and st.session_state.get("orchestrator_template"):
        resolved = _resolve_template_steps(st.session_state.orchestrator_template)
        if pipeline != resolved:
            st.caption("Pipeline modified from template. **Template name**")
            col_name, col_save = st.columns([3, 1])
            with col_name:
                custom_name = st.text_input(
                    "Template name",
                    value=st.session_state.get("orchestrator_custom_template_name", "My pipeline"),
                    key="orchestrator_custom_template_name",
                    placeholder="e.g. My usual publish run",
                    label_visibility="collapsed",
                )
            with col_save:
                save_tpl_clicked = st.button("Save as custom template", key="orchestrator_save_template_btn", use_container_width=True)
            if save_tpl_clicked:
                try:
                    from core.pipeline_persistence import save_custom_template
                    name = (custom_name or "").strip() or "My pipeline"
                    save_custom_template(name, pipeline)
                    st.success(f"Saved as '{name}'")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save template: {e}")


def _render_progress(shared: dict, pipeline: list[str]) -> None:
    """Render pipeline progress display."""
    st.subheader("Pipeline progress")

    current_idx = shared.get("current_step_index", -1)
    current_id = shared.get("current_step_id", "")
    step_status = shared.get("step_status", "")
    step_progress = shared.get("step_progress", {}) or {}

    step_labels = {s["id"]: s["label"] for s in PIPELINE_STEPS}

    # Step indicator
    total = len(pipeline)
    if current_idx >= 0 and current_idx < total:
        label = step_labels.get(current_id, current_id)
        st.metric("Current step", f"{current_idx + 1}/{total}: {label}")

    # Per-step progress (for Image step - MJ progress)
    if current_id == "image":
        publish_status = step_progress.get("publish_status", "")
        uxd_status = step_progress.get("uxd_action_status", "")
        download_status = step_progress.get("download_status", "")
        batch_idx = step_progress.get("batch_current_index", 0)
        batch_total = step_progress.get("batch_total", 0)

        cols = st.columns(3)
        with cols[0]:
            st.caption("Publish")
            st.write(publish_status or "idle")
        with cols[1]:
            st.caption("Upscale/Vary")
            st.write(uxd_status or "idle")
        with cols[2]:
            st.caption("Download")
            st.write(download_status or "idle")
        if batch_total > 0:
            st.progress(batch_idx / batch_total if batch_total else 0)
            st.caption(f"Design {batch_idx}/{batch_total}")

    elif current_id == "evaluate":
        cur = step_progress.get("current", 0)
        total = step_progress.get("total", 1)
        if total > 0:
            st.progress(cur / total)
            st.caption(f"Evaluating image {cur}/{total}")

    elif current_id in ("canva", "pinterest"):
        msg = step_progress.get("message", step_progress.get("status", "In progress..."))
        st.info(msg)
        cur = step_progress.get("current", 0)
        tot = step_progress.get("total", 0)
        if tot > 0:
            st.progress(cur / tot)
