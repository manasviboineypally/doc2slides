"""
LangGraph orchestration for the Doc2Slides pipeline.

Current structure: START → parser → summarizer → planner → END

As we add agents on later days, we'll add more nodes and edges here.
This is the only file that needs to change when we add new agents.
The agents themselves stay independent.
"""
from langgraph.graph import StateGraph, START, END
from app.agents.state import AgentState
from app.agents.parser import parser_agent
from app.agents.summarizer import summarizer_agent
from app.agents.planner import planner_agent


def build_pipeline():
    """
    Build the agent pipeline.
    
    Current structure:
        START → parser → summarizer → planner → END
    
    Future structure:
        START → parser → summarizer → planner → writer → builder → END
    """
    graph = StateGraph(AgentState)
    
    # Register nodes
    graph.add_node("parser", parser_agent)
    graph.add_node("summarizer", summarizer_agent)
    graph.add_node("planner", planner_agent)
    
    # Define flow
    graph.add_edge(START, "parser")
    graph.add_edge("parser", "summarizer")
    graph.add_edge("summarizer", "planner")
    graph.add_edge("planner", END)
    
    return graph.compile()


# Build once at import time
pipeline = build_pipeline()


# ── Manual test entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else "test.pdf"
    
    # Allow overriding via command line: python -m app.agents.graph <pdf> <audience> <count>
    audience = sys.argv[2] if len(sys.argv) > 2 else "student"
    slide_count = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    initial_state: AgentState = {
        "pdf_path": pdf_file,
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
    
    print("=" * 70)
    print("🚀 Starting Doc2Slides pipeline")
    print("=" * 70)
    
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
        
        # Print summaries if the Summarizer ran
        if final_state.get("section_summaries"):
            print(f"\n" + "=" * 70)
            print("📝 Section Summaries (first 3)")
            print("=" * 70)
            for section in doc.sections[:3]:
                summary = final_state["section_summaries"].get(section.id, "N/A")
                print(f"\n[{section.id}] {section.heading}")
                print(f"  → {summary}")
        
        # Print slide plan if the Planner ran
        if final_state.get("slide_plan"):
            plan = final_state["slide_plan"]
            print(f"\n" + "=" * 70)
            print(f"🎯 Slide Plan (audience: {plan['audience']})")
            print("=" * 70)
            for slide in plan["slides"]:
                sources = ", ".join(slide["sources"]) if slide["sources"] else "-"
                print(f"\n  Slide {slide['index']} [{slide['type']}]: {slide['title']}")
                print(f"    Theme: {slide['theme']}")
                print(f"    Sources: {sources}")
    else:
        print("No document parsed — check errors above.")