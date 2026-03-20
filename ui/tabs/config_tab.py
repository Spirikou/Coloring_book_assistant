"""Configuration tab for browser slots and system settings."""

from __future__ import annotations

import streamlit as st

from core.browser_config import (
    BrowserSlot,
    ValidationError,
    check_browser_connection,
    get_port_for_role,
    load_slots,
    save_slots,
    test_connection,
    validate_slots,
)
from core.jobs import list_jobs
from core.persistence import list_design_packages
from integrations.midjourney.automation.browser_utils import launch_browser_for_port


ROLE_OPTIONS = ["midjourney", "pinterest", "canva", "unused"]


def _collect_section_status() -> list[dict]:
    """Collect key status/errors for each app section to help with debugging."""
    statuses: list[dict] = []

    # Design generation
    try:
        packages = list_design_packages()
        count = len(packages)
        statuses.append({
            "section": "Design Generation",
            "status": "ok" if count > 0 else "warning",
            "message": f"{count} design package(s)" if count > 0 else "No design packages yet. Generate a design first.",
        })
    except Exception as e:
        statuses.append({
            "section": "Design Generation",
            "status": "error",
            "message": str(e),
        })

    # Image generation (Midjourney)
    try:
        port = get_port_for_role("midjourney")
        result = check_browser_connection(port)
        connected = result.get("connected", False)
        statuses.append({
            "section": "Image Generation (Midjourney)",
            "status": "ok" if connected else "error",
            "message": f"Browser connected on port {port}" if connected else f"Browser not connected on port {port}. Launch from slot above.",
        })
    except Exception as e:
        statuses.append({
            "section": "Image Generation (Midjourney)",
            "status": "error",
            "message": str(e),
        })

    # Canva design creation
    try:
        port = get_port_for_role("canva")
        result = check_browser_connection(port)
        connected = result.get("connected", False)
        statuses.append({
            "section": "Canva Design Creation",
            "status": "ok" if connected else "error",
            "message": f"Browser connected on port {port}" if connected else f"Browser not connected on port {port}. Launch from slot above.",
        })
    except Exception as e:
        statuses.append({
            "section": "Canva Design Creation",
            "status": "error",
            "message": str(e),
        })

    # Pinterest publishing
    try:
        port = get_port_for_role("pinterest")
        result = check_browser_connection(port)
        connected = result.get("connected", False)
        statuses.append({
            "section": "Pinterest Publishing",
            "status": "ok" if connected else "error",
            "message": f"Browser connected on port {port}" if connected else f"Browser not connected on port {port}. Launch from slot above.",
        })
    except Exception as e:
        statuses.append({
            "section": "Pinterest Publishing",
            "status": "error",
            "message": str(e),
        })

    # Playwright
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        statuses.append({
            "section": "Playwright",
            "status": "ok",
            "message": "Playwright installed (sync_api available)",
        })
    except Exception as e:
        statuses.append({
            "section": "Playwright",
            "status": "error",
            "message": f"Playwright issue: {e}. Run `uv sync` or `pip install playwright`.",
        })

    # Recent failed jobs
    try:
        jobs = list_jobs()
        failed = [j for j in jobs if j.status == "failed"][:3]
        if failed:
            for j in failed:
                statuses.append({
                    "section": f"Recent failure: {j.action}",
                    "status": "error",
                    "message": j.design_path or "No design path",
                })
    except Exception:
        pass

    return statuses


def _render_key_status_section() -> None:
    """Render the key status/errors expander for debugging."""
    statuses = _collect_section_status()
    has_errors = any(s["status"] == "error" for s in statuses)
    has_warnings = any(s["status"] == "warning" for s in statuses)
    expanded = has_errors or has_warnings

    with st.expander("Key status / errors (for debugging)", expanded=expanded):
        st.caption(
            "Quick health check for each section. Use this to diagnose connection or setup issues. "
            "Ports come from the browser slots below."
        )
        for item in statuses:
            section = item["section"]
            status = item["status"]
            message = item["message"]
            if status == "ok":
                st.success(f"**{section}:** {message}")
            elif status == "warning":
                st.warning(f"**{section}:** {message}")
            else:
                st.error(f"**{section}:** {message}")


def _render_slot_editor(slot: BrowserSlot, index: int) -> BrowserSlot:
    """Render UI controls for a single browser slot and return updated slot. Narrow port column."""
    col_role, col_port, col_label, col_test, col_launch = st.columns([2, 1, 3, 2, 2])
    with col_role:
        role = st.selectbox(
            "Role",
            options=ROLE_OPTIONS,
            index=ROLE_OPTIONS.index(slot.role) if slot.role in ROLE_OPTIONS else ROLE_OPTIONS.index("unused"),
            key=f"browser_slot_{index}_role",
        )
    with col_port:
        port = st.number_input(
            "Port",
            min_value=1,
            max_value=65535,
            value=int(slot.port) if slot.port > 0 else 9222,
            step=1,
            key=f"browser_slot_{index}_port",
        )
    with col_label:
        label = st.text_input(
            "Label",
            value=slot.label or "",
            key=f"browser_slot_{index}_label",
            placeholder="Optional name (e.g. Midjourney, Pinterest 1)",
        )
    status_msg = ""
    with col_test:
        if st.button("Test", key=f"browser_slot_{index}_test"):
            ok, msg = test_connection(int(port))
            status_msg = msg
            if ok:
                st.success("Connected")
            else:
                st.error("Not reachable")
    with col_launch:
        if st.button("Launch", key=f"browser_slot_{index}_launch", help=f"Start browser on port {port}"):
            result = launch_browser_for_port(int(port))
            if result.get("success"):
                st.success("Launched")
            else:
                st.error(result.get("message", "Launch failed"))
            if result.get("message"):
                status_msg = result["message"]
    if status_msg:
        st.caption(status_msg)

    return BrowserSlot(id=slot.id, role=role, port=int(port), label=label)


def _render_current_jobs_section() -> None:
    """Compact summary of running and recent jobs for Config tab."""
    jobs = list_jobs()
    running = [j for j in jobs if j.status == "running"]
    recent = sorted(
        [j for j in jobs if j.status in ("completed", "failed", "queued")],
        key=lambda j: j.created_at,
        reverse=True,
    )[:10]
    packages = {p["path"]: p["title"] for p in list_design_packages()}

    def _design_label(path: str) -> str:
        if not path:
            return "—"
        return packages.get(path, path[:50] + "…" if len(path) > 50 else path)

    if not running and not recent:
        st.caption("No jobs yet. Go to **Design Generation**, **Image Generation**, or **Orchestration** to run workflows.")
        return
    if running:
        st.markdown("**Running**")
        for j in running:
            st.caption(f"• {j.action}: {_design_label(j.design_path)}")
    if recent:
        st.markdown("**Recent**")
        for j in recent:
            st.caption(f"• {j.action} – {_design_label(j.design_path)} ({j.status})")
    st.caption("See **Progress** tab for full history.")


@st.fragment
def render_config_tab() -> None:
    """Render the configuration tab. Fragment so tab stays stable when other tabs rerun."""
    st.header("Configuration")
    st.caption("Configure browser slots, ports, and basic system settings.")

    _render_key_status_section()

    # One-line job summary outside expander
    jobs = list_jobs()
    running = [j for j in jobs if j.status == "running"]
    recent_count = len([j for j in jobs if j.status in ("completed", "failed", "queued")])
    if running or recent_count:
        summary_parts = []
        if running:
            summary_parts.append(f"**{len(running)} running**")
        if recent_count:
            summary_parts.append(f"{recent_count} recent")
        st.caption("Jobs: " + ", ".join(summary_parts) + " — expand for details.")
    with st.expander("Current jobs", expanded=bool(running)):
        _render_current_jobs_section()

    st.subheader("Notifications")
    st.caption("Control when completion alerts appear (in-app toast and notification center).")
    if "notification_settings" not in st.session_state:
        from config import (
            NOTIFICATIONS_ENABLED,
            NOTIFICATIONS_IN_APP_ENABLED,
            NOTIFY_ON_SINGLE_TASKS,
            NOTIFY_ON_WORKFLOWS,
        )
        st.session_state.notification_settings = {
            "enabled": NOTIFICATIONS_ENABLED,
            "in_app": NOTIFICATIONS_IN_APP_ENABLED,
            "single_tasks": NOTIFY_ON_SINGLE_TASKS,
            "workflows": NOTIFY_ON_WORKFLOWS,
        }
    ns = st.session_state.notification_settings
    c1, c2 = st.columns(2)
    with c1:
        ns["enabled"] = st.toggle("Notifications enabled", value=ns.get("enabled", True), key="notif_enabled")
        ns["in_app"] = st.toggle("In-app notifications", value=ns.get("in_app", True), key="notif_in_app")
    with c2:
        ns["single_tasks"] = st.toggle("Notify on single tasks", value=ns.get("single_tasks", True), key="notif_single_tasks")
        ns["workflows"] = st.toggle("Notify on workflows", value=ns.get("workflows", True), key="notif_workflows")
    st.session_state.notification_settings = ns

    slots = load_slots()

    st.subheader("Browser slots")
    st.caption(
        "Define up to four browser instances. Use **Launch** to start a browser on each slot's port "
        "(each uses a separate profile). Or start browsers manually and assign roles and ports here."
    )

    updated_slots: list[BrowserSlot] = []
    for idx, slot in enumerate(slots):
        with st.expander(f"Slot {idx + 1} – {slot.label or slot.id}", expanded=True if idx == 0 else False):
            updated = _render_slot_editor(slot, idx)
            updated_slots.append(updated)

    col_save, col_reset = st.columns([2, 1])
    save_clicked = False
    with col_save:
        save_clicked = st.button("Save configuration", type="primary")
    with col_reset:
        reset_clicked = st.button("Reset to defaults", type="secondary", help="Reset all browser slots to default ports and roles.")

    if reset_clicked:
        st.session_state["config_confirm_reset"] = True
        st.rerun()

    if st.session_state.get("config_confirm_reset"):
        st.warning("**Reset all browser slots to defaults?** This cannot be undone.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm reset", key="config_confirm_reset_btn", type="primary"):
                from core.browser_config import _default_slots  # type: ignore[import]
                defaults = _default_slots()
                try:
                    validate_slots(defaults)
                    save_slots(defaults)
                    st.session_state.pop("config_confirm_reset", None)
                    st.success("Browser slots reset to defaults.")
                    st.rerun()
                except ValidationError as e:
                    st.error(f"Default configuration invalid: {e}")
        with c2:
            if st.button("Cancel", key="config_cancel_reset_btn"):
                st.session_state.pop("config_confirm_reset", None)
                st.rerun()
        st.stop()

    if save_clicked:
        try:
            validate_slots(updated_slots)
        except ValidationError as e:
            st.error(str(e))
        else:
            save_slots(updated_slots)
            st.success("Browser configuration saved.")

