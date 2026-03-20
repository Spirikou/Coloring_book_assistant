"""In-app notification center and toast for task/workflow completion."""

from __future__ import annotations

import streamlit as st

from config import NOTIFICATION_TOAST_DURATION_SECONDS
from core.notifications import (
    NOTIFICATIONS_SESSION_KEY,
    clear_notifications,
    get_notifications,
)


def render_notification_toast() -> None:
    """Show toast for the most recent notification if one was just added."""
    last = st.session_state.pop("_last_toast", None)
    if last is None:
        return
    msg = last.get("_message", last.get("task_name", "Task") + " completed")
    try:
        st.toast(msg, duration=NOTIFICATION_TOAST_DURATION_SECONDS)
    except Exception:
        pass


def render_notification_center() -> None:
    """Render the notification center panel (sidebar or inline)."""
    notifications = get_notifications()
    with st.expander("Notifications", expanded=False):
        if not notifications:
            st.caption("No notifications yet")
        else:
            for n in notifications[:20]:
                msg = n.get("_message", n.get("task_name", "Task") + " completed")
                st.caption(msg)
            if len(notifications) > 0:
                if st.button("Clear all", key="notification_clear_all"):
                    clear_notifications()
                    st.rerun()


def render_notification_center_compact() -> None:
    """Render compact notification center for sidebar."""
    notifications = get_notifications()
    st.caption(f"**Notifications** ({len(notifications)})")
    if not notifications:
        st.caption("No notifications yet")
    else:
        for n in notifications[:10]:
            msg = n.get("_message", n.get("task_name", "Task") + " completed")
            st.caption(f"• {msg}")
        if st.button("Clear all", key="notification_clear_sidebar"):
            clear_notifications()
            st.rerun()
