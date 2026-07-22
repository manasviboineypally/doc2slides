"""
Persistent job store using SQLAlchemy + PostgreSQL.

This replaces the previous in-memory dict-based store. Jobs now survive
server restarts and can be queried across sessions.
"""
from datetime import datetime
from typing import Optional
from app.db.session import SessionLocal
from app.db.models import Job


def create_job(job_id: str, filename: str, audience: str, slide_count: int) -> dict:
    """Register a new job as pending."""
    db = SessionLocal()
    try:
        job = Job(
            job_id=job_id,
            status="pending",
            filename=filename,
            audience=audience,
            slide_count=slide_count,
            created_at=datetime.utcnow(),
            current_step="starting",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return _job_to_dict(job)
    finally:
        db.close()


def update_job(job_id: str, **updates) -> Optional[dict]:
    """Update fields on an existing job."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return None
        
        for key, value in updates.items():
            if hasattr(job, key):
                setattr(job, key, value)
        
        db.commit()
        db.refresh(job)
        return _job_to_dict(job)
    finally:
        db.close()


def get_job(job_id: str) -> Optional[dict]:
    """Retrieve a job by ID."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return None
        return _job_to_dict(job)
    finally:
        db.close()


def all_jobs() -> list:
    """Return all jobs (for debugging or an admin endpoint)."""
    db = SessionLocal()
    try:
        jobs = db.query(Job).order_by(Job.created_at.desc()).all()
        return [_job_to_dict(j) for j in jobs]
    finally:
        db.close()


def _job_to_dict(job: Job) -> dict:
    """Convert a Job SQLAlchemy row into a plain dict for API responses."""
    return {
        "job_id": job.job_id,
        "status": job.status,
        "filename": job.filename,
        "audience": job.audience,
        "slide_count": job.slide_count,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "current_step": job.current_step,
        "error": job.error,
        "result": job.result,
    }