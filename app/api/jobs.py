"""
Job endpoints — accept PDF uploads, run the pipeline, return results.
"""
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from app.agents.graph import pipeline
from app.agents.state import AgentState

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Where uploaded files temporarily live
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Where generated .pptx files land
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


@router.post("/")
async def create_job(
    file: UploadFile = File(...),
    audience: str = Form("student"),
    slide_count: int = Form(10),
):
    """
    Accept a PDF + audience preference, run the pipeline, return parsed
    sections, summaries, slide plan, written slides, and a download URL
    for the generated .pptx file.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
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
    
    # Save uploaded PDF
    job_id = str(uuid.uuid4())[:8]
    pdf_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # Build initial state and run pipeline
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
    
    if final_state["parsed_doc"] is None:
        raise HTTPException(
            status_code=500,
            detail={"errors": final_state["errors"]},
        )
    
    # Build download URL from the output path
    output_path = final_state.get("output_path")
    download_url = None
    if output_path:
        filename = Path(output_path).name
        download_url = f"/jobs/download/{filename}"
    
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
        "download_url": download_url,
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
        "written_slides": final_state.get("written_slides"),
    }


@router.get("/download/{filename}")
async def download_file(filename: str):
    """Serve a generated .pptx file for download."""
    file_path = OUTPUT_DIR / filename
    
    # Prevent path traversal attacks
    if not file_path.exists() or file_path.parent.resolve() != OUTPUT_DIR.resolve():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )