"""Reusable UI components for Pinterest tab."""

import streamlit as st
from pathlib import Path
from integrations.pinterest.antivirus_check import run_full_check, get_bitdefender_warning
from ui.components.shared_checks import render_combined_checks, BROWSER_STATUS_KEY
from core.persistence import (
    save_pinterest_config,
    save_preview_to_images_folder,
    load_pinterest_config,
    list_publish_sessions,
    load_session_config,
    delete_session_image,
    delete_publish_session,
    IMAGE_EXTENSIONS,
)


def render_pinterest_combined_checks(state: dict) -> dict:
    """Render combined system + prerequisites checks in one expander."""
    return render_combined_checks(state, "pinterest")


def render_prerequisites_check(state: dict) -> dict:
    """
    Render prerequisites checklist with clear status indicators.
    
    Returns:
        dict with check results
    """
    st.subheader("Prerequisites Checklist")
    
    # Check design package
    has_title = bool(state.get("title"))
    has_description = bool(state.get("description"))
    design_generated = has_title and has_description
    
    # Check images - look for folder path and images in that folder
    images_folder_path = state.get("images_folder_path", "")
    uploaded_images = state.get("uploaded_images", [])
    images_ready = state.get("images_ready", False)
    
    # Check if folder exists and has images
    from utils.folder_monitor import get_images_in_folder
    if images_folder_path:
        folder_images = get_images_in_folder(images_folder_path)
        has_images = len(folder_images) > 0
        image_count = len(folder_images)
    else:
        has_images = False
        image_count = 0
    
    # Browser check
    browser_status = state.get(BROWSER_STATUS_KEY, {})
    browser_connected = browser_status.get("connected", False)
    
    checks = {
        "design_generated": design_generated,
        "images_available": has_images or images_ready,
        "browser_connected": browser_connected
    }
    
    # Render status cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Design package status card
        if design_generated:
            st.success("✓ **Design Package**\n\nTitle and description generated")
        else:
            st.error("✗ **Design Package**\n\nMissing: " + ("title" if not has_title else "") + (", description" if not has_description else ""))
    
    with col2:
        # Images status card
        if has_images:
            expected_count = len(state.get("midjourney_prompts", []))
            if expected_count > 0:
                st.success(f"✓ **Images Available**\n\n{image_count} images found" + (f" (expected {expected_count})" if expected_count != image_count else ""))
            else:
                st.success(f"✓ **Images Available**\n\n{image_count} images found")
        elif images_ready:
            st.success(f"✓ **Images Ready**\n\n{len(uploaded_images)} images marked as ready")
        else:
            if images_folder_path:
                st.warning(f"○ **Images**\n\nNo images found in folder:\n`{images_folder_path}`")
            else:
                st.warning("○ **Images**\n\nNo images folder set. Go to Image Generation tab first.")
    
    with col3:
        # Browser status card
        if browser_connected:
            port = browser_status.get("port", "N/A")
            st.success(f"✓ **Browser Connected**\n\nPort: {port}")
        else:
            st.warning("○ **Browser**\n\nNot connected. Click 'Check Browser' below.")
    
    # Browser check button
    if st.button("Check Browser Connection", key="check_browser_btn", use_container_width=True):
        st.session_state["check_browser_clicked"] = True
        st.rerun()
    
    # Determine if ready (design and images are required, browser can be set up later)
    all_ready = checks["design_generated"] and checks["images_available"]
    
    return {
        "all_ready": all_ready,
        "checks": checks,
        "image_count": image_count if has_images else 0,
        "images_folder_path": images_folder_path
    }


def render_configuration_section(state: dict, effective_images_folder: str = "") -> dict:
    """Render configuration inputs.
    effective_images_folder: Fallback path when state has none (e.g. from GENERATED_IMAGES_DIR).
    """
    st.subheader("Configuration")

    saved_config = load_pinterest_config()
    default_board = state.get("pinterest_board_name") or (saved_config.get("board_name", "") if saved_config else "")
    default_folder = state.get("images_folder_path") or effective_images_folder or (
        saved_config.get("images_folder_path", "") if saved_config else ""
    )

    board_name = st.text_input(
        "Pinterest Board Name",
        value=default_board,
        help="Enter the exact name of your Pinterest board (must match exactly)",
        key="pinterest_board_input",
        placeholder="e.g., Coloring Books"
    )

    images_folder = st.text_input(
        "Images Folder",
        value=default_folder,
        help="Path to folder containing images to publish.",
        key="pinterest_images_folder_input",
        placeholder="e.g., C:/path/to/generated_images"
    )
    images_folder = images_folder.strip() if images_folder else ""

    if images_folder:
        from utils.folder_monitor import get_images_in_folder
        folder_images = get_images_in_folder(images_folder)
        image_count = len(folder_images)
        if image_count > 0:
            st.success(f"**Images Folder:** `{images_folder}`\n\n✓ {image_count} images found")
        else:
            st.warning(f"**Images Folder:** `{images_folder}`\n\n○ No images found in this folder")
    else:
        st.warning("Enter the path to the folder containing your images.")

    if st.button("Save Configuration", key="pinterest_save_config_btn", help="Save board name and images folder for next time"):
        if save_pinterest_config(board_name, images_folder):
            st.success("Configuration saved.")
            st.rerun()
        else:
            st.error("Failed to save configuration.")

    return {
        "board_name": board_name,
        "images_folder": images_folder
    }


def render_preview_section(state: dict, images_folder: str) -> dict:
    """
    Render preview before publishing: editable title, description, and image grid.
    Users can remove images from the publish batch before starting.

    Returns:
        dict with title, description, selected_images to use when publishing
    """
    from utils.folder_monitor import get_images_in_folder

    st.subheader("Preview before publishing")
    st.caption("Edit the title and description, review images, and remove any you don't want to publish.")

    title = st.text_input(
        "Pin title",
        value=state.get("title", ""),
        key="pinterest_preview_title",
        help="Title for all pins (max 100 chars on Pinterest)",
        max_chars=100,
    )

    description = st.text_area(
        "Pin description",
        value=state.get("description", ""),
        key="pinterest_preview_description",
        help="Description for all pins (max 600 chars recommended)",
        height=150,
    )

    # Save modifications button - persists title/description to book_config.json in images folder
    if images_folder and Path(images_folder).exists():
        if st.button(
            "Save modifications",
            key="pinterest_save_modifications_btn",
            help="Save title and description to the images folder before publishing. Changes persist across sessions.",
        ):
            if save_preview_to_images_folder(
                images_folder,
                title,
                description,
                seo_keywords=state.get("seo_keywords"),
            ):
                state["title"] = title
                state["description"] = description
                if "workflow_state" in st.session_state:
                    st.session_state.workflow_state = state
                st.success("Modifications saved to the images folder.")
                st.rerun()
            else:
                st.error("Failed to save modifications.")

    # Excluded images (removed from batch before publishing)
    excluded = set(state.get("pinterest_excluded_images", []))
    # Clear excluded when images folder changes
    folder_key = "pinterest_preview_folder"
    if state.get(folder_key) != images_folder:
        excluded = set()
        state["pinterest_excluded_images"] = []
        state[folder_key] = images_folder
        if "workflow_state" in st.session_state:
            st.session_state.workflow_state = state

    # Image grid
    if images_folder and Path(images_folder).exists():
        all_paths = get_images_in_folder(images_folder)
        all_paths.sort(key=lambda p: Path(p).name)
        to_publish = [p for p in all_paths if p not in excluded]
        removed = [p for p in all_paths if p in excluded]

        if to_publish:
            st.markdown(f"**Images to publish** ({len(to_publish)} images)")
            cols = st.columns(min(4, len(to_publish)) or 1)
            for i, img_path in enumerate(to_publish):
                col = cols[i % len(cols)]
                with col:
                    try:
                        st.image(str(img_path), caption=Path(img_path).name, use_container_width=True)
                    except Exception:
                        st.caption(Path(img_path).name)
                    if st.button("Remove", key=f"preview_remove_{Path(img_path).name}".replace(".", "_"), type="secondary"):
                        state.setdefault("pinterest_excluded_images", []).append(img_path)
                        st.session_state.workflow_state = state
                        st.rerun()

        if removed:
            with st.expander(f"Removed ({len(removed)} images — click to add back)", expanded=False):
                cols = st.columns(min(4, len(removed)) or 1)
                for i, img_path in enumerate(removed):
                    col = cols[i % len(cols)]
                    with col:
                        try:
                            st.image(str(img_path), caption=Path(img_path).name, use_container_width=True)
                        except Exception:
                            st.caption(Path(img_path).name)
                        if st.button("Add back", key=f"preview_addback_{Path(img_path).name}".replace(".", "_")):
                            state["pinterest_excluded_images"] = [p for p in state.get("pinterest_excluded_images", []) if p != img_path]
                            st.session_state.workflow_state = state
                            st.rerun()

        if not to_publish and not all_paths:
            st.warning("No images found in the selected folder.")
        elif not to_publish:
            st.warning("All images removed. Add some back or select a different folder.")
    else:
        to_publish = []
        st.warning("Select an images folder in Configuration to preview.")

    return {
        "title": title,
        "description": description,
        "selected_images": to_publish,
    }


def render_progress_display(progress: dict):
    """Render real-time progress display."""
    if not progress:
        return
    
    step = progress.get("step", "")
    current = progress.get("current", 0)
    total = progress.get("total", 0)
    status = progress.get("status", "")
    message = progress.get("message", "")
    
    st.subheader("Publishing Progress")
    
    if total > 0:
        progress_pct = current / total
        st.progress(progress_pct)
        st.caption(f"{message} ({current}/{total})")
    else:
        st.info(message)
    
    # Status indicator
    if status == "completed":
        st.success("✓ Publishing completed!")
    elif status == "failed":
        st.error("✗ Publishing failed")
    elif status == "in_progress":
        st.info("Publishing in progress...")


def render_results_summary(results: dict):
    """Render publishing results summary."""
    if not results:
        return
    
    st.subheader("Results Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Images", results.get("total_images", 0))
    
    with col2:
        st.metric("Published", results.get("published", 0), delta_color="normal")
    
    with col3:
        st.metric("Already Published", results.get("already_published", 0))
    
    with col4:
        st.metric("Failed", results.get("failed", 0), delta_color="inverse")
    
    # Message
    message = results.get("message", "")
    if results.get("success", False):
        st.success(message)
    else:
        st.error(message)
    
    # Errors if any
    errors = results.get("errors", [])
    if errors:
        with st.expander("Errors", expanded=True):
            for error in errors:
                st.error(error)


def render_session_management(state: dict) -> None:
    """Render the Publishing Sessions section: list sessions, selector, load view."""
    st.subheader("Publishing Sessions")
    sessions = list_publish_sessions()
    if not sessions:
        st.info("No publish sessions yet. Start publishing to create sessions.")
        return

    # Session selector
    options = [
        f"{s['timestamp']} — {s['title'][:40]}{'...' if len(s['title']) > 40 else ''} ({s['published_count']}/{s['image_count']} pins)"
        for s in sessions
    ]
    selected_idx = st.selectbox(
        "Select session",
        range(len(sessions)),
        format_func=lambda i: options[i],
        key="pinterest_session_select",
    )
    if selected_idx is not None and 0 <= selected_idx < len(sessions):
        selected = sessions[selected_idx]
        state["pinterest_selected_session"] = selected["folder_path"]
        st.session_state.workflow_state = state
        render_session_detail(selected, state)


