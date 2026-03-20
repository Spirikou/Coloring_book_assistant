"""Notification service for task and workflow completion alerts.

Supports in-app toast and notification center. Events can be emitted directly
(from Streamlit context) or queued from subprocesses via a shared dict.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

logger = logging.getLogger(__name__)

NOTIFICATIONS_SESSION_KEY = "notifications"
PENDING_NOTIFICATIONS_KEY = "pending_notifications"
MAX_NOTIFICATIONS = 20

EventType = Literal["task.completed", "workflow.completed"]


def _get_notification_config() -> dict[str, Any]:
    """Get notification settings from config or session state overrides."""
    try:
        from config import (
            NOTIFICATIONS_ENABLED,
            NOTIFICATIONS_IN_APP_ENABLED,
            NOTIFY_ON_SINGLE_TASKS,
            NOTIFY_ON_WORKFLOWS,
        )
        defaults = {
            "enabled": NOTIFICATIONS_ENABLED,
            "in_app": NOTIFICATIONS_IN_APP_ENABLED,
            "single_tasks": NOTIFY_ON_SINGLE_TASKS,
            "workflows": NOTIFY_ON_WORKFLOWS,
        }
    except ImportError:
        defaults = {
            "enabled": True,
            "in_app": True,
            "single_tasks": True,
            "workflows": True,
        }
    try:
        import streamlit as st
        overrides = st.session_state.get("notification_settings", {})
        return {k: overrides.get(k, v) for k, v in defaults.items()}
    except Exception:
        return defaults


def _should_send(event_type: EventType, config: dict[str, Any]) -> bool:
    """Check if notification should be sent based on settings."""
    if not config.get("enabled", True):
        return False
    if not config.get("in_app", True):
        return False
    if event_type == "task.completed" and not config.get("single_tasks", True):
        return False
    if event_type == "workflow.completed" and not config.get("workflows", True):
        return False
    return True


def _format_message(event: dict[str, Any]) -> str:
    """Format notification message from event."""
    task_name = event.get("task_name", "Task")
    completed_at = event.get("completed_at", "")
    try:
        if isinstance(completed_at, str) and "T" in completed_at:
            dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        else:
            dt = datetime.now(timezone.utc)
        time_str = dt.strftime("%H:%M")
    except (ValueError, TypeError):
        time_str = "now"
    idx = event.get("task_index")
    total = event.get("task_total")
    if idx is not None and total is not None and total > 1:
        return f"{task_name} ({idx} of {total}) completed at {time_str}"
    return f"{task_name} completed at {time_str}"


def _dedup_key(event: dict[str, Any]) -> str:
    """Generate deduplication key for event."""
    return f"{event.get('task_id', '')}:{event.get('event_type', '')}:{event.get('completed_at', '')}"


def notify_completed(
    event_type: EventType,
    task_id: str,
    task_name: str,
    completed_at: str | None = None,
    duration_seconds: float | None = None,
    result_summary: str | None = None,
    deep_link: str | None = None,
    task_index: int | None = None,
    task_total: int | None = None,
) -> bool:
    """Emit a completion notification (call from Streamlit context).

    Returns True if notification was sent, False if skipped (disabled or dedup).
    """
    if completed_at is None:
        completed_at = datetime.now(timezone.utc).isoformat()
    config = _get_notification_config()
    if not _should_send(event_type, config):
        logger.info(
            "Notification skipped task_id=%s event_type=%s channel=in_app status=skipped",
            task_id, event_type,
        )
        return False
    event = {
        "event_type": event_type,
        "task_id": task_id,
        "task_name": task_name,
        "completed_at": completed_at,
        "duration_seconds": duration_seconds,
        "result_summary": result_summary,
        "deep_link": deep_link,
        "task_index": task_index,
        "task_total": task_total,
    }
    try:
        import streamlit as st
        if NOTIFICATIONS_SESSION_KEY not in st.session_state:
            st.session_state[NOTIFICATIONS_SESSION_KEY] = []
        notifications = st.session_state[NOTIFICATIONS_SESSION_KEY]
        key = _dedup_key(event)
        seen = {_dedup_key(n) for n in notifications}
        if key in seen:
            return False
        event["_message"] = _format_message(event)
        notifications.insert(0, event)
        if len(notifications) > MAX_NOTIFICATIONS:
            st.session_state[NOTIFICATIONS_SESSION_KEY] = notifications[:MAX_NOTIFICATIONS]
        st.session_state["_last_toast"] = event
        logger.info(
            "Notification task_id=%s event_type=%s channel=in_app status=sent timestamp=%s",
            task_id, event_type, completed_at,
        )
        return True
    except Exception as e:
        logger.exception("Notification error: %s", e)
        return False


def queue_notification_for_subprocess(
    shared: dict,
    event_type: EventType,
    task_id: str,
    task_name: str,
    completed_at: str | None = None,
    duration_seconds: float | None = None,
    result_summary: str | None = None,
    deep_link: str | None = None,
    task_index: int | None = None,
    task_total: int | None = None,
) -> None:
    """Queue a notification from a subprocess. Main process will process via process_pending_notifications."""
    if completed_at is None:
        completed_at = datetime.now(timezone.utc).isoformat()
    event = {
        "event_type": event_type,
        "task_id": task_id,
        "task_name": task_name,
        "completed_at": completed_at,
        "duration_seconds": duration_seconds,
        "result_summary": result_summary,
        "deep_link": deep_link,
        "task_index": task_index,
        "task_total": task_total,
    }
    if PENDING_NOTIFICATIONS_KEY not in shared:
        shared[PENDING_NOTIFICATIONS_KEY] = []
    try:
        shared[PENDING_NOTIFICATIONS_KEY].append(event)
    except Exception as e:
        logger.warning("Could not queue notification in shared dict: %s", e)


def process_pending_notifications(shared: dict) -> int:
    """Process notifications queued by subprocesses. Call from main Streamlit process when polling shared.

    Returns number of notifications processed.
    """
    pending = shared.pop(PENDING_NOTIFICATIONS_KEY, [])
    if not pending:
        return 0
    count = 0
    for event in pending:
        try:
            if notify_completed(
                event_type=event.get("event_type", "task.completed"),
                task_id=event.get("task_id", "unknown"),
                task_name=event.get("task_name", "Task"),
                completed_at=event.get("completed_at"),
                duration_seconds=event.get("duration_seconds"),
                result_summary=event.get("result_summary"),
                deep_link=event.get("deep_link"),
                task_index=event.get("task_index"),
                task_total=event.get("task_total"),
            ):
                count += 1
        except Exception as e:
            logger.warning("Failed to process queued notification: %s", e)
    return count


def clear_notifications() -> None:
    """Clear all notifications from the notification center."""
    try:
        import streamlit as st
        st.session_state[NOTIFICATIONS_SESSION_KEY] = []
    except Exception:
        pass


def get_notifications() -> list[dict[str, Any]]:
    """Get current notifications list (newest first)."""
    try:
        import streamlit as st
        return list(st.session_state.get(NOTIFICATIONS_SESSION_KEY, []))
    except Exception:
        return []
