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
- **LLM:** Google Gemini
- **Vector DB:** ChromaDB
- **PDF parsing:** pdfplumber, PyMuPDF
- **PowerPoint generation:** python-pptx
- **Database:** PostgreSQL

## Status

🚧 Currently building this project. Progress:
- ✅ Day 1: PDF text extraction
- ✅ Day 2: Section detection with font analysis
- ✅ Day 3: Pydantic data models
- ✅ Day 4: LangGraph multi-agent orchestration
- ✅ Day 5: FastAPI HTTP layer + interactive Swagger docs
- 🔲 Day 6: ChromaDB + chunking
- 🔲 Week 2: Summarizer, Planner, Writer, Builder agents
- 🔲 Week 3: Async background jobs + deployment

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