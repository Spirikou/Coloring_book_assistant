"""Lightweight job model for workflow actions.

A *job* represents a single action against a design, for example:
    - design generation
    - image generation (Midjourney)
    - Canva layout creation
    - Pinterest publishing

This module focuses on the data model and persistence. Scheduling and UI
integration are handled elsewhere.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, TypedDict

from config import OUTPUT_DIR

ActionType = Literal["design", "image", "canva", "pinterest"]
JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class JobDict(TypedDict):
    """JSON-serializable representation of a job."""

    id: str
    design_path: str
    action: ActionType
    status: JobStatus
    created_at: str
    started_at: str | None
    finished_at: str | None
    error_message: str


@dataclass
class Job:
    """In-memory job representation."""

    id: str
    design_path: str
    action: ActionType
    status: JobStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str = ""

    def to_dict(self) -> JobDict:
        return JobDict(
            id=self.id,
            design_path=self.design_path,
            action=self.action,
            status=self.status,
            created_at=self.created_at.isoformat(),
            started_at=self.started_at.isoformat() if self.started_at else None,
            finished_at=self.finished_at.isoformat() if self.finished_at else None,
            error_message=self.error_message,
        )

    @classmethod
    def from_dict(cls, data: JobDict) -> "Job":
        return cls(
            id=data["id"],
            design_path=data.get("design_path", ""),
            action=data["action"],
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            finished_at=datetime.fromisoformat(data["finished_at"]) if data.get("finished_at") else None,
            error_message=data.get("error_message", ""),
        )


JOBS_FILE: Path = OUTPUT_DIR / "config" / "jobs.json"
JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_jobs_raw() -> list[Job]:
    """Load all jobs from disk. Returns empty list on error."""
    if not JOBS_FILE.exists():
        return []
    try:
        with open(JOBS_FILE, encoding="utf-8") as f:
            raw = json.load(f) or []
    except Exception:
        return []
    jobs: list[Job] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            job_dict: JobDict = {
                "id": str(item.get("id", "")) or str(uuid.uuid4()),
                "design_path": str(item.get("design_path", "")),
                "action": item.get("action", "design"),
                "status": item.get("status", "queued"),
                "created_at": item.get("created_at") or datetime.utcnow().isoformat(),
                "started_at": item.get("started_at"),
                "finished_at": item.get("finished_at"),
                "error_message": item.get("error_message", ""),
            }  # type: ignore[assignment]
            jobs.append(Job.from_dict(job_dict))
        except Exception:
            continue
    return jobs


def _save_jobs_raw(jobs: list[Job]) -> None:
    data = [job.to_dict() for job in jobs]
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_jobs() -> list[Job]:
    """Return all jobs."""
    return _load_jobs_raw()


def create_job(design_path: str, action: ActionType, status: JobStatus = "queued") -> Job:
    """Create and persist a new job."""
    jobs = _load_jobs_raw()
    job = Job(
        id=str(uuid.uuid4()),
        design_path=design_path,
        action=action,
        status=status,
        created_at=datetime.utcnow(),
    )
    jobs.append(job)
    _save_jobs_raw(jobs)
    return job


def update_job_status(job_id: str, status: JobStatus, error_message: str | None = None) -> None:
    """Update status (and optional error message) for a job."""
    jobs = _load_jobs_raw()
    changed = False
    now = datetime.utcnow()
    for job in jobs:
        if job.id == job_id:
            job.status = status
            if status == "running" and job.started_at is None:
                job.started_at = now
            if status in ("completed", "failed", "cancelled"):
                job.finished_at = now
            if error_message is not None:
                job.error_message = error_message
            changed = True
            break
    if changed:
        _save_jobs_raw(jobs)


def get_running_jobs_by_action(action: ActionType) -> list[Job]:
    """Return all jobs with given action and status 'running'."""
    return [j for j in _load_jobs_raw() if j.action == action and j.status == "running"]


def has_running_image_job() -> bool:
    """Convenience helper: True if any image-generation job is marked running."""
    return any(j.status == "running" for j in _load_jobs_raw() if j.action == "image")

