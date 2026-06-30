"""
Job endpoints — accept PDF uploads, run the pipeline, return results.
"""
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.agents.graph import pipeline
from app.agents.state import AgentState

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Where uploaded files temporarily live
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/")
async def create_job(file: UploadFile = File(...)):
    """
    Accept a PDF, run the pipeline, return parsed sections.
    
    Today (Day 5) this runs synchronously — we wait for the parser to 
    finish before responding. On Day 12 we'll make it async with 
    background tasks.
    """
    # 1. Validate
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # 2. Save uploaded file with a unique name
    job_id = str(uuid.uuid4())[:8]
    pdf_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # 3. Build initial state and run pipeline
    initial_state: AgentState = {
        "pdf_path": str(pdf_path),
        "audience": "student",
        "slide_count": 10,
        "parsed_doc": None,
        "section_summaries": None,
        "slide_plan": None,
        "written_slides": None,
        "output_path": None,
        "errors": [],
        "current_step": "starting",
    }
    
    final_state = pipeline.invoke(initial_state)
    
    # 4. Return a JSON response
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
    }