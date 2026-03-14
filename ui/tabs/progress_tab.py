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


def _render_designs_section(jobs: list[Job]) -> None:
    st.subheader("Designs")
    packages = list_design_packages()
    if not packages:
        st.caption("No design packages found.")
        return

    # Map design path -> job summaries (image jobs for now)
    image_jobs_by_design: dict[str, list[Job]] = {}
    for job in jobs:
        if job.action != "image":
            continue
        key = job.design_path or ""
        image_jobs_by_design.setdefault(key, []).append(job)

    cols = st.columns([3, 2, 2, 2])
    cols[0].markdown("**Design**")
    cols[1].markdown("**Images**")
    cols[2].markdown("**Last image job**")
    cols[3].markdown("**Status**")

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
        with cols[0]:
            st.write(title)
            st.caption(path)
        with cols[1]:
            st.write(img_count)
        with cols[2]:
            if last_job:
                st.write(last_job.status)
                st.caption(_format_dt(last_job.created_at.isoformat()))
            else:
                st.caption("No image jobs")
        with cols[3]:
            if last_job:
                if last_job.status == "running":
                    st.info("Image generation running")
                elif last_job.status == "completed":
                    st.success("Image generation completed")
                elif last_job.status == "failed":
                    st.error("Image generation failed")
                else:
                    st.caption(last_job.status)
            else:
                st.caption("Idle")


def _render_jobs_section(jobs: list[Job]) -> None:
    st.subheader("Jobs")
    if not jobs:
        st.caption("No jobs recorded yet.")
        return

    # Sort newest first
    jobs_sorted = sorted(jobs, key=lambda j: j.created_at, reverse=True)[:50]

    cols = st.columns([2, 2, 2, 3, 3])
    cols[0].markdown("**Action**")
    cols[1].markdown("**Status**")
    cols[2].markdown("**Design path**")
    cols[3].markdown("**Started**")
    cols[4].markdown("**Finished**")

    for job in jobs_sorted:
        with cols[0]:
            st.write(job.action)
        with cols[1]:
            if job.status == "running":
                st.info("running")
            elif job.status == "completed":
                st.success("completed")
            elif job.status == "failed":
                st.error("failed")
            else:
                st.caption(job.status)
        with cols[2]:
            st.caption(job.design_path or "—")
        with cols[3]:
            st.caption(_format_dt(job.created_at.isoformat()))
        with cols[4]:
            finished = job.finished_at.isoformat() if job.finished_at else None
            st.caption(_format_dt(finished))


def _render_browser_slots_section() -> None:
    st.subheader("Browser slots")
    slots = load_slots()
    if not slots:
        st.caption("No slots configured.")
        return

    cols = st.columns([1, 2, 2, 3])
    cols[0].markdown("**Slot**")
    cols[1].markdown("**Role**")
    cols[2].markdown("**Port**")
    cols[3].markdown("**Connection**")

    for slot in slots:
        with cols[0]:
            st.write(slot.id)
            if slot.label:
                st.caption(slot.label)
        with cols[1]:
            st.write(slot.role)
        with cols[2]:
            st.write(slot.port)
        with cols[3]:
            ok, msg = test_connection(slot.port)
            if slot.role == "unused":
                st.caption("unused")
            elif ok:
                st.success("connected")
                st.caption(msg)
            else:
                st.warning("not reachable")
                st.caption(msg)


def render_progress_tab() -> None:
    """Render the Progress tab."""
    st.header("Progress")
    st.caption("Overview of designs, jobs, and browser slots.")

    jobs = list_jobs()

    with st.container():
        _render_designs_section(jobs)

    st.markdown("---")

    with st.container():
        _render_jobs_section(jobs)

    st.markdown("---")

    with st.container():
        _render_browser_slots_section()

