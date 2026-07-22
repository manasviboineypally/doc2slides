"""
SQLAlchemy database models for Doc2Slides.

Currently just a Job model to persist async job state.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Job(Base):
    """Persistent record of a document processing job."""
    
    __tablename__ = "jobs"
    
    job_id = Column(String(16), primary_key=True)
    status = Column(String(32), nullable=False, default="pending")  # pending / processing / completed / failed
    filename = Column(String(255), nullable=False)
    audience = Column(String(32), nullable=False)
    slide_count = Column(Integer, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    current_step = Column(String(64), nullable=False, default="starting")
    error = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)