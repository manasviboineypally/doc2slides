"""
Writer agent — turns slide plans into actual slide content.

Reads:  state["slide_plan"], state["section_summaries"], state["parsed_doc"], state["audience"]
Writes: state["written_slides"], state["current_step"]

For each slide in the plan:
1. Look up the sources referenced in the plan
2. Build a focused prompt with plan intent + source content
3. Ask GPT for structured slide content (title + bullets + speaker notes)
4. Validate with Pydantic

Uses gpt-4o-mini with JSON mode for reliable structured output.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from app.agents.state import AgentState
from app.schemas.slide import Slide, WrittenDeck

PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise RuntimeError("OPENAI_API_KEY not found in .env")

_client = OpenAI(api_key=_api_key)
MODEL_NAME = "gpt-4o-mini"


WRITER_PROMPT = """You are writing slide content for a presentation.

AUDIENCE: {audience}
SLIDE INDEX: {index}
SLIDE TYPE: {slide_type}
INTENDED TITLE: {title}
THEME (what this slide should convey): {theme}

SOURCE MATERIAL from the paper:
---
{source_content}
---

Write this slide's content for a {audience} audience.

Guidelines by audience:
- kid: Use simple words, concrete analogies, short bullets (4-8 words each)
- student: Educational tone, clear technical terms with brief definitions
- engineer: Precise technical language, assume domain knowledge
- executive: Business framing, focus on impact and takeaways, no jargon

Return ONLY valid JSON matching this exact schema:
{{
  "title": "polished slide title (may improve on the intended title)",
  "bullets": [
    "First bullet point — short and focused",
    "Second bullet point",
    "Third bullet point"
  ],
  "speaker_notes": "1-3 sentences the presenter can use to introduce or expand on this slide"
}}

Rules:
- Include 3-5 bullets (never more, never fewer)
- Each bullet: 5-15 words max
- Speaker notes: 1-3 sentences
- No markdown formatting in bullets (no ** or #)
- Return ONLY the JSON object, no code fences or commentary
"""


def write_slide(
    audience: str,
    plan_slide: dict,
    source_content: str,
) -> Slide:
    """Ask GPT to write one slide's content, then validate with Pydantic."""
    prompt = WRITER_PROMPT.format(
        audience=audience,
        index=plan_slide["index"],
        slide_type=plan_slide["type"],
        title=plan_slide["title"],
        theme=plan_slide["theme"],
        source_content=source_content or "[no source content available]",
    )
    
    response = _client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    
    raw_json = response.choices[0].message.content
    parsed = json.loads(raw_json)
    
    return Slide(
        index=plan_slide["index"],
        title=parsed["title"],
        bullets=parsed.get("bullets", []),
        speaker_notes=parsed.get("speaker_notes"),
    )


def build_source_content(
    plan_slide: dict,
    doc,
    summaries: dict,
) -> str:
    """Combine the summaries and section content referenced by this slide's plan."""
    sources = plan_slide.get("sources", [])
    if not sources:
        return ""
    
    # Build a mapping of section_id → Section for quick lookup
    section_by_id = {s.id: s for s in doc.sections}
    
    blocks = []
    for sec_id in sources:
        section = section_by_id.get(sec_id)
        summary = summaries.get(sec_id, "")
        if section:
            # Include the summary + a snippet of the raw section content
            snippet = section.content[:1500]
            blocks.append(
                f"Section: {section.heading}\n"
                f"Summary: {summary}\n"
                f"Content excerpt: {snippet}"
            )
        elif summary:
            blocks.append(f"Section {sec_id}: {summary}")
    
    return "\n\n---\n\n".join(blocks)


def writer_agent(state: AgentState) -> dict:
    """
    Writer node. Turns each plan slide into fully-written slide content.
    """
    plan = state.get("slide_plan")
    doc = state.get("parsed_doc")
    summaries = state.get("section_summaries", {})
    audience = state["audience"]
    
    if not plan or not doc:
        return {
            "errors": state.get("errors", []) + ["Writer: missing slide_plan or parsed_doc"],
            "current_step": "writer_failed",
        }
    
    plan_slides = plan["slides"]
    print(f"✍️  [Writer] Writing content for {len(plan_slides)} slides...")
    
    written = []
    for i, plan_slide in enumerate(plan_slides, start=1):
        source_content = build_source_content(plan_slide, doc, summaries)
        print(f"   [{i}/{len(plan_slides)}] Writing slide {plan_slide['index']}: {plan_slide['title'][:50]}...")
        try:
            slide = write_slide(audience, plan_slide, source_content)
            written.append(slide.model_dump())
        except Exception as e:
            print(f"   ⚠️  Failed on slide {plan_slide['index']}: {e}")
            # Fallback: use the plan info as a stub slide
            written.append({
                "index": plan_slide["index"],
                "title": plan_slide["title"],
                "bullets": [plan_slide["theme"]],
                "speaker_notes": f"[Writer failed] {e}",
            })
    
    print(f"✅ [Writer] Wrote {len(written)} slides")
    
    return {
        "written_slides": written,
        "current_step": "writer_complete",
    }