"""
Shared state for the Doc2Slides agent pipeline.

This is the contract every agent agrees on. Each agent reads what it 
needs from state and writes its output back. LangGraph automatically 
merges agent outputs into the shared state object.

As we add more agents (Summarizer, Planner, Writer, Builder), they'll 
each fill in their own field.
"""
from app.schemas.plan import DeckPlan
from typing import TypedDict, Optional, List
from app.schemas.document import ParsedDocument


class AgentState(TypedDict):
    """The shared state passed between all agents in the pipeline."""
    
    # ── Input (set by the API or user before pipeline starts) ──
    pdf_path: str                       # path to the PDF to process
    audience: str                       # "kid" | "student" | "engineer" | "executive"
    slide_count: int                    # 5, 10, or 15
    
    # ── Filled by Parser agent (Day 4 — today!) ──
    parsed_doc: Optional[ParsedDocument]
    
    # ── Filled by Summarizer agent (Week 2) ──
    section_summaries: Optional[dict]
    
    # ── Filled by Planner agent (Week 2) ──
    slide_plan: Optional[dict]
    
    # ── Filled by Writer agent (Week 2) ──
    written_slides: Optional[List[dict]]
    
    # ── Filled by Builder agent (Week 2) ──
    output_path: Optional[str]
    
    # ── Bookkeeping ──
    errors: List[str]
    current_step: str