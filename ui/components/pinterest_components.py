"""Reusable UI components for Pinterest tab."""

import streamlit as st
from integrations.pinterest.antivirus_check import run_full_check, get_bitdefender_warning
from ui.components.shared_checks import render_combined_checks, BROWSER_STATUS_KEY


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


def render_configuration_section(state: dict) -> dict:
    """Render configuration inputs."""
    st.subheader("Configuration")
    
    board_name = st.text_input(
        "Pinterest Board Name",
        value=state.get("pinterest_board_name", ""),
        help="Enter the exact name of your Pinterest board (must match exactly)",
        key="pinterest_board_input",
        placeholder="e.g., Coloring Books"
    )
    
    images_folder = state.get("images_folder_path", "")
    if images_folder:
        from utils.folder_monitor import get_images_in_folder
        folder_images = get_images_in_folder(images_folder)
        image_count = len(folder_images)
        
        if image_count > 0:
            st.success(f"**Images Folder:** `{images_folder}`\n\n✓ {image_count} images found")
        else:
            st.warning(f"**Images Folder:** `{images_folder}`\n\n○ No images found in this folder")
    else:
        st.warning("No images folder set. Please set the folder path in the Image Generation tab first.")
    
    return {
        "board_name": board_name,
        "images_folder": images_folder
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
