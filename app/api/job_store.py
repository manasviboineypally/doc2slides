"""
In-memory job store for tracking async pipeline jobs.

This is a temporary solution — Day 13 will replace this with PostgreSQL.
For now, jobs live in a Python dict, which means they disappear when 
the server restarts. That's fine for MVP.
"""
from datetime import datetime
from typing import Optional


# Global dict mapping job_id → job info
_jobs: dict = {}


def create_job(job_id: str, filename: str, audience: str, slide_count: int) -> dict:
    """Register a new job as pending."""
    job = {
        "job_id": job_id,
        "status": "pending",
        "filename": filename,
        "audience": audience,
        "slide_count": slide_count,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "current_step": "starting",
        "error": None,
        "result": None,
    }
    _jobs[job_id] = job
    return job


def update_job(job_id: str, **updates) -> Optional[dict]:
    """Update fields on an existing job."""
    if job_id not in _jobs:
        return None
    _jobs[job_id].update(updates)
    return _jobs[job_id]


def get_job(job_id: str) -> Optional[dict]:
    """Retrieve a job by ID."""
    return _jobs.get(job_id)


def all_jobs() -> list:
    """Return all jobs (for debugging or an admin endpoint later)."""
    return list(_jobs.values())