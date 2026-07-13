"""
Planner agent — decides the slide structure for the deck.

Reads:  state["parsed_doc"], state["section_summaries"], state["audience"], state["slide_count"]
Writes: state["slide_plan"], state["current_step"]

Uses GPT with strict JSON output to produce a validated DeckPlan.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from app.agents.state import AgentState
from app.schemas.plan import DeckPlan, SlidePlan

# Load .env from the project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise RuntimeError("OPENAI_API_KEY not found in .env")

_client = OpenAI(api_key=_api_key)
MODEL_NAME = "gpt-4o-mini"


PLANNER_PROMPT = """You are a presentation designer creating a slide deck plan.

DOCUMENT: {doc_title}
AUDIENCE: {audience}
TARGET SLIDE COUNT: {slide_count}

The document has these sections with brief summaries:
{sections_block}

Design a slide plan with exactly {slide_count} slides that:
1. Opens with a title slide (type: "title")
2. Progresses logically through the ideas
3. Ends with a conclusion slide (type: "conclusion")
4. Uses appropriate slide types: title, context, concept, example, comparison, conclusion
5. Draws content from the section summaries (reference section IDs like "sec_1", "sec_3")
6. Adapts tone/depth for the {audience} audience

Return ONLY valid JSON matching this exact schema:
{{
  "slides": [
    {{
      "index": 1,
      "type": "title",
      "title": "short slide title",
      "theme": "what this slide should convey",
      "sources": ["sec_id_1", "sec_id_2"]
    }},
    ...
  ]
}}

The response MUST be valid JSON — no markdown code fences, no commentary, just the JSON object.
"""


def plan_slides(doc_title: str, sections_block: str, audience: str, slide_count: int) -> DeckPlan:
    """Ask GPT to design a slide plan, then validate it with Pydantic."""
    prompt = PLANNER_PROMPT.format(
        doc_title=doc_title,
        sections_block=sections_block,
        audience=audience,
        slide_count=slide_count,
    )
    
    # Use response_format to force JSON output
    response = _client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    
    # Parse GPT's response
    raw_json = response.choices[0].message.content
    parsed = json.loads(raw_json)
    
    # Validate with Pydantic — errors here mean GPT returned bad structure
    slides = [SlidePlan(**s) for s in parsed["slides"]]
    
    return DeckPlan(
        audience=audience,
        total_slides=len(slides),
        slides=slides,
    )


def planner_agent(state: AgentState) -> dict:
    """
    Planner node. Uses GPT to design a slide deck plan from section summaries.
    """
    doc = state["parsed_doc"]
    summaries = state.get("section_summaries", {})
    audience = state["audience"]
    slide_count = state["slide_count"]
    
    if doc is None or not summaries:
        return {
            "errors": state.get("errors", []) + ["Planner: missing parsed_doc or summaries"],
            "current_step": "planner_failed",
        }
    
    print(f"📋 [Planner] Designing {slide_count} slides for audience: {audience}")
    
    # Build the sections block — each section with its ID, heading, and summary
    lines = []
    for section in doc.sections:
        summary = summaries.get(section.id, "[no summary]")
        lines.append(f"- {section.id} ({section.heading}): {summary}")
    sections_block = "\n".join(lines)
    
    # Use the source filename as the doc title fallback
    doc_title = Path(doc.source_file).stem
    
    try:
        plan = plan_slides(doc_title, sections_block, audience, slide_count)
        print(f"✅ [Planner] Generated plan with {plan.total_slides} slides")
        # Convert to dict for storage in state (avoids Pydantic serialization gotchas)
        return {
            "slide_plan": plan.model_dump(),
            "current_step": "planner_complete",
        }
    except Exception as e:
        error_msg = f"Planner failed: {type(e).__name__}: {e}"
        print(f"❌ [Planner] {error_msg}")
        return {
            "slide_plan": None,
            "errors": state.get("errors", []) + [error_msg],
            "current_step": "planner_failed",
        }