"""Shared system and prerequisites check components for Canva and Pinterest tabs."""

import streamlit as st
from integrations.pinterest.antivirus_check import run_full_check
from integrations.pinterest.browser_utils import check_browser_connection, launch_browser_with_debugging


def _render_checks_summary(check_results: dict, prerq: dict) -> None:
    """Render a concise summary of all checks completed."""
    file_check = check_results["file_check"]
    playwright_check = check_results["playwright_check"]
    checks = prerq["checks"]
    browser_status = prerq["browser_status"]

    st.markdown("**Checks completed**")
    summary_items = []
    summary_items.append(f"• **Files:** {file_check['total_checked']} checked, {file_check['total_checked'] - file_check['total_missing']} present")
    if playwright_check["installed"]:
        summary_items.append("• **Playwright:** Python package OK, sync_api imported")
    else:
        summary_items.append("• **Playwright:** ❌ Not installed or import failed")
    if checks["browser_connected"]:
        port = browser_status.get("port", "N/A")
        summary_items.append(f"• **Browser:** ✅ Connected on port {port}")
    else:
        summary_items.append("• **Browser:** ⚠️ Not connected (port 9222)")
    st.caption("\n".join(summary_items))


def _render_system_check_content(check_results: dict) -> None:
    """Render system check content (Bitdefender, files, Playwright) with detailed info."""
    file_check = check_results["file_check"]
    playwright_check = check_results["playwright_check"]
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

    st.markdown("**File check**")
    if not file_check["all_present"]:
        st.error(f"❌ Missing {file_check['total_missing']} of {file_check['total_checked']} files")
        for file_name in file_check["missing_files"]:
            file_info = file_check["file_status"].get(file_name, {})
            path = file_info.get("path", "unknown")
            st.error(f"  - `{file_name}` (expected: `{path}`)")
        st.warning("Check Bitdefender quarantine and restore deleted files.")
    else:
        st.success(f"✅ All {file_check['total_checked']} critical files present")
        with st.expander("Files checked (paths)", expanded=False):
            for name, info in file_check["file_status"].items():
                status = "✅" if info.get("exists") else "❌"
                st.text(f"  {status} {name}: {info.get('path', '')}")

    st.markdown("**Playwright**")
    if not playwright_check["installed"]:
        st.error("❌ Playwright not installed")
        st.info("Run: `uv sync` or `pip install playwright`")
        st.caption("Checks: Python package import, sync_api module")
    else:
        critical_issues = [
            i for i in playwright_check["issues"]
            if "importing" in i.lower() or "not installed" in i.lower()
        ]
        if critical_issues:
            st.error("❌ Playwright issues")
            for issue in critical_issues:
                st.error(f"  - {issue}")
            st.info("**Fix:** Run `uv sync` or `pip install playwright`")
        else:
            st.success("✅ Playwright installed (sync_api imported)")
            if playwright_check.get("browsers_available"):
                st.caption(f"  Checked: {', '.join(playwright_check['browsers_available'])} — browser binaries optional (connects to existing browser)")

    if check_results.get("recommendations"):
        st.markdown("**Recommendations**")
        for rec in check_results["recommendations"]:
            st.markdown(f"  {rec}")


def _get_prerequisites_state(state: dict, tab_name: str) -> dict:
    """Get prerequisites state for canva or pinterest tab."""
    browser_key = "canva_browser_status" if tab_name == "canva" else "pinterest_browser_status"
    check_btn_key = "check_browser_canva_clicked" if tab_name == "canva" else "check_browser_clicked"

    has_title = bool(state.get("title"))
    has_description = bool(state.get("description"))
    design_generated = has_title and has_description

    images_folder_path = state.get("images_folder_path", "")
    selected_images = state.get("selected_images", [])
    from utils.folder_monitor import get_images_in_folder
    if images_folder_path:
        folder_images = get_images_in_folder(images_folder_path)
        has_images = len(folder_images) > 0
        image_count = len(folder_images)
    else:
        has_images = False
        image_count = 0

    # When selected_images is set, use that as effective image set
    if selected_images:
        has_images = True
        image_count = len(selected_images)

    browser_status = state.get(browser_key, {})
    browser_connected = browser_status.get("connected", False)

    checks = {
        "design_generated": design_generated,
        "images_available": has_images,
        "browser_connected": browser_connected
    }
    all_ready = checks["design_generated"] and checks["images_available"]

    session_state_key = "check_browser_canva_clicked" if tab_name == "canva" else "check_browser_clicked"
    button_key = "check_browser_canva_btn" if tab_name == "canva" else "check_browser_btn"

    return {
        "checks": checks,
        "all_ready": all_ready,
        "image_count": image_count,
        "images_folder_path": images_folder_path,
        "browser_status": browser_status,
        "session_state_key": session_state_key,
        "button_key": button_key,
    }


