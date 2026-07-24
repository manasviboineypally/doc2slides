"""
FastAPI application entry point.
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import jobs
from app.db.session import init_db

# Create tables if they don't exist
init_db()

app = FastAPI(
    title="Doc2Slides API",
    description="Convert PDFs into audience-tailored slide presentations.",
    version="0.14.0",
)

app.include_router(jobs.router)

# Serve static assets (CSS, JS, images) from /static/*
STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    """Serve the main UI page."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api")
async def api_root():
    """API info endpoint (was previously /)."""
    return {
        "message": "Doc2Slides API is running",
        "docs": "/docs",
        "create_job": "POST /jobs/",
    }