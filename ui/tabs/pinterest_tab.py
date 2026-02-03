"""Pinterest Publishing tab."""

import streamlit as st
import threading
from pathlib import Path

from integrations.pinterest.browser_utils import check_browser_connection, launch_browser_with_debugging, get_browser_status
from workflows.pinterest.publisher import PinterestPublishingWorkflow
from ui.components.pinterest_components import (
    render_prerequisites_check,
    render_configuration_section,
    render_progress_display,
    render_results_summary,
    render_antivirus_check
)


def render_pinterest_tab(state: dict):
    """Render the Pinterest Publishing tab."""
    st.header("📌 Pinterest Publishing")
    
    # Run antivirus/system check first
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### System Health Check")
    with col2:
        if st.button("🔄 Refresh Check", key="run_system_check_btn", help="Re-run system check for missing files and antivirus interference"):
            st.rerun()
    
    # Always show the check
    antivirus_check = render_antivirus_check()
    
    # Show informational message (not blocking)
    file_check = antivirus_check["file_check"]
    playwright_check = antivirus_check["playwright_check"]
    
    # Only show error for truly critical issues (missing Python files)
    critical_playwright_issues = [
        issue for issue in playwright_check["issues"]
        if "importing" in issue.lower() or "not installed" in issue.lower()
    ]
    
    if not file_check["all_present"]:
        st.warning("⚠️ **Some files may be missing** - Check details above. You can still try publishing to see the actual error.")
    elif not playwright_check["installed"] or len(critical_playwright_issues) > 0:
        st.warning("⚠️ **Playwright issues detected** - Check details above. You can still try publishing to see the actual error.")
    else:
        st.success("✅ **System check passed!** You're ready to publish.")
    
    st.divider()
    
    # Initialize workflow
    if "pinterest_workflow" not in st.session_state:
        st.session_state.pinterest_workflow = PinterestPublishingWorkflow()
    
    workflow = st.session_state.pinterest_workflow
    
    # Initialize state fields if needed
    if "pinterest_status" not in state:
        state["pinterest_status"] = "pending"
    if "pinterest_progress" not in state:
        state["pinterest_progress"] = {}
    if "pinterest_results" not in state:
        state["pinterest_results"] = {}
    if "pinterest_browser_status" not in state:
        state["pinterest_browser_status"] = {}
    if "pinterest_board_name" not in state:
        state["pinterest_board_name"] = ""
    if "pinterest_folder_path" not in state:
        state["pinterest_folder_path"] = ""
    
    # Check browser connection
    if st.session_state.get("check_browser_clicked", False):
        st.session_state.check_browser_clicked = False
        browser_status = check_browser_connection()
        state["pinterest_browser_status"] = browser_status
        st.session_state.workflow_state = state
    
    # Auto-check browser on load
    if not state.get("pinterest_browser_status"):
        browser_status = check_browser_connection()
        state["pinterest_browser_status"] = browser_status
        st.session_state.workflow_state = state
    
    # Prerequisites check
    prerequisites = render_prerequisites_check(state)
    
    # Get image info from prerequisites
    images_folder_path = prerequisites.get("images_folder_path", state.get("images_folder_path", ""))
    image_count = prerequisites.get("image_count", 0)
    
    # Browser connection section
    st.divider()
    
    browser_status = state.get("pinterest_browser_status", {})
    if not browser_status.get("connected", False):
        st.warning("🌐 Browser Connection Required")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.info("""
            To publish pins, you need a browser running with remote debugging enabled.
            
            1. Click "Launch Browser" below
            2. Log into Pinterest in the opened browser
            3. Return here and click "Continue"
            """)
        
        with col2:
            if st.button("🚀 Launch Browser", key="launch_browser_btn"):
                with st.spinner("Launching browser..."):
                    launch_result = launch_browser_with_debugging()
                    
                    if launch_result.get("success", False):
                        st.success(launch_result["message"])
                        st.info("Please log into Pinterest in the opened browser, then click 'Continue' below.")
                        st.session_state["browser_launched"] = True
                    else:
                        st.error(launch_result["message"])
            
            if st.session_state.get("browser_launched", False):
                if st.button("✅ Continue", key="continue_after_browser"):
                    # Re-check connection
                    browser_status = check_browser_connection()
                    state["pinterest_browser_status"] = browser_status
                    st.session_state.workflow_state = state
                    st.session_state.browser_launched = False
                    st.rerun()
    else:
        st.success(f"✅ Browser connected on port {browser_status.get('port', 'N/A')}")
    
    st.divider()
    
    # Configuration section
    if prerequisites["all_ready"]:
        config = render_configuration_section(state)
        
        # Use images folder from prerequisites if available
        if not config["images_folder"] and images_folder_path:
            config["images_folder"] = images_folder_path
        
        # Show image count info
        if image_count > 0:
            expected_count = len(state.get("midjourney_prompts", []))
            if expected_count > 0 and image_count != expected_count:
                st.info(f"ℹ️ Publishing {image_count} images (expected {expected_count} from prompts). You can publish with available images.")
        
        # Update state with board name
        if config["board_name"]:
            state["pinterest_board_name"] = config["board_name"]
            st.session_state.workflow_state = state
        
        # Publishing section
        st.divider()
        st.subheader("🚀 Publishing")
        
        # Show current progress if publishing
        if state.get("pinterest_status") == "publishing":
            render_progress_display(state.get("pinterest_progress", {}))
        
        # Validate we have images folder
        if not config["images_folder"]:
            st.error("❌ No images folder specified. Please set the images folder in the Image Generation tab.")
        elif not Path(config["images_folder"]).exists():
            st.error(f"❌ Images folder not found: `{config['images_folder']}`")
        else:
            # Start publishing button
            can_publish = prerequisites["all_ready"] and config["board_name"] and browser_status.get("connected", False) and config["images_folder"]
            
            if st.button("🚀 Start Publishing", disabled=not can_publish, key="start_publishing_btn"):
                # Don't block - let the workflow run and log the actual error
                # The workflow logger will capture any real issues
                
                # Initialize workflow logger
                try:
                    from integrations.pinterest.workflow_logger import get_workflow_logger
                    workflow_logger = get_workflow_logger()
                    workflow_logger.log_action("start_publishing_button_clicked", {
                        "folder_path": config["images_folder"],
                        "board_name": config["board_name"]
                    })
                except Exception as e:
                    workflow_logger = None
                    st.warning(f"Could not initialize logger: {e}")
                
                # Prepare folder
                try:
                    with st.spinner("Preparing publishing folder..."):
                        if workflow_logger:
                            workflow_logger.log_action("preparing_folder", {
                                "images_folder": config["images_folder"]
                            })
                        
                        state["pinterest_status"] = "preparing"
                        st.session_state.workflow_state = state
                        
                        folder_path = workflow.prepare_publishing_folder(
                            design_state=state,
                            images_folder=config["images_folder"],
                        )
                        
                        if workflow_logger:
                            workflow_logger.log_action("folder_prepared", {
                                "folder_path": folder_path
                            })
                        
                        state["pinterest_folder_path"] = folder_path
                        state["pinterest_status"] = "publishing"
                        st.session_state.workflow_state = state
                    
                    # Progress callback
                    def progress_callback(progress_update: dict):
                        state["pinterest_progress"] = progress_update
                        st.session_state.workflow_state = state
                        if workflow_logger:
                            workflow_logger.log_action("progress_update", progress_update)
                    
                    # Publish
                    with st.spinner("Publishing pins..."):
                        if workflow_logger:
                            workflow_logger.log_action("starting_publish", {
                                "folder_path": folder_path,
                                "board_name": config["board_name"]
                            })
                        
                        results = workflow.publish_to_pinterest(
                            folder_path=folder_path,
                            board_name=config["board_name"],
                            progress_callback=progress_callback
                        )
                        
                        if workflow_logger:
                            workflow_logger.log_action("publish_completed", {
                                "success": results.get("success", False),
                                "results": results
                            })
                        
                        state["pinterest_results"] = results
                        if results.get("success", False):
                            state["pinterest_status"] = "completed"
                        else:
                            state["pinterest_status"] = "failed"
                        st.session_state.workflow_state = state
                    
                    st.rerun()
                    
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    st.error(f"Error: {str(e)}")
                    with st.expander("Error Details", expanded=False):
                        st.code(error_details)
                    
                    # Log error to workflow logger
                    try:
                        from integrations.pinterest.workflow_logger import get_workflow_logger
                        workflow_logger = get_workflow_logger()
                        workflow_logger.log_error(e, "pinterest_tab - Start Publishing")
                        workflow_logger.close()
                        log_file = workflow_logger.log_file
                        st.info(f"📝 Full error log saved to: `{log_file}`")
                    except:
                        pass
                    
                    state["pinterest_status"] = "failed"
                    st.session_state.workflow_state = state
            
            # Show results if completed
            if state.get("pinterest_status") in ["completed", "failed"]:
                st.divider()
                render_results_summary(state.get("pinterest_results", {}))
    else:
        # Show what's missing
        missing = []
        if not prerequisites["checks"]["design_generated"]:
            missing.append("Design package (generate in Design Generation tab)")
        if not prerequisites["checks"]["images_available"]:
            missing.append("Images (set folder in Image Generation tab)")
        if not prerequisites["checks"]["browser_connected"]:
            missing.append("Browser connection (click 'Check Browser' above)")
        
        st.info(f"💡 **Please complete prerequisites:**\n\n" + "\n".join(f"  • {item}" for item in missing))

