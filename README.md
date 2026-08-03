# Doc2Slides

An AI agent that converts research papers, articles, and documents into 
audience-tailored PowerPoint presentations.

## What it does

Upload a PDF, pick your target audience (10-year-old / student / engineer / 
executive), and get back a fully editable `.pptx` deck. Same document, 
different output depending on who's reading.


## 🚀 Live demo

**Try it now:** [web-production-6eded.up.railway.app](https://web-production-6eded.up.railway.app)

Upload any PDF, pick your audience, and get a downloadable PowerPoint in ~30 seconds.


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
- **PDF parsing:** pdfplumber
- **PowerPoint generation:** python-pptx
- **Database:** PostgreSQL (SQLAlchemy)
- **Frontend:** Vanilla HTML/CSS/JS (no build step)

## Current status

Building in public.

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
- Async job processing with polling (`POST /jobs/` returns immediately, `GET /jobs/{job_id}` for status)
- PostgreSQL job persistence via SQLAlchemy
- Modern HTML UI with drag-drop, audience cards, and real-time progress
- Evaluation harness (parser assertions + RAG precision + LLM-as-judge for summaries)
- Deployed to Railway (public URL, PostgreSQL, auto-deploy on git push)

**🚧 In progress**
- Demo video

**📋 Planned**
- Demo video
- Blog post write-up

## Try it locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set up your .env file
# OPENAI_API_KEY=your-key-here
# DATABASE_URL=postgresql+psycopg2://postgres:PASSWORD@localhost:5432/doc2slides

# Run the API
uvicorn app.main:app --reload

# Open the UI
# http://localhost:8000/

# Or use the API directly
# http://localhost:8000/docs
```

Upload any PDF, pick an audience, choose the number of slides (3-50), 
and get back a downloadable `.pptx` deck.

## Evaluation

The `evals/` folder contains three evaluation strategies:

- **Parser evals** — deterministic ground-truth assertions on section detection
- **RAG evals** — top-K precision on hand-labeled query→section pairs
- **Summarizer evals** — GPT-as-judge scoring faithfulness, completeness, clarity

Run any of them individually:

```bash
python -m evals.parser_eval
python -m evals.rag_eval
python -m evals.summary_eval
```