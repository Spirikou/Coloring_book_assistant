"""Pinterest Publishing tab."""

from __future__ import annotations

import streamlit as st
from pathlib import Path

from core.browser_config import check_browser_connection, get_port_for_role
from core.persistence import load_pinterest_config
from workflows.pinterest.publisher import PinterestPublishingWorkflow
from ui.components.pinterest_components import (
    render_pinterest_combined_checks,
    render_configuration_section,
    render_preview_section,
    render_progress_display,
    render_results_summary,
    render_session_management,
)

PINTEREST_TAB_STATE_KEY = "pinterest_tab_state"


def _resolve_pinterest_state(workflow_state: dict | None) -> tuple[dict | None, bool]:
    """Resolve state from workflow or tab-specific load. Returns (state, from_workflow)."""
    state = workflow_state or st.session_state.get(PINTEREST_TAB_STATE_KEY)
    from_workflow = state is workflow_state and workflow_state is not None
    return state, from_workflow


def _persist_pinterest_state(state: dict, from_workflow: bool) -> None:
    if from_workflow:
        st.session_state.workflow_state = state
    else:
        st.session_state[PINTEREST_TAB_STATE_KEY] = state


def render_pinterest_tab(workflow_state: dict | None) -> None:
    """Render the Pinterest Publishing tab. Uses workflow_state or a design loaded in this tab."""
    st.header("Pinterest Publishing")

    mode = st.radio(
        "Mode",
        options=["Bulk", "Single design"],
        horizontal=True,
        key="pinterest_mode_select",
        help="Bulk publishes multiple design packages sequentially. Single design publishes the current loaded design package.",
    )
    st.markdown("---")

    state, from_workflow = _resolve_pinterest_state(st.session_state.get("workflow_state"))

    if "pinterest_workflow" not in st.session_state:
        st.session_state.pinterest_workflow = PinterestPublishingWorkflow()
    workflow = st.session_state.pinterest_workflow

    pinterest_port = get_port_for_role("pinterest")
    if mode == "Bulk":
        # Bulk runs don't require a design loaded; keep a small bulk state for checks.
        if "pinterest_bulk_state" not in st.session_state:
            st.session_state["pinterest_bulk_state"] = {"browser_status": {}}
        bulk_state: dict = st.session_state.get("pinterest_bulk_state") or {"browser_status": {}}

        if st.session_state.get("check_browser_clicked", False):
            st.session_state.check_browser_clicked = False
            bs = check_browser_connection(pinterest_port)
            bulk_state["browser_status"] = bs
            st.session_state["pinterest_bulk_state"] = bulk_state

        if st.session_state.get("refresh_browser_check_pinterest", False):
            st.session_state.refresh_browser_check_pinterest = False
            bs = check_browser_connection(pinterest_port)
            bulk_state["browser_status"] = bs
            st.session_state["pinterest_bulk_state"] = bulk_state

        bulk_browser_status = bulk_state.get("browser_status") or check_browser_connection(pinterest_port)
        bulk_state["browser_status"] = bulk_browser_status
        st.session_state["pinterest_bulk_state"] = bulk_state

        st.subheader("Bulk setup")
        render_pinterest_combined_checks(bulk_state, key_prefix="pinterest_bulk")

        with st.expander("Bulk Pinterest — run multiple designs (sequential)", expanded=True):
            from core.persistence import list_design_packages, load_design_package, load_pinterest_config
            from features.image_generation.monitor import get_images_in_folder
            from ui.components.bulk_runners import build_design_package_options, run_bulk_pinterest

            packages = list_design_packages()
            saved_cfg = load_pinterest_config() or {}
            default_board = saved_cfg.get("board_name", "")
            default_max_pins = int(saved_cfg.get("max_pins_per_design", 0) or 0)

            col_board, col_max = st.columns([2, 1])
            with col_board:
                bulk_board_name = st.text_input(
                    "Pinterest board",
                    value=st.session_state.get("pinterest_bulk_board_name", default_board),
                    key="pinterest_bulk_board_name_input",
                    placeholder="e.g. Coloring Books",
                ).strip()
                st.session_state["pinterest_bulk_board_name"] = bulk_board_name
            with col_max:
                bulk_max_pins = st.number_input(
                    "Max pins per design",
                    min_value=0,
                    max_value=500,
                    value=int(st.session_state.get("pinterest_bulk_max_pins", default_max_pins) or 0),
                    step=1,
                    key="pinterest_bulk_max_pins_input",
                )
                st.session_state["pinterest_bulk_max_pins"] = int(bulk_max_pins or 0)

            if not packages:
                st.caption("No design packages found. Create some in the Design Generation tab first.")
                return

            options = build_design_package_options(packages)
            selected_labels = st.multiselect(
                "Design packages to publish",
                options=list(options.keys()),
                key="pinterest_bulk_package_select",
            )

            bulk_can_publish = (
                bool(selected_labels)
                and bulk_browser_status.get("connected", False)
                and bool(bulk_board_name)
            )
            col_run, col_info = st.columns([2, 3])
            with col_run:
                bulk_clicked = st.button(
                    "Run bulk Pinterest",
                    disabled=not bulk_can_publish,
                    key="pinterest_bulk_start_btn",
                    use_container_width=True,
                )
            with col_info:
                if not selected_labels:
                    st.caption("Select at least one design package to enable bulk Pinterest.")
                elif not bulk_board_name:
                    st.caption("Set a board name above to enable bulk Pinterest.")
                elif not bulk_browser_status.get("connected", False):
                    st.caption(f"Browser not connected on Pinterest slot (port {pinterest_port}). Connect it in the Config tab.")
                else:
                    limit_text = f" (max {int(bulk_max_pins)} pins per design)" if int(bulk_max_pins) > 0 else " (all images)"
                    st.caption(f"{len(selected_labels)} design(s) will be published sequentially{limit_text}.")

            if bulk_clicked and bulk_can_publish:
                selected_paths = [options[lbl] for lbl in selected_labels if options.get(lbl)]
                run_bulk_pinterest(
                    st=st,
                    workflow=workflow,
                    selected_design_paths=selected_paths,
                    load_design_package=load_design_package,
                    get_images_in_folder=get_images_in_folder,
                    board_name=bulk_board_name,
                    max_pins_per_design=int(bulk_max_pins or 0),
                )

        return

    # Single-design UI below (requires a design loaded)
    st.subheader("Single design")
    from ui.components.design_selector import render_tab_design_selector
    render_tab_design_selector("pinterest", persist_to_workflow=True, tab_state_key=PINTEREST_TAB_STATE_KEY)
    st.markdown("---")

    state, from_workflow = _resolve_pinterest_state(st.session_state.get("workflow_state"))
    if state is None:
        st.info("Load a design package above to start the single-design Pinterest workflow.")
        return

    st.caption(
        f"Using: **{state.get('title', 'Untitled')}**"
        + (" (from sidebar)" if from_workflow else " (loaded in this tab)")
    )

    if "pinterest_status" not in state:
        state["pinterest_status"] = "pending"
    if "pinterest_progress" not in state:
        state["pinterest_progress"] = {}
    if "pinterest_results" not in state:
        state["pinterest_results"] = {}
    # Migrate from legacy keys; use shared browser_status (same port for Canva and Pinterest)
    if "browser_status" not in state:
        legacy = state.get("pinterest_browser_status") or state.get("canva_browser_status")
        state["browser_status"] = legacy if isinstance(legacy, dict) else {}
    if "pinterest_board_name" not in state:
        state["pinterest_board_name"] = ""
    if "pinterest_folder_path" not in state:
        state["pinterest_folder_path"] = ""

    # check_browser_clicked / refresh_browser_check_pinterest are handled above (bulk + single)

    if not state.get("browser_status"):
        browser_status = check_browser_connection(pinterest_port)
        state["browser_status"] = browser_status
        _persist_pinterest_state(state, from_workflow)

    prerequisites = render_pinterest_combined_checks(state, key_prefix="pinterest_single")
    images_folder_path = prerequisites.get("images_folder_path", state.get("images_folder_path", ""))
    image_count = prerequisites.get("image_count", 0)
    browser_status = state.get("browser_status", {})

    if prerequisites["all_ready"]:
        with st.expander("Configuration", expanded=False):
            config = render_configuration_section(state, effective_images_folder=images_folder_path)
        if not config["images_folder"] and images_folder_path:
            config["images_folder"] = images_folder_path
        if config["board_name"]:
            state["pinterest_board_name"] = config["board_name"]
            _persist_pinterest_state(state, from_workflow)

        st.subheader("Publishing")
        if state.get("pinterest_status") == "publishing":
            render_progress_display(state.get("pinterest_progress", {}))

        if not config["images_folder"]:
            st.error("No images folder. Set folder in Image Generation tab.")
        elif not Path(config["images_folder"]).exists():
            st.error(f"Folder not found: `{config['images_folder']}`")
        else:
            # Preview: editable title, description, image grid
            preview = render_preview_section(state, config["images_folder"])

            # Apply max pins per design limit (0 = publish all)
            selected = preview.get("selected_images") or []
            max_pins = int(config.get("max_pins_per_design", state.get("pinterest_max_pins_per_design", 0)) or 0)
            total_selected_before_limit = len(selected)
            if max_pins > 0 and selected:
                selected = selected[:max_pins]

            # Update state with the effective limit for this run
            state["pinterest_max_pins_per_design"] = max_pins
            _persist_pinterest_state(state, from_workflow)

            can_publish = (
                prerequisites["all_ready"]
                and config["board_name"]
                and browser_status.get("connected", False)
                and config["images_folder"]
                and len(selected) > 0
            )
            n_images_effective = len(selected)
            col_start, col_status = st.columns([2, 3])
            with col_start:
                start_clicked = st.button("Start Publishing", disabled=not can_publish, key="start_publishing_btn", use_container_width=True)
            with col_status:
                if can_publish:
                    if max_pins > 0 and total_selected_before_limit > max_pins:
                        st.caption(
                            f"{n_images_effective} image(s) (limited to first {max_pins} "
                            f"of {total_selected_before_limit}) → board **{config['board_name']}** — ready to publish."
                        )
                    else:
                        st.caption(f"{n_images_effective} image(s) → board **{config['board_name']}** — ready to publish.")
                else:
                    if not config["board_name"]:
                        st.caption("Set board name in Configuration to enable Start Publishing.")
                    elif not browser_status.get("connected", False):
                        st.caption("Connect browser (System & Prerequisites) to enable Start Publishing.")
                    elif image_count == 0:
                        st.caption("Add images to publish (or check the images folder) to enable Start Publishing.")
                    else:
                        st.caption("Complete prerequisites above to enable Start Publishing.")

            if start_clicked:
                try:
                    from integrations.pinterest.workflow_logger import get_workflow_logger
                    workflow_logger = get_workflow_logger()
                except Exception:
                    workflow_logger = None

                try:
                    with st.spinner("Preparing..."):
                        state["pinterest_status"] = "preparing"
                        state["images_folder_path"] = config["images_folder"]
                        _persist_pinterest_state(state, from_workflow)
                        # Use preview selection (user may have removed images), already limited above
                        design_state = {**state, "title": preview["title"], "description": preview["description"]}
                        folder = config["images_folder"]
                        from features.image_generation.monitor import get_images_in_folder
                        all_in_folder = get_images_in_folder(folder)
                        # If we have a max limit or explicit selection, treat as exclusions to force copy-based folder
                        no_exclusions = (
                            len(selected) == 0
                            or (
                                max_pins == 0
                                and len(selected) == len(all_in_folder)
                            )
                        )
                        has_book_config = (Path(folder) / "book_config.json").exists()
                        use_direct = has_book_config and no_exclusions
                        folder_path = workflow.prepare_publishing_folder(
                            design_state=design_state,
                            images_folder=folder,
                            selected_images=selected if selected else None,
                            use_folder_directly=use_direct,
                        )
                        state["pinterest_folder_path"] = folder_path
                        state["pinterest_status"] = "publishing"
                        _persist_pinterest_state(state, from_workflow)

                    progress_placeholder = st.empty()

                    def progress_callback(progress_update: dict):
                        state["pinterest_progress"] = progress_update
                        _persist_pinterest_state(state, from_workflow)
                        cur = progress_update.get("current", 0)
                        tot = progress_update.get("total", 0)
                        with progress_placeholder.container():
                            if tot > 0:
                                st.caption(f"Publishing {cur}/{tot} pins...")
                            else:
                                st.caption(progress_update.get("message", "Publishing pins..."))

                    with st.spinner("Publishing pins..."):
                        results = workflow.publish_to_pinterest(
                            folder_path=folder_path,
                            board_name=config["board_name"],
                            progress_callback=progress_callback
                        )
                        state["pinterest_results"] = results
                        state["pinterest_status"] = "completed" if results.get("success", False) else "failed"
                        _persist_pinterest_state(state, from_workflow)
                        if state["pinterest_status"] == "completed":
                            from core.notifications import notify_completed
                            notify_completed(
                                "task.completed",
                                task_id=state.get("design_package_path", "pinterest") or "pinterest",
                                task_name="Pinterest Publish",
                                result_summary=f"{results.get('pins_published', 0)} pins published",
                            )
                    st.rerun()
                except Exception as e:
                    import traceback
                    st.error(f"Error: {str(e)}")
                    with st.expander("Error Details", expanded=False):
                        st.code(traceback.format_exc())
                    if workflow_logger:
                        try:
                            workflow_logger.log_error(e, "pinterest_tab")
                            st.info(f"Log: `{workflow_logger.log_file}`")
                        except Exception:
                            pass
                    state["pinterest_status"] = "failed"
                    _persist_pinterest_state(state, from_workflow)

        if state.get("pinterest_status") in ["completed", "failed"]:
            render_results_summary(state.get("pinterest_results", {}))

        # Publishing Sessions section
        with st.expander("Publishing Sessions — browse and manage past sessions", expanded=False):
            # Handle re-run from session detail
            if state.get("pinterest_rerun_requested") and state.get("pinterest_rerun_folder"):
                folder_path = state["pinterest_rerun_folder"]
                saved_config = load_pinterest_config()
                board_name = state.get("pinterest_board_name") or (saved_config.get("board_name", "") if saved_config else "")
                browser_status = state.get("browser_status", {})
                if board_name and browser_status.get("connected", False):
                    state["pinterest_rerun_requested"] = False
                    state["pinterest_status"] = "publishing"
                    _persist_pinterest_state(state, from_workflow)
                    progress_placeholder = st.empty()

                    def rerun_progress_callback(progress_update: dict):
                        state["pinterest_progress"] = progress_update
                        _persist_pinterest_state(state, from_workflow)
                        cur = progress_update.get("current", 0)
                        tot = progress_update.get("total", 0)
                        with progress_placeholder.container():
                            if tot > 0:
                                st.caption(f"Publishing {cur}/{tot} pins...")
                            else:
                                st.caption(progress_update.get("message", "Publishing pins..."))

                    try:
                        with st.spinner("Re-publishing pins..."):
                            results = workflow.publish_to_pinterest(
                                folder_path=folder_path,
                                board_name=board_name,
                                progress_callback=rerun_progress_callback,
                            )
                            state["pinterest_results"] = results
                            state["pinterest_status"] = "completed" if results.get("success", False) else "failed"
                            _persist_pinterest_state(state, from_workflow)
                            if state["pinterest_status"] == "completed":
                                from core.notifications import notify_completed
                                notify_completed(
                                    "task.completed",
                                    task_id=state.get("pinterest_rerun_folder", "pinterest-rerun") or "pinterest-rerun",
                                    task_name="Pinterest Publish",
                                    result_summary=f"{results.get('pins_published', 0)} pins published",
                                )
                        st.rerun()
                    except Exception as e:
                        import traceback
                        st.error(f"Error: {str(e)}")
                        with st.expander("Error Details", expanded=False):
                            st.code(traceback.format_exc())
                        state["pinterest_status"] = "failed"
                        state["pinterest_rerun_requested"] = False
                        _persist_pinterest_state(state, from_workflow)
                        st.rerun()
                else:
                    if not board_name:
                        st.error("Board name required for re-run. Set it in Configuration above.")
                    else:
                        st.error("Browser not connected. Check browser connection above.")
                    state["pinterest_rerun_requested"] = False
                    _persist_pinterest_state(state, from_workflow)

            render_session_management(state)
    else:
        missing = []
        if not prerequisites["checks"]["design_generated"]:
            missing.append("Design package (Design Generation tab)")
        if not prerequisites["checks"]["images_available"]:
            missing.append("Images (Image Generation tab)")
        if not prerequisites["checks"]["browser_connected"]:
            missing.append("Browser (Check Browser above)")
        st.info("Complete: " + ", ".join(missing))
