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
- 🔲 Day 3: Pydantic data models
- 🔲 Week 2: Multi-agent pipeline
- 🔲 Week 3: FastAPI + deployment

See `testing_notes.md` for known limitations and test results.