def _render_prerequisites_content(state: dict, tab_name: str, prerq: dict) -> None:
    """Render prerequisites content (design, images, browser) including browser status and actions."""
    checks = prerq["checks"]
    session_state_key = prerq["session_state_key"]
    button_key = prerq["button_key"]
    browser_status = prerq["browser_status"]
    launch_key = f"launch_browser_{tab_name}_btn"
    continue_key = f"continue_after_browser_{tab_name}"

    st.markdown("**Prerequisites**")
    col1, col2, col3 = st.columns(3)
    with col1:
        if checks["design_generated"]:
            st.success("✅ Design Package")
        else:
            st.error("❌ Design Package")
    with col2:
        if checks["images_available"]:
            st.success(f"✅ Images ({prerq['image_count']})")
        else:
            st.warning("⚠️ Images")
    with col3:
        if checks["browser_connected"]:
            port = browser_status.get("port", "N/A")
            st.success(f"✅ Browser (port {port})")
        else:
            st.warning("⚠️ Browser")

    st.markdown("**Browser connection**")
    if checks["browser_connected"]:
        port = browser_status.get("port", "N/A")
        st.success(f"✅ Browser connected on port {port}")
        st.caption("Check: Remote debugging port active. Start browser with: `--remote-debugging-port=9222`")
    else:
        st.warning("Browser not connected. Launch browser with remote debugging, then log in.")
        st.caption("Check: No browser detected on port 9222. Use Launch Browser or start manually with remote debugging.")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔍 Check Browser", key=button_key, use_container_width=True):
                st.session_state[session_state_key] = True
                st.rerun()
            if st.button("🚀 Launch Browser", key=launch_key, use_container_width=True):
                with st.spinner("Launching..."):
                    result = launch_browser_with_debugging()
                    if result.get("success"):
                        st.success(result["message"])
                        st.session_state[f"browser_launched_{tab_name}"] = True
                        st.rerun()
                    else:
                        st.error(result["message"])
        with col_b:
            if st.session_state.get(f"browser_launched_{tab_name}", False):
                if st.button("✅ Continue", key=f"continue_{tab_name}_btn", use_container_width=True):
                    bs = check_browser_connection()
                    state_key = "canva_browser_status" if tab_name == "canva" else "pinterest_browser_status"
                    state[state_key] = bs
                    st.session_state.workflow_state = state
                    st.session_state[f"browser_launched_{tab_name}"] = False
                    st.rerun()


def render_combined_checks(state: dict, tab_name: str) -> dict:
    """
    Render system + prerequisites in one collapsible expander.
    tab_name: "canva" or "pinterest"
    Returns dict with check_results, all_ready, checks, images_folder_path, image_count
    """
    check_results = run_full_check()
    prerq = _get_prerequisites_state(state, tab_name)

    # Count issues for header
    file_check = check_results["file_check"]
    playwright_check = check_results["playwright_check"]
    critical_playwright = [
        i for i in playwright_check["issues"]
        if "importing" in i.lower() or "not installed" in i.lower()
    ]
    issue_count = (
        (0 if file_check["all_present"] else 1) +
        (0 if playwright_check["installed"] and not critical_playwright else 1) +
        sum(1 for k, v in prerq["checks"].items() if not v and k != "browser_connected")
    )

    # Status line + Refresh
    col1, col2 = st.columns([4, 1])
    with col1:
        if issue_count == 0 and prerq["all_ready"]:
            st.success("✅ Ready")
        elif issue_count > 0:
            st.warning(f"⚠️ {issue_count} issue(s) – expand for details")
        else:
            st.info("Complete prerequisites below")
    with col2:
        refresh_key = f"refresh_checks_{tab_name}"
        if st.button("🔄", key=refresh_key, help="Refresh checks"):
            st.rerun()

    with st.expander("System & Prerequisites", expanded=check_results["has_issues"] or not prerq["all_ready"]):
        _render_checks_summary(check_results, prerq)
        _render_system_check_content(check_results)
        st.divider()
        _render_prerequisites_content(state, tab_name, prerq)

    return {
        "check_results": check_results,
        "all_ready": prerq["all_ready"],
        "checks": prerq["checks"],
        "images_folder_path": prerq["images_folder_path"],
        "image_count": prerq["image_count"],
    }
