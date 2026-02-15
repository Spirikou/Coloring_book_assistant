"""Reusable UI components for Canva tab."""

import streamlit as st
from integrations.pinterest.antivirus_check import run_full_check
from ui.components.shared_checks import render_combined_checks, BROWSER_STATUS_KEY


def render_canva_combined_checks(state: dict) -> dict:
    """Render combined system + prerequisites checks in one expander."""
    return render_combined_checks(state, "canva")


def render_canva_prerequisites_check(state: dict) -> dict:
    """
    Render prerequisites checklist (same as Pinterest - design, images, browser).
    Uses same images_folder_path as Pinterest.
    """
    st.subheader("📋 Prerequisites Checklist")
    
    has_title = bool(state.get("title"))
    has_description = bool(state.get("description"))
    design_generated = has_title and has_description
    
    images_folder_path = state.get("images_folder_path", "")
    uploaded_images = state.get("uploaded_images", [])
    images_ready = state.get("images_ready", False)
    
    from utils.folder_monitor import get_images_in_folder
    if images_folder_path:
        folder_images = get_images_in_folder(images_folder_path)
        has_images = len(folder_images) > 0
        image_count = len(folder_images)
    else:
        has_images = False
        image_count = 0
    
    browser_status = state.get(BROWSER_STATUS_KEY, {})
    browser_connected = browser_status.get("connected", False)
    
    checks = {
        "design_generated": design_generated,
        "images_available": has_images or images_ready,
        "browser_connected": browser_connected
    }
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if design_generated:
            st.success("✅ **Design Package**\n\nTitle and description generated")
        else:
            st.error("❌ **Design Package**\n\nMissing: " + ("title" if not has_title else "") + (", description" if not has_description else ""))
    
    with col2:
        if has_images:
            expected_count = len(state.get("midjourney_prompts", []))
            if expected_count > 0:
                st.success(f"✅ **Images Available**\n\n{image_count} images found" + (f" (expected {expected_count})" if expected_count != image_count else ""))
            else:
                st.success(f"✅ **Images Available**\n\n{image_count} images found")
        elif images_ready:
            st.success(f"✅ **Images Ready**\n\n{len(uploaded_images)} images marked as ready")
        else:
            if images_folder_path:
                st.warning(f"⚠️ **Images**\n\nNo images found in folder:\n`{images_folder_path}`")
            else:
                st.warning("⚠️ **Images**\n\nNo images folder set. Go to Image Generation tab first.")
    
    with col3:
        if browser_connected:
            port = browser_status.get("port", "N/A")
            st.success(f"✅ **Browser Connected**\n\nPort: {port}")
        else:
            st.warning("⚠️ **Browser**\n\nNot connected. Click 'Check Browser' below.")
    
    if st.button("🔍 Check Browser Connection", key="check_browser_canva_btn", use_container_width=True):
        st.session_state["check_browser_canva_clicked"] = True
        st.rerun()
    
    all_ready = checks["design_generated"] and checks["images_available"]
    
    return {
        "all_ready": all_ready,
        "checks": checks,
        "image_count": image_count if has_images else 0,
        "images_folder_path": images_folder_path
    }


def render_canva_configuration_section(state: dict) -> dict:
    """Render configuration - images folder from state (read-only, same as Pinterest), page size, layout options."""
    st.subheader("⚙️ Configuration")
    
    images_folder = state.get("images_folder_path", "")
    if images_folder:
        from utils.folder_monitor import get_images_in_folder
        folder_images = get_images_in_folder(images_folder)
        image_count = len(folder_images)
        
        if image_count > 0:
            st.success(f"📁 **Images Folder (same as Pinterest):** `{images_folder}`\n\n✅ {image_count} images found")
        else:
            st.warning(f"📁 **Images Folder:** `{images_folder}`\n\n⚠️ No images found in this folder")
    else:
        st.warning("⚠️ No images folder set. Please set the folder path in the Image Generation tab first.")
    
    st.caption("Uses the same images folder as Pinterest Publishing - no separate folder selection.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        page_size = st.text_input(
            "Page Size (inches)",
            value=state.get("canva_page_size", "8.625x8.75"),
            help="Format: WIDTHxHEIGHT e.g. 8.625x8.75 for coloring book",
            key="canva_page_size_input",
            placeholder="8.625x8.75"
        )
        margin_percent = st.number_input(
            "Margin %",
            min_value=0.0,
            max_value=50.0,
            value=float(state.get("canva_margin_percent", 8.0)),
            step=0.5,
            key="canva_margin_input"
        )
    
    with col2:
        outline_height_percent = st.number_input(
            "Outline Height %",
            min_value=0.0,
            max_value=50.0,
            value=float(state.get("canva_outline_height_percent", 6.0)),
            step=0.5,
            key="canva_outline_input"
        )
        blank_between = st.checkbox(
            "Add blank page between images",
            value=state.get("canva_blank_between", True),
            key="canva_blank_between_input"
        )
    
    return {
        "images_folder": images_folder,
        "page_size": page_size or "8.625x8.75",
        "margin_percent": margin_percent,
        "outline_height_percent": outline_height_percent,
        "blank_between": blank_between,
    }


def render_canva_progress_display(progress: dict):
    """Render real-time progress display."""
    if not progress:
        return
    
    step = progress.get("step", "")
    current = progress.get("current", 0)
    total = progress.get("total", 0)
    status = progress.get("status", "")
    message = progress.get("message", "")
    
    st.subheader("📊 Design Progress")
    
    if total > 0:
        progress_pct = current / total
        st.progress(progress_pct)
        st.caption(f"{message} ({current}/{total})")
    else:
        st.info(message)
    
    if status == "completed":
        st.success("✅ Design creation completed!")
    elif status == "failed":
        st.error("❌ Design creation failed")
    elif status == "in_progress":
        st.info("🔄 Creating design...")


def render_canva_results_summary(results: dict):
    """Render design results summary."""
    if not results:
        return
    
    st.subheader("📈 Results Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Images", results.get("total_images", 0))
    
    with col2:
        st.metric("Successful", results.get("successful", 0), delta_color="normal")
    
    with col3:
        st.metric("Failed", results.get("failed", 0), delta_color="inverse")
    
    with col4:
        st.metric("Total Pages", results.get("total_pages", 0))
    
    message = results.get("message", "")
    if results.get("success", False):
        st.success(message)
        
        design_url = results.get("design_url", "")
        if design_url:
            st.markdown("**Design URL:**")
            st.link_button("🔗 Open in Canva", design_url, type="primary")
    else:
        st.error(message)
    
    errors = results.get("errors", [])
    if errors:
        with st.expander("⚠️ Errors", expanded=True):
            for error in errors:
                st.error(error)


def render_canva_antivirus_check() -> dict:
    """Render antivirus/system check - reuses Pinterest antivirus check (same Playwright, browser)."""
    st.subheader("🛡️ System Check")
    
    check_results = run_full_check()
    warning = check_results["bitdefender_warning"]
    
    with st.expander("⚠️ Bitdefender Antivirus Warning", expanded=check_results["has_issues"]):
        st.warning(f"**{warning['title']}**")
        st.info(warning["message"])
        
        st.markdown("**Recommendations:**")
        for i, rec in enumerate(warning["recommendations"], 1):
            st.markdown(f"{i}. {rec}")
        
        st.markdown("**Paths to add to Bitdefender exclusions:**")
        for path in warning["exclusion_paths"]:
            st.code(path, language=None)
    
    file_check = check_results["file_check"]
    if not file_check["all_present"]:
        st.error(f"❌ **Missing Files Detected** ({file_check['total_missing']} of {file_check['total_checked']} files)")
        for file_name in file_check["missing_files"]:
            file_info = file_check["file_status"].get(file_name, {})
            st.error(f"  - `{file_name}` (expected at: `{file_info.get('path', 'unknown')}`)")
        st.warning("**Action Required:** Check Bitdefender's quarantine and restore deleted files.")
    else:
        st.success(f"✅ **All Critical Files Present** ({file_check['total_checked']} files checked)")
    
    playwright_check = check_results["playwright_check"]
    if not playwright_check["installed"]:
        st.error("❌ **Playwright Not Installed**")
        st.info("Run: `uv sync` or `pip install playwright`")
    elif len(playwright_check["issues"]) > 0:
        critical_issues = [issue for issue in playwright_check["issues"] 
                          if "importing" in issue.lower() or "not installed" in issue.lower()]
        if critical_issues:
            st.error("❌ **Playwright Critical Issues**")
            for issue in critical_issues:
                st.error(f"  - {issue}")
            st.info("**Fix:** Run `uv sync` or `pip install playwright`")
        else:
            st.success("✅ **Playwright Installed**")
    else:
        st.success("✅ **Playwright Installed**")
        st.caption("ℹ️ Using existing browser connection (same port 9222 as Pinterest)")
    
    if check_results["recommendations"]:
        st.markdown("**📋 Recommendations:**")
        for rec in check_results["recommendations"]:
            st.markdown(f"  {rec}")
    
    return check_results
