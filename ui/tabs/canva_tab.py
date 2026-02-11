"""Canva Design tab."""

import streamlit as st
from pathlib import Path

from integrations.pinterest.browser_utils import check_browser_connection
from workflows.canva.designer import CanvaDesignWorkflow
from ui.components.canva_components import (
    render_canva_combined_checks,
    render_canva_configuration_section,
    render_canva_progress_display,
    render_canva_results_summary,
)


def render_canva_tab(state: dict):
    """Render the Canva Design tab. Uses same images folder as Pinterest."""
    st.header("🎨 Canva Design")

    if "canva_workflow" not in st.session_state:
        st.session_state.canva_workflow = CanvaDesignWorkflow()
    workflow = st.session_state.canva_workflow

    if "canva_status" not in state:
        state["canva_status"] = "pending"
    if "canva_progress" not in state:
        state["canva_progress"] = {}
    if "canva_results" not in state:
        state["canva_results"] = {}
    if "canva_browser_status" not in state:
        state["canva_browser_status"] = {}

    if st.session_state.get("check_browser_canva_clicked", False):
        st.session_state.check_browser_canva_clicked = False
        browser_status = check_browser_connection()
        state["canva_browser_status"] = browser_status
        st.session_state.workflow_state = state

    if not state.get("canva_browser_status"):
        browser_status = check_browser_connection()
        state["canva_browser_status"] = browser_status
        st.session_state.workflow_state = state

    prerequisites = render_canva_combined_checks(state)
    images_folder_path = prerequisites.get("images_folder_path", state.get("images_folder_path", ""))
    browser_status = state.get("canva_browser_status", {})

    if prerequisites["all_ready"]:
        with st.expander("⚙️ Configuration", expanded=False):
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
        st.session_state.workflow_state = state

        st.subheader("🚀 Design Creation")
        if state.get("canva_status") == "creating":
            render_canva_progress_display(state.get("canva_progress", {}))

        if not config["images_folder"]:
            st.error("❌ No images folder. Set folder in Image Generation tab.")
        elif not Path(config["images_folder"]).exists():
            st.error(f"❌ Folder not found: `{config['images_folder']}`")
        else:
            can_create = prerequisites["all_ready"] and config["images_folder"] and browser_status.get("connected", False)
            if st.button("🚀 Start Design Creation", disabled=not can_create, key="start_canva_design_btn"):
                try:
                    state["canva_status"] = "creating"
                    st.session_state.workflow_state = state

                    def progress_callback(progress_update: dict):
                        state["canva_progress"] = progress_update
                        st.session_state.workflow_state = state

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
                        st.session_state.workflow_state = state
                    st.rerun()
                except Exception as e:
                    import traceback
                    st.error(f"Error: {str(e)}")
                    with st.expander("Error Details", expanded=False):
                        st.code(traceback.format_exc())
                    state["canva_status"] = "failed"
                    st.session_state.workflow_state = state

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
        st.info("💡 Complete: " + ", ".join(missing))
