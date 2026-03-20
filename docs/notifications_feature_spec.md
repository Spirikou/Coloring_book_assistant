# Notification Feature Spec

## Scope (v1)

- **Trigger:** Single task completion and whole workflow (bulk) completion
- **Channel:** In-app only (toast/banner + notification center)
- **Later:** Telegram as a second channel once in-app is stable

---

## 1. Product Goal

> When a task or workflow finishes, the app reliably alerts me in-app so I can act immediately.

---

## 2. Trigger Definition

Notifications fire for **single tasks** (one item completes) and **whole workflows** (bulk run completes). Both are in scope for v1.

### Single tasks (one item completes)

| Task | Completion Signal | Location |
|------|-------------------|----------|
| Single design creation | `state["status"] == "complete"` | features/design_generation/workflow.py |
| Single Pinterest publish | `state["pinterest_status"] == "completed"` | ui/tabs/pinterest_tab.py |
| Single Canva design creation | `workflow.create_design()` returns successfully | ui/tabs/canva_tab.py |
| Single Midjourney pipeline (one design) | `publish_status`, `uxd_action_status`, `download_status` all `"completed"` | features/image_generation/midjourney_runner.py |
| Single design in bulk Canva | One iteration of `run_bulk_canva` loop completes | ui/components/bulk_runners.py |
| Single design in bulk Pinterest | One iteration of `run_bulk_pinterest` loop completes | ui/components/bulk_runners.py |
| Single design in batch image gen | One design's MJ pipeline done | features/image_generation/midjourney_runner.py |
| Orchestration pipeline step | Each step (design, image, evaluate, canva, pinterest) completes | core/pipeline_runner.py |

### Whole workflows (bulk run completes)

| Workflow | Completion Signal | Location |
|----------|-------------------|----------|
| Bulk Design Generation | All designs from "Generate All N" complete | features/design_generation/ui.py |
| Bulk Image Gen (batch Midjourney) | All designs in batch done | features/image_generation/midjourney_runner.py |
| Bulk Pinterest | `st.success("Bulk Pinterest run completed.")` | ui/components/bulk_runners.py |
| Bulk Canva | `st.success("Bulk Canva run completed.")` | ui/components/bulk_runners.py |
| Orchestration pipeline | `shared["status"] == "completed"` | core/pipeline_runner.py |

**Explicitly out of scope for v1:** Failure alerts, job status changes (queued/running).

---

## 3. Event Contract (Schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["event_type", "task_id", "task_name", "completed_at"],
  "properties": {
    "event_type": {
      "enum": ["task.completed", "workflow.completed"],
      "description": "task.completed = single item; workflow.completed = whole bulk run"
    },
    "task_id": { "type": "string", "description": "Unique run identifier" },
    "task_name": { "type": "string", "description": "Human-readable name" },
    "completed_at": { "type": "string", "format": "date-time", "description": "ISO8601 timestamp" },
    "duration_seconds": { "type": "number", "description": "Optional elapsed time" },
    "result_summary": { "type": "string", "description": "Optional short summary" },
    "deep_link": { "type": "string", "description": "Optional tab or view to open on click" },
    "task_index": { "type": "integer", "description": "Optional: current index in bulk" },
    "task_total": { "type": "integer", "description": "Optional: total items in bulk" }
  }
}
```

**Deduplication key:** `task_id` + `event_type` + `completed_at`

---

## 4. In-App UX Spec

| Element | Recommendation |
|---------|----------------|
| Toast position | Top-right, non-blocking |
| Auto-dismiss | 5 seconds (configurable) |
| Notification center | Sidebar, list newest first |
| Max items | 20 (in-memory) |
| Clear-all | Button to clear all |
| Message template (task) | `"[Task Name] completed at [HH:MM]"` |
| Message template (workflow) | `"[Workflow Name] completed at [HH:MM]"` |
| Message template (task in bulk) | `"[Task Name] (N of M) completed at [HH:MM]"` |
| Empty state | "No notifications yet" |

---

## 5. Settings Schema

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `notifications_enabled` | bool | `true` | Master switch |
| `notifications_in_app_enabled` | bool | `true` | In-app channel |
| `notify_on_single_tasks` | bool | `true` | Task-level notifications |
| `notify_on_workflows` | bool | `true` | Workflow-level notifications |
| `notification_toast_duration_seconds` | int | `5` | Toast auto-dismiss delay |

Stored in config.py and session state; exposed via Config tab.

---

## 6. Acceptance Criteria

- [ ] Completing a single task produces exactly one `task.completed` event (when enabled)
- [ ] Completing a whole workflow produces exactly one `workflow.completed` event (when enabled)
- [ ] In-app toast appears when app is open and notifications enabled
- [ ] Notification center shows events and persists until cleared or session ends
- [ ] Disabling `notifications_enabled` prevents toast and center updates
- [ ] Disabling `notify_on_single_tasks` suppresses task-level notifications only
- [ ] Disabling `notify_on_workflows` suppresses workflow-level notifications only
- [ ] No duplicate notifications (dedup by `task_id` + `event_type` + `completed_at`)
- [ ] Empty state displays when notification center has no items

---

## 7. Observability

| Log field | Description |
|-----------|-------------|
| `task_id` | Run identifier |
| `event_type` | `task.completed` or `workflow.completed` |
| `channel` | `in_app` |
| `status` | `sent` \| `skipped` \| `error` |
| `timestamp` | ISO8601 |

---

## 8. Implementation

- **core/notifications.py** — `notify_completed()`, `queue_notification_for_subprocess()`, `process_pending_notifications()`
- **ui/components/notification_center.py** — Toast and notification center UI
- **config.py** — Notification settings
- **Config tab** — Toggle controls for notification preferences

Subprocess workflows (pipeline_runner, midjourney_runner) queue events to shared dict; main process calls `process_pending_notifications(shared)` when polling.
