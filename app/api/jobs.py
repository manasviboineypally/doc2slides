"""
Job endpoints — accept PDF uploads, run the pipeline, return results.
"""
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.agents.graph import pipeline
from app.agents.state import AgentState

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Where uploaded files temporarily live
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/")
async def create_job(
    file: UploadFile = File(...),
    audience: str = Form("student"),
    slide_count: int = Form(10),
):
    """
    Accept a PDF + audience preference, run the pipeline, return parsed
    sections, summaries, and slide plan.
    
    Runs synchronously — we wait for the pipeline to finish before responding.
    Async background job support is planned.
    """
    # ── Validate file ─────────────────────────────────────────────────────
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # ── Validate audience & slide count ───────────────────────────────────
    valid_audiences = {"kid", "student", "engineer", "executive"}
    if audience not in valid_audiences:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid audience. Must be one of: {sorted(valid_audiences)}",
        )
    
    if slide_count not in (5, 10, 15):
        raise HTTPException(
            status_code=400,
            detail="slide_count must be 5, 10, or 15",
        )
    
    # ── Save uploaded file with a unique name ─────────────────────────────
    job_id = str(uuid.uuid4())[:8]
    pdf_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # ── Build initial state and run pipeline ──────────────────────────────
    initial_state: AgentState = {
        "pdf_path": str(pdf_path),
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
    
    final_state = pipeline.invoke(initial_state)
    
    # ── Return a JSON response ────────────────────────────────────────────
    if final_state["parsed_doc"] is None:
        raise HTTPException(
            status_code=500,
            detail={"errors": final_state["errors"]},
        )
    
    doc = final_state["parsed_doc"]
    return {
        "job_id": job_id,
        "status": final_state["current_step"],
        "filename": file.filename,
        "audience": audience,
        "slide_count": slide_count,
        "total_pages": doc.metadata.total_pages,
        "sections_found": doc.metadata.total_sections,
        "total_words": doc.total_words(),
        "sections": [
            {
                "id": s.id,
                "heading": s.heading,
                "page": s.page,
                "word_count": s.word_count,
            }
            for s in doc.sections
        ],
        "section_summaries": final_state.get("section_summaries"),
        "slide_plan": final_state.get("slide_plan"),
    }