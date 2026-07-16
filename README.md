# Doc2Slides

An AI agent that converts research papers, articles, and documents into 
audience-tailored PowerPoint presentations.

## What it does

Upload a PDF, pick your target audience (10-year-old / student / engineer / 
executive), and get back a fully editable `.pptx` deck. Same document, 
different output depending on who's reading.

## Architecture

A multi-agent pipeline built with LangGraph:

1. **Parser** — extracts structured text, sections, and figures from PDFs
2. **Summarizer** — RAG-based section summarization using ChromaDB
3. **Planner** — designs slide structure based on document content + audience
4. **Writer** — generates audience-appropriate slide content
5. **Builder** — produces the final editable `.pptx` file

## Tech stack

- **Backend:** Python, FastAPI
- **Agents:** LangGraph, LangChain
- **LLM:** OpenAI GPT-4o-mini
- **Vector DB:** ChromaDB
- **PDF parsing:** pdfplumber, PyMuPDF
- **PowerPoint generation:** python-pptx
- **Database:** PostgreSQL

## Current status

Building in public — production-ready foundations done, AI agents in progress.

**✅ Completed**
- PDF parsing with font-aware section detection
- Pydantic data contracts across the pipeline
- LangGraph multi-agent orchestration
- FastAPI HTTP layer with auto-generated Swagger docs
- ChromaDB vector store with semantic search (RAG foundation)
- Summarizer agent (LLM-powered section summarization via GPT-4o-mini)
- Planner agent (structured slide plan via JSON mode + Pydantic)
- Writer agent (audience-adaptive slide content generation)
- Builder agent (editable .pptx file generation via python-pptx)
- HTTP download endpoint (`GET /jobs/download/{filename}`)
- End-to-end testing across multiple audiences
-Async job processing with polling (`POST /jobs/` returns immediately, `GET /jobs/{job_id}` for status)


**🚧 In progress**
- PostgreSQL job persistence


**📋 Planned**
- Async background jobs
- PostgreSQL job persistence
- Minimal HTML UI
- Deployment



## Try it locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API
uvicorn app.main:app --reload

# Open the interactive docs
# http://localhost:8000/docs
```

Upload any PDF via the `/jobs/` endpoint and get back structured 
section data extracted by the LangGraph pipeline.