"""
Parser agent — the first node in the Doc2Slides pipeline.

Reads: state["pdf_path"]
Writes: state["parsed_doc"], state["current_step"]

This agent is a thin wrapper around the parsing logic we built on Days 1-3.
The job here is to:
1. Take the PDF path from state
2. Run our existing parsing functions
3. Return the result as a state update

LangGraph automatically merges the dict we return into the state.
"""
from app.agents.state import AgentState
from app.parser.sections import detect_sections, filter_real_sections, build_document


def parser_agent(state: AgentState) -> dict:
    """
    The Parser node. Converts a raw PDF into a validated ParsedDocument.
    """
    pdf_path = state["pdf_path"]
    print(f"🔍 [Parser] Processing: {pdf_path}")
    
    try:
        # Step 1: Raw section detection (returns list of dicts)
        raw_sections = detect_sections(pdf_path)
        
        # Step 2: Filter and auto-correct
        filtered = filter_real_sections(raw_sections)
        
        # Step 3: Build the validated Pydantic ParsedDocument
        parsed_doc = build_document(pdf_path, filtered)
        
        print(f"✅ [Parser] Extracted {len(parsed_doc.sections)} sections, "
              f"{parsed_doc.total_words()} words")
        
        # Return ONLY the fields we want to update in state
        # LangGraph merges this into the existing state
        return {
            "parsed_doc": parsed_doc,
            "current_step": "parser_complete",
        }
    
    except Exception as e:
        # If parsing fails, log it and continue
        # The graph can decide what to do based on errors
        error_msg = f"Parser failed: {type(e).__name__}: {e}"
        print(f"❌ [Parser] {error_msg}")
        
        return {
            "parsed_doc": None,
            "errors": state.get("errors", []) + [error_msg],
            "current_step": "parser_failed",
        }