def render_session_detail(session: dict, state: dict) -> None:
    """Render session detail: title, description, image grid with Delete, Re-run button."""
    folder_path = session["folder_path"]
    config = load_session_config(folder_path) or {}
    title = config.get("title", "Untitled")
    description = config.get("description", "")

    st.markdown("---")
    st.markdown(f"**Title:** {title}")
    with st.expander("Description", expanded=False):
        st.text(description[:500] + ("..." if len(description) > 500 else ""))

    # Image grid
    folder = Path(folder_path)
    image_files = [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]
    image_files.sort(key=lambda p: p.name)

    if not image_files:
        st.warning("No images in this session.")
    else:
        st.markdown("**Images**")
        cols = st.columns(min(4, len(image_files)) or 1)
        for i, img_path in enumerate(image_files):
            col = cols[i % len(cols)]
            with col:
                try:
                    st.image(str(img_path), caption=img_path.name, use_container_width=True)
                except Exception:
                    st.caption(img_path.name)
                folder_name = Path(folder_path).name
                if st.button("Delete", key=f"del_{folder_name}_{img_path.name}".replace(".", "_"), type="secondary"):
                    if delete_session_image(folder_path, img_path.name):
                        st.success(f"Deleted {img_path.name}")
                        st.rerun()
                    else:
                        st.error(f"Failed to delete {img_path.name}")

    # Re-run and Delete session buttons
    st.markdown("---")
    col_rerun, col_del, _ = st.columns([1, 1, 2])
    with col_rerun:
        if st.button("Re-run Publishing", key="rerun_publishing_btn"):
            state["pinterest_rerun_folder"] = folder_path
            state["pinterest_rerun_requested"] = True
            st.session_state.workflow_state = state
            st.rerun()
    with col_del:
        if state.get("pinterest_delete_confirm") == folder_path:
            st.warning("Delete this session and all its images?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Confirm delete", key="confirm_del_session", type="primary"):
                    if delete_publish_session(folder_path):
                        state.pop("pinterest_delete_confirm", None)
                        if "pinterest_selected_session" in state:
                            del state["pinterest_selected_session"]
                        st.session_state.workflow_state = state
                        st.success("Session deleted.")
                        st.rerun()
                    else:
                        st.error("Failed to delete session.")
            with c2:
                if st.button("Cancel", key="cancel_del_session"):
                    state.pop("pinterest_delete_confirm", None)
                    st.session_state.workflow_state = state
                    st.rerun()
        else:
            if st.button("Delete session", key=f"del_session_{Path(folder_path).name}".replace(".", "_"), type="secondary"):
                state["pinterest_delete_confirm"] = folder_path
                st.session_state.workflow_state = state
                st.rerun()


def render_antivirus_check() -> dict:
    """
    Render antivirus interference check (Bitdefender warning and file checks).
    
    Returns:
        dict with check results
    """
    st.subheader("System Check")
    
    # Run checks
    check_results = run_full_check()
    
    # Show Bitdefender warning
    warning = check_results["bitdefender_warning"]
    
    with st.expander("Bitdefender Antivirus Warning", expanded=check_results["has_issues"]):
        st.warning(f"**{warning['title']}**")
        st.info(warning["message"])
        
        st.markdown("**Recommendations:**")
        for i, rec in enumerate(warning["recommendations"], 1):
            st.markdown(f"{i}. {rec}")
        
        st.markdown("**Paths to add to Bitdefender exclusions:**")
        for path in warning["exclusion_paths"]:
            st.code(path, language=None)
    
    # Show file check results
    file_check = check_results["file_check"]
    if not file_check["all_present"]:
        st.error(f"✗ **Missing Files Detected** ({file_check['total_missing']} of {file_check['total_checked']} files)")
        
        st.markdown("**Missing files:**")
        for file_name in file_check["missing_files"]:
            file_info = file_check["file_status"].get(file_name, {})
            st.error(f"  - `{file_name}` (expected at: `{file_info.get('path', 'unknown')}`)")
        
        st.warning("**Action Required:** Check Bitdefender's quarantine and restore deleted files, or reinstall the project.")
    else:
        st.success(f"✓ **All Critical Files Present** ({file_check['total_checked']} files checked)")
    
    # Show Playwright check
    playwright_check = check_results["playwright_check"]
    if not playwright_check["installed"]:
        st.error("✗ **Playwright Not Installed**")
        st.info("Run: `uv sync` or `pip install playwright`")
    elif len(playwright_check["issues"]) > 0:
        # Separate critical vs informational issues
        critical_issues = [issue for issue in playwright_check["issues"] 
                          if "importing" in issue.lower() or "not installed" in issue.lower()]
        info_issues = [issue for issue in playwright_check["issues"] if issue not in critical_issues]
        
        if critical_issues:
            st.error("✗ **Playwright Critical Issues**")
            for issue in critical_issues:
                st.error(f"  - {issue}")
            st.info("**Fix:** Run `uv sync` or `pip install playwright`")
        elif info_issues:
            st.info("**Playwright Note**")
            for issue in info_issues:
                st.info(f"  - {issue}")
            st.caption("This is informational - browser automation will use your existing browser (connect_existing=True)")
        else:
            st.success("✓ **Playwright Installed**")
    else:
        st.success("✓ **Playwright Installed**")
        st.caption("Using existing browser connection (browser binaries not required)")
    
    # Show recommendations
    if check_results["recommendations"]:
        st.markdown("**Recommendations:**")
        for rec in check_results["recommendations"]:
            st.markdown(f"  {rec}")
    
    return check_results
