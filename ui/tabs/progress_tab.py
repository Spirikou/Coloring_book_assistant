"""Progress tab - overview of designs, jobs, and browser slots."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from core.browser_config import load_slots, test_connection
from core.jobs import Job, list_jobs
from core.persistence import list_design_packages


def _format_dt(iso_str: str | None) -> str:
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_str


def _truncate_path(path: str, max_len: int = 50) -> str:
    """Truncate path for display, show tail."""
    if not path or len(path) <= max_len:
        return path or "—"
    return "…" + path[-(max_len - 1):]


def _render_designs_section(jobs: list[Job]) -> None:
    st.subheader("Designs")
    packages = list_design_packages()
    if not packages:
        st.caption("No design packages found. Go to the **Design Generation** tab to create one.")
        return

    # Map design path -> job summaries (image jobs for now)
    image_jobs_by_design: dict[str, list[Job]] = {}
    for job in jobs:
        if job.action != "image":
            continue
        key = job.design_path or ""
        image_jobs_by_design.setdefault(key, []).append(job)

    # Header row
    h_cols = st.columns([3, 1, 2, 2])
    h_cols[0].markdown("**Design**")
    h_cols[1].markdown("**Images**")
    h_cols[2].markdown("**Last image job**")
    h_cols[3].markdown("**Status**")

    for pkg in packages:
        path = pkg["path"]
        title = pkg["title"]
        img_count = pkg["image_count"]
        jobs_for_design = sorted(
            image_jobs_by_design.get(path, []),
            key=lambda j: j.created_at,
            reverse=True,
        )
        last_job = jobs_for_design[0] if jobs_for_design else None
        row_cols = st.columns([3, 1, 2, 2])
        with row_cols[0]:
            st.write(title)
            st.caption(_truncate_path(path))
        with row_cols[1]:
            st.write(img_count)
        with row_cols[2]:
            if last_job:
                st.write(last_job.status)
                st.caption(_format_dt(last_job.created_at.isoformat()))
            else:
                st.caption("No image jobs")
        with row_cols[3]:
            if last_job:
                if last_job.status == "running":
                    st.caption("Running")
                elif last_job.status == "completed":
                    st.caption("Completed")
                elif last_job.status == "failed":
                    st.caption("Failed")
                else:
                    st.caption(last_job.status)
            else:
                st.caption("Idle")


def _render_jobs_section(jobs: list[Job]) -> None:
    st.subheader("Jobs")
    if not jobs:
        st.caption("No jobs recorded yet. Run design gen, image gen, or a pipeline from other tabs to see jobs here.")
        return

    jobs_sorted = sorted(jobs, key=lambda j: j.created_at, reverse=True)[:50]

    # Header row
    h_cols = st.columns([1, 1, 3, 2, 2])
    h_cols[0].markdown("**Action**")
    h_cols[1].markdown("**Status**")
    h_cols[2].markdown("**Design path**")
    h_cols[3].markdown("**Started**")
    h_cols[4].markdown("**Finished**")

    for job in jobs_sorted:
        row_cols = st.columns([1, 1, 3, 2, 2])
        with row_cols[0]:
            st.write(job.action)
        with row_cols[1]:
            st.caption(job.status)
        with row_cols[2]:
            st.caption(_truncate_path(job.design_path or ""))
        with row_cols[3]:
            st.caption(_format_dt(job.created_at.isoformat()))
        with row_cols[4]:
            finished = job.finished_at.isoformat() if job.finished_at else None
            st.caption(_format_dt(finished))


def _render_browser_slots_section() -> None:
    st.subheader("Browser slots")
    slots = load_slots()
    if not slots:
        st.caption("No slots configured.")
        return

    # Header row
    h_cols = st.columns([1, 1, 1, 2])
    h_cols[0].markdown("**Slot**")
    h_cols[1].markdown("**Role**")
    h_cols[2].markdown("**Port**")
    h_cols[3].markdown("**Connection**")

    for slot in slots:
        row_cols = st.columns([1, 1, 1, 2])
        with row_cols[0]:
            st.write(slot.id)
            if slot.label:
                st.caption(slot.label)
        with row_cols[1]:
            st.write(slot.role)
        with row_cols[2]:
            st.write(slot.port)
        with row_cols[3]:
            ok, msg = test_connection(slot.port)
            if slot.role == "unused":
                st.caption("unused")
            elif ok:
                st.caption("Connected")
                if msg:
                    st.caption(msg)
            else:
                st.caption("Not reachable")
                if msg:
                    st.caption(msg)


@st.fragment
def render_progress_tab() -> None:
    """Render the Progress tab. Fragment so tab stays stable when other tabs rerun."""
    st.header("Progress")
    st.caption("Overview of designs, jobs, and browser slots.")

    jobs = list_jobs()
    packages = list_design_packages()
    n_designs = len(packages) if packages else 0
    n_jobs = len(jobs)
    n_running = sum(1 for j in jobs if j.status == "running")
    try:
        from core.browser_config import load_slots
        slots = load_slots()
        n_slots = len(slots) if slots else 0
    except Exception:
        n_slots = 0

    # Summary line at top
    summary = f"**Designs:** {n_designs}  |  **Jobs:** {n_jobs}" + (f" ({n_running} running)" if n_running else "") + f"  |  **Slots:** {n_slots}"
    st.markdown(summary)

    sub_tab_designs, sub_tab_jobs, sub_tab_browser = st.tabs(["Designs", "Jobs", "Browser slots"])
    with sub_tab_designs:
        with st.container():
            _render_designs_section(jobs)
    with sub_tab_jobs:
        with st.container():
            _render_jobs_section(jobs)
    with sub_tab_browser:
        with st.container():
            _render_browser_slots_section()

