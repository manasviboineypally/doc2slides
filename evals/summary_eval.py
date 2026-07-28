"""
Summarizer eval — uses GPT as a judge to score summary quality.

For each section, retrieves the summary, then asks GPT to score:
- Faithfulness (does the summary match the source content?)
- Completeness (does it cover key points?)
- Clarity (is it clear and coherent?)

Each score is 1-5. Higher is better.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from app.parser.sections import detect_sections, filter_real_sections, build_document
from app.agents.summarizer import summarizer_agent
from app.agents.state import AgentState

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
JUDGE_MODEL = "gpt-4o-mini"


JUDGE_PROMPT = """You are evaluating a summary of a section from a research paper.

ORIGINAL SECTION HEADING: {heading}

ORIGINAL SECTION CONTENT (excerpt):
---
{content}
---

GENERATED SUMMARY:
---
{summary}
---

Score the summary on three dimensions, each from 1 to 5:

1. FAITHFULNESS — Does the summary accurately represent the source? 
   5 = perfectly faithful, no fabricated claims
   3 = mostly accurate with minor drift
   1 = contains false or unrelated claims

2. COMPLETENESS — Does it capture the key ideas?
   5 = all major points captured
   3 = most major points, some missed
   1 = misses core message

3. CLARITY — Is it clear and well-written?
   5 = crisp, coherent, easy to read
   3 = readable but awkward
   1 = confusing or fragmented

Return ONLY valid JSON in this exact format:
{{"faithfulness": N, "completeness": N, "clarity": N, "brief_reason": "one sentence why"}}
"""


def score_summary(heading: str, content: str, summary: str) -> dict:
    """Ask GPT to score one summary. Returns dict with scores."""
    prompt = JUDGE_PROMPT.format(heading=heading, content=content[:2000], summary=summary)
    response = _client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def eval_summaries(pdf_name: str) -> dict:
    """Generate summaries for all sections and score each with LLM-as-judge."""
    pdf_path = Path(pdf_name)
    if not pdf_path.exists():
        return {"error": f"{pdf_name} not found"}
    
    print(f"\n🔬 Evaluating summaries for {pdf_name}...")
    
    # Parse
    raw = detect_sections(str(pdf_path))
    filtered = filter_real_sections(raw)
    doc = build_document(str(pdf_path), filtered)
    
    # Generate summaries
    state: AgentState = {
        "pdf_path": str(pdf_path),
        "audience": "student",
        "slide_count": 10,
        "parsed_doc": doc,
        "section_summaries": None,
        "slide_plan": None,
        "written_slides": None,
        "output_path": None,
        "errors": [],
        "current_step": "starting",
    }
    result = summarizer_agent(state)
    summaries = result.get("section_summaries", {})
    
    # Score each section
    results = {
        "pdf": pdf_name,
        "sections_scored": 0,
        "faithfulness_avg": 0,
        "completeness_avg": 0,
        "clarity_avg": 0,
        "details": [],
    }
    
    total_faith = total_complete = total_clarity = 0
    
    for section in doc.sections:
        summary = summaries.get(section.id)
        if not summary:
            continue
        
        print(f"   Scoring {section.id}: {section.heading[:50]}...")
        try:
            scores = score_summary(section.heading, section.content, summary)
            
            faith = scores.get("faithfulness", 0)
            complete = scores.get("completeness", 0)
            clarity = scores.get("clarity", 0)
            
            total_faith += faith
            total_complete += complete
            total_clarity += clarity
            
            results["details"].append({
                "section_id": section.id,
                "heading": section.heading,
                "faithfulness": faith,
                "completeness": complete,
                "clarity": clarity,
                "reason": scores.get("brief_reason", ""),
            })
            results["sections_scored"] += 1
        except Exception as e:
            print(f"   ⚠️  Failed to score {section.id}: {e}")
    
    n = max(results["sections_scored"], 1)
    results["faithfulness_avg"] = round(total_faith / n, 2)
    results["completeness_avg"] = round(total_complete / n, 2)
    results["clarity_avg"] = round(total_clarity / n, 2)
    
    return results


def print_results(results: dict):
    if "error" in results:
        print(f"❌ {results['error']}")
        return
    
    print(f"\n📄 {results['pdf']}")
    print(f"   Sections scored: {results['sections_scored']}")
    print(f"   Faithfulness: {results['faithfulness_avg']}/5")
    print(f"   Completeness: {results['completeness_avg']}/5")
    print(f"   Clarity:      {results['clarity_avg']}/5")
    
    print("\n   Per-section scores:")
    for d in results["details"]:
        print(f"   [{d['section_id']}] {d['heading'][:40]:40s} "
              f"F:{d['faithfulness']} C:{d['completeness']} L:{d['clarity']}")
        if d.get("reason"):
            print(f"       → {d['reason']}")


if __name__ == "__main__":
    print("=" * 70)
    print("🎯 SUMMARIZER EVALUATION (LLM-as-judge)")
    print("=" * 70)
    print("This runs slowly — 1 GPT call per section per PDF.")
    
    r1 = eval_summaries("test.pdf")
    print_results(r1)
    
    print("\n" + "=" * 70)
    print("Summary evaluation done.")
    print("=" * 70)