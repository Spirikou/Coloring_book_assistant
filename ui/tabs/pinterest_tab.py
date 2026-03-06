"""Pinterest Publishing tab."""

import streamlit as st
from pathlib import Path

from integrations.pinterest.browser_utils import check_browser_connection
from workflows.pinterest.publisher import PinterestPublishingWorkflow
from core.persistence import load_pinterest_config
from ui.components.pinterest_components import (
    render_pinterest_combined_checks,
    render_configuration_section,
    render_preview_section,
    render_progress_display,
    render_results_summary,
    render_session_management,
)


def render_pinterest_tab(state: dict):
    """Render the Pinterest Publishing tab."""
    st.header("Pinterest Publishing")

    if "pinterest_workflow" not in st.session_state:
        st.session_state.pinterest_workflow = PinterestPublishingWorkflow()
    workflow = st.session_state.pinterest_workflow

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

    if st.session_state.get("check_browser_clicked", False):
        st.session_state.check_browser_clicked = False
        browser_status = check_browser_connection()
        state["browser_status"] = browser_status
        st.session_state.workflow_state = state

    if st.session_state.get("refresh_browser_check_pinterest", False):
        st.session_state.refresh_browser_check_pinterest = False
        browser_status = check_browser_connection()
        state["browser_status"] = browser_status
        st.session_state.workflow_state = state

    if not state.get("browser_status"):
        browser_status = check_browser_connection()
        state["browser_status"] = browser_status
        st.session_state.workflow_state = state

    prerequisites = render_pinterest_combined_checks(state)
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
            st.session_state.workflow_state = state

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

            can_publish = (
                prerequisites["all_ready"]
                and config["board_name"]
                and browser_status.get("connected", False)
                and config["images_folder"]
                and len(preview.get("selected_images", [])) > 0
            )
            if st.button("Start Publishing", disabled=not can_publish, key="start_publishing_btn"):
                try:
                    from integrations.pinterest.workflow_logger import get_workflow_logger
                    workflow_logger = get_workflow_logger()
                except Exception:
                    workflow_logger = None

                try:
                    with st.spinner("Preparing..."):
                        state["pinterest_status"] = "preparing"
                        state["images_folder_path"] = config["images_folder"]
                        st.session_state.workflow_state = state
                        # Use preview selection (user may have removed images)
                        selected = preview.get("selected_images") or []
                        design_state = {**state, "title": preview["title"], "description": preview["description"]}
                        folder = config["images_folder"]
                        from utils.folder_monitor import get_images_in_folder
                        all_in_folder = get_images_in_folder(folder)
                        no_exclusions = len(selected) == 0 or len(selected) == len(all_in_folder)
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
                        st.session_state.workflow_state = state

                    progress_placeholder = st.empty()

                    def progress_callback(progress_update: dict):
                        state["pinterest_progress"] = progress_update
                        st.session_state.workflow_state = state
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
                        st.session_state.workflow_state = state
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
                    st.session_state.workflow_state = state

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
                    st.session_state.workflow_state = state
                    progress_placeholder = st.empty()

                    def rerun_progress_callback(progress_update: dict):
                        state["pinterest_progress"] = progress_update
                        st.session_state.workflow_state = state
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
                            st.session_state.workflow_state = state
                        st.rerun()
                    except Exception as e:
                        import traceback
                        st.error(f"Error: {str(e)}")
                        with st.expander("Error Details", expanded=False):
                            st.code(traceback.format_exc())
                        state["pinterest_status"] = "failed"
                        state["pinterest_rerun_requested"] = False
                        st.session_state.workflow_state = state
                        st.rerun()
                else:
                    if not board_name:
                        st.error("Board name required for re-run. Set it in Configuration above.")
                    else:
                        st.error("Browser not connected. Check browser connection above.")
                    state["pinterest_rerun_requested"] = False
                    st.session_state.workflow_state = state

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
