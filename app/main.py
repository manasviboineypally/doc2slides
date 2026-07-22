"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from app.api import jobs
from app.db.session import init_db

# Create tables if they don't exist
init_db()

app = FastAPI(
    title="Doc2Slides API",
    description="Convert PDFs into audience-tailored slide presentations.",
    version="0.5.0",
)

app.include_router(jobs.router)


@app.get("/")
async def root():
    return {
        "message": "Doc2Slides API is running",
        "docs": "/docs",
        "create_job": "POST /jobs/",
    }