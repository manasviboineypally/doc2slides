"""
FastAPI application entry point.
Run with: uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from app.api import jobs

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