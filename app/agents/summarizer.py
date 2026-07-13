"""
Summarizer agent — the first LLM-powered node in the Doc2Slides pipeline.

Reads:  state["parsed_doc"]
Writes: state["section_summaries"], state["current_step"]

For each section in the parsed document:
1. Retrieve the most relevant chunks from ChromaDB (RAG!)
2. Send them to OpenAI with a focused prompt
3. Store the 3-sentence summary

Uses gpt-4o-mini as the LLM (fast, cheap, good quality).
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from app.agents.state import AgentState
from app.vectorstore.chroma import index_document, search

# Load .env from the project root (regardless of where python is run from)
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise RuntimeError("OPENAI_API_KEY not found in .env")

_client = OpenAI(api_key=_api_key)
MODEL_NAME = "gpt-4o-mini"


SUMMARIZE_PROMPT = """You are summarizing a section of a research paper for a general audience.

Section heading: {heading}

Relevant text from the section:
---
{content}
---

Write a clear 3-sentence summary of this section. Focus on:
1. What this section is about (topic)
2. The key insight or finding
3. Why it matters

Do not use bullet points or lists. Write plain flowing sentences.
Do not start with "This section" — get straight to the substance.
"""


def summarize_section(heading: str, content: str) -> str:
    """Ask GPT for a 3-sentence summary of one section."""
    prompt = SUMMARIZE_PROMPT.format(heading=heading, content=content)
    response = _client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def summarizer_agent(state: AgentState) -> dict:
    """
    Summarizer node. Uses RAG + GPT to summarize every section.
    """
    doc = state["parsed_doc"]
    if doc is None:
        return {
            "errors": state.get("errors", []) + ["Summarizer: no parsed_doc in state"],
            "current_step": "summarizer_failed",
        }
    
    print(f"🧠 [Summarizer] Processing {len(doc.sections)} sections...")
    
    # Index the document into ChromaDB (so we can RAG over it)
    index_stats = index_document(doc)
    print(f"   Indexed {index_stats['total_chunks']} chunks into vector store")
    
    # For each section, retrieve the top chunks and summarize
    summaries = {}
    for i, section in enumerate(doc.sections, start=1):
        # RAG retrieval — get the 3 most relevant chunks
        results = search(
            query=f"key ideas from {section.heading}",
            source_file=doc.source_file,
            top_k=3,
        )
        section_chunks = [
            r["text"] for r in results 
            if r["metadata"]["section_id"] == section.id
        ]
        if not section_chunks:
            section_chunks = [section.content[:2000]]
        
        context = "\n\n".join(section_chunks)[:3000]
        
        print(f"   [{i}/{len(doc.sections)}] Summarizing {section.heading[:50]}...")
        try:
            summary = summarize_section(section.heading, context)
            summaries[section.id] = summary
        except Exception as e:
            print(f"   ⚠️  Failed on {section.id}: {e}")
            summaries[section.id] = f"[Summary failed]"
    
    print(f"✅ [Summarizer] Generated {len(summaries)} summaries")
    
    return {
        "section_summaries": summaries,
        "current_step": "summarizer_complete",
    }