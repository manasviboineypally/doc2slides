"""
LangGraph orchestration for the Doc2Slides pipeline.

Today (Day 4) the graph has just one node — the Parser. 
As we add agents on later days, we'll add more nodes and edges here.

This is the only file that needs to change when we add new agents.
The agents themselves stay independent.
"""
from langgraph.graph import StateGraph, START, END
from agents.state import AgentState
from agents.parser import parser_agent


def build_pipeline():
    """
    Build the agent pipeline.
    
    Current structure:
        START → parser → END
    
    Future structure (Week 2):
        START → parser → summarizer → planner → writer → builder → END
    """
    # Create a graph that operates on AgentState
    graph = StateGraph(AgentState)
    
    # Register the parser node
    graph.add_node("parser", parser_agent)
    
    # Define the flow: START → parser → END
    graph.add_edge(START, "parser")
    graph.add_edge("parser", END)
    
    # Compile into a runnable pipeline
    return graph.compile()


# Build once at import time
pipeline = build_pipeline()


# ── Manual test entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else "test.pdf"
    
    # Build the initial state — fields the Parser doesn't fill in start empty
    initial_state: AgentState = {
        "pdf_path": pdf_file,
        "audience": "student",          # placeholder — Writer will use this later
        "slide_count": 10,              # placeholder — Planner will use this later
        "parsed_doc": None,
        "section_summaries": None,
        "slide_plan": None,
        "written_slides": None,
        "output_path": None,
        "errors": [],
        "current_step": "starting",
    }
    
    print("=" * 70)
    print("🚀 Starting Doc2Slides pipeline")
    print("=" * 70)
    
    # Run the pipeline — this is the magic line
    final_state = pipeline.invoke(initial_state)
    
    print("\n" + "=" * 70)
    print("📋 Final state summary")
    print("=" * 70)
    print(f"Current step:    {final_state['current_step']}")
    print(f"Errors:          {len(final_state['errors'])}")
    
    if final_state["parsed_doc"]:
        doc = final_state["parsed_doc"]
        print(f"Document:        {doc.source_file}")
        print(f"Total pages:     {doc.metadata.total_pages}")
        print(f"Sections found:  {doc.metadata.total_sections}")
        print(f"Total words:     {doc.total_words()}")
        print(f"\nFirst 3 sections:")
        for s in doc.sections[:3]:
            print(f"  [{s.id}] {s.heading} ({s.word_count} words)")
    else:
        print("No document parsed — check errors above.")