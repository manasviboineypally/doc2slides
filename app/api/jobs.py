"""
Job endpoints — accept PDF uploads, run the pipeline asynchronously.

Flow:
1. POST /jobs/         → creates a job, schedules pipeline as background task, returns job_id
2. GET /jobs/{job_id}  → returns current status of the job
3. GET /jobs/download/{filename} → serves the finished .pptx file
"""
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.agents.graph import pipeline
from app.agents.state import AgentState
from app.api.job_store import create_job, update_job, get_job

router = APIRouter(prefix="/jobs", tags=["jobs"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


def run_pipeline_task(job_id: str, pdf_path: str, audience: str, slide_count: int):
    """
    The actual pipeline runner. Runs in the background.
    Updates the job_store as the pipeline progresses.
    """
    from datetime import datetime
    
    update_job(job_id, status="processing", started_at=datetime.utcnow().isoformat())
    
    initial_state: AgentState = {
        "pdf_path": pdf_path,
        "audience": audience,
        "slide_count": slide_count,
        "parsed_doc": None,
        "section_summaries": None,
        "slide_plan": None,
        "written_slides": None,
        "output_path": None,
        "errors": [],
        "current_step": "starting",
    }
    
    try:
        final_state = pipeline.invoke(initial_state)
        
        # Extract useful data for the client
        doc = final_state["parsed_doc"]
        output_path = final_state.get("output_path")
        
        result = {
            "total_pages": doc.metadata.total_pages if doc else None,
            "sections_found": doc.metadata.total_sections if doc else None,
            "total_words": doc.total_words() if doc else None,
            "download_url": f"/jobs/download/{Path(output_path).name}" if output_path else None,
            "sections": [
                {"id": s.id, "heading": s.heading, "page": s.page, "word_count": s.word_count}
                for s in doc.sections
            ] if doc else [],
            "section_summaries": final_state.get("section_summaries"),
            "slide_plan": final_state.get("slide_plan"),
            "written_slides": final_state.get("written_slides"),
        }
        
        update_job(
            job_id,
            status="completed",
            completed_at=datetime.utcnow().isoformat(),
            current_step=final_state["current_step"],
            result=result,
        )
    
    except Exception as e:
        update_job(
            job_id,
            status="failed",
            completed_at=datetime.utcnow().isoformat(),
            error=f"{type(e).__name__}: {e}",
        )


@router.post("/")
async def create_job_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    audience: str = Form("student"),
    slide_count: int = Form(10),
):
    """
    Accept a PDF upload, schedule the pipeline in the background,
    and return a job_id immediately for polling.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    valid_audiences = {"kid", "student", "engineer", "executive"}
    if audience not in valid_audiences:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid audience. Must be one of: {sorted(valid_audiences)}",
        )
    
    if slide_count < 3 or slide_count > 50:
        raise HTTPException(
            status_code=400,
            detail="slide_count must be between 3 and 50",
        )
    
    # Save uploaded PDF
    job_id = str(uuid.uuid4())[:8]
    pdf_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # Register the job as pending
    create_job(job_id, file.filename, audience, slide_count)
    
    # Schedule the pipeline to run in the background
    background_tasks.add_task(
        run_pipeline_task,
        job_id=job_id,
        pdf_path=str(pdf_path),
        audience=audience,
        slide_count=slide_count,
    )
    
    # Return immediately with the job_id
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Job created. Poll GET /jobs/{job_id} for status.",
        "poll_url": f"/jobs/{job_id}",
    }


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    """Poll this endpoint to check job status."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/download/{filename}")
async def download_file(filename: str):
    """Serve a generated .pptx file for download."""
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists() or file_path.parent.resolve() != OUTPUT_DIR.resolve():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )