"""Canva Design tab."""

from __future__ import annotations

import streamlit as st
from pathlib import Path

from core.browser_config import check_browser_connection, get_port_for_role
from workflows.canva.designer import CanvaDesignWorkflow
from ui.components.canva_components import (
    render_canva_combined_checks,
    render_canva_configuration_section,
    render_canva_progress_display,
    render_canva_results_summary,
)

CANVA_TAB_STATE_KEY = "canva_tab_state"


def _resolve_canva_state(workflow_state: dict | None) -> tuple[dict | None, bool]:
    """Resolve state from workflow or tab-specific load. Returns (state, from_workflow)."""
    state = workflow_state or st.session_state.get(CANVA_TAB_STATE_KEY)
    from_workflow = state is workflow_state and workflow_state is not None
    return state, from_workflow


def _persist_canva_state(state: dict, from_workflow: bool) -> None:
    if from_workflow:
        st.session_state.workflow_state = state
    else:
        st.session_state[CANVA_TAB_STATE_KEY] = state


def render_canva_tab(workflow_state: dict | None) -> None:
    """Render the Canva Design tab. Uses workflow_state or a design loaded in this tab."""
    st.header("Canva Design")

    from ui.components.design_selector import render_tab_design_selector
    render_tab_design_selector("canva", persist_to_workflow=True, tab_state_key=CANVA_TAB_STATE_KEY)
    st.markdown("---")

    state, from_workflow = _resolve_canva_state(st.session_state.get("workflow_state"))
    if state is None:
        st.info("Load a design package above or create one in the Design Generation tab.")
        return

    st.caption(f"Using: **{state.get('title', 'Untitled')}**" + (" (from sidebar)" if from_workflow else " (loaded in this tab)"))

    if "canva_workflow" not in st.session_state:
        st.session_state.canva_workflow = CanvaDesignWorkflow()
    workflow = st.session_state.canva_workflow

    if "canva_status" not in state:
        state["canva_status"] = "pending"
    if "canva_progress" not in state:
        state["canva_progress"] = {}
    if "canva_results" not in state:
        state["canva_results"] = {}
    # Migrate from legacy keys; use shared browser_status (same port for Canva and Pinterest)
    if "browser_status" not in state:
        legacy = state.get("canva_browser_status") or state.get("pinterest_browser_status")
        state["browser_status"] = legacy if isinstance(legacy, dict) else {}

    canva_port = get_port_for_role("canva")
    if st.session_state.get("check_browser_canva_clicked", False):
        st.session_state.check_browser_canva_clicked = False
        browser_status = check_browser_connection(canva_port)
        state["browser_status"] = browser_status
        _persist_canva_state(state, from_workflow)

    if st.session_state.get("refresh_browser_check_canva", False):
        st.session_state.refresh_browser_check_canva = False
        browser_status = check_browser_connection(canva_port)
        state["browser_status"] = browser_status
        _persist_canva_state(state, from_workflow)

    if not state.get("browser_status"):
        browser_status = check_browser_connection(canva_port)
        state["browser_status"] = browser_status
        _persist_canva_state(state, from_workflow)

    prerequisites = render_canva_combined_checks(state)
    images_folder_path = prerequisites.get("images_folder_path", state.get("images_folder_path", ""))
    browser_status = state.get("browser_status", {})

    if prerequisites["all_ready"]:
        with st.expander("Configuration", expanded=False):
            config = render_canva_configuration_section(state)
        if not config["images_folder"] and images_folder_path:
            config["images_folder"] = images_folder_path
        if config["page_size"]:
            state["canva_page_size"] = config["page_size"]
        if "margin_percent" in config:
            state["canva_margin_percent"] = config["margin_percent"]
        if "outline_height_percent" in config:
            state["canva_outline_height_percent"] = config["outline_height_percent"]
        if "blank_between" in config:
            state["canva_blank_between"] = config["blank_between"]
        _persist_canva_state(state, from_workflow)

        st.subheader("Design Creation")
        if state.get("canva_status") == "creating":
            render_canva_progress_display(state.get("canva_progress", {}))

        if not config["images_folder"]:
            st.error("No images folder. Set folder in Image Generation tab.")
        elif not Path(config["images_folder"]).exists():
            st.error(f"Folder not found: `{config['images_folder']}`")
        else:
            can_create = prerequisites["all_ready"] and config["images_folder"] and browser_status.get("connected", False)
            n_images = prerequisites.get("image_count", 0)
            col_start, col_status = st.columns([2, 3])
            with col_start:
                start_clicked = st.button("Start Design Creation", disabled=not can_create, key="start_canva_design_btn", use_container_width=True)
            with col_status:
                if can_create:
                    st.caption(f"Ready. {n_images} images.")
                else:
                    if not browser_status.get("connected", False):
                        st.caption("Browser not connected.")
                    elif not config["images_folder"]:
                        st.caption("No images folder.")
                    else:
                        st.caption("Complete prerequisites above.")
            if start_clicked and can_create:
                try:
                    state["canva_status"] = "creating"
                    _persist_canva_state(state, from_workflow)

                    def progress_callback(progress_update: dict):
                        state["canva_progress"] = progress_update
                        _persist_canva_state(state, from_workflow)

                    selected = state.get("selected_images") or []
                    with st.spinner("Creating Canva design..."):
                        results = workflow.create_design(
                            images_folder=config["images_folder"],
                            page_size=config["page_size"],
                            margin_percent=config["margin_percent"],
                            outline_height_percent=config["outline_height_percent"],
                            blank_between=config["blank_between"],
                            progress_callback=progress_callback,
                            selected_images=selected if selected else None,
                        )
                        state["canva_results"] = results
                        state["canva_status"] = "completed" if results.get("success", False) else "failed"
                        _persist_canva_state(state, from_workflow)
                    st.rerun()
                except Exception as e:
                    import traceback
                    st.error(f"Error: {str(e)}")
                    with st.expander("Error Details", expanded=False):
                        st.code(traceback.format_exc())
                    state["canva_status"] = "failed"
                    _persist_canva_state(state, from_workflow)

        if state.get("canva_status") in ["completed", "failed"]:
            render_canva_results_summary(state.get("canva_results", {}))
    else:
        missing = []
        if not prerequisites["checks"]["design_generated"]:
            missing.append("Design package (Design Generation tab)")
        if not prerequisites["checks"]["images_available"]:
            missing.append("Images (Image Generation tab)")
        if not prerequisites["checks"]["browser_connected"]:
            missing.append("Browser (Check Browser above)")
        st.info("Complete: " + ", ".join(missing))
