"""
Parser eval — measures how well the Parser matches ground truth.

Runs the Parser on each test PDF, compares detected sections against
expected sections in evals/datasets/*_expected.json.

Scores:
- Section count within expected range
- Heading text contains expected keyword
- Content contains required keywords
"""
import json
from pathlib import Path
from app.parser.sections import detect_sections, filter_real_sections, build_document

EVAL_DIR = Path(__file__).parent
DATASETS_DIR = EVAL_DIR / "datasets"


def eval_test_pdf() -> dict:
    """Evaluate parsing of test.pdf against strict ground truth."""
    with open(DATASETS_DIR / "test_expected.json") as f:
        expected = json.load(f)
    
    pdf_path = Path("test.pdf")
    if not pdf_path.exists():
        return {"error": "test.pdf not found"}
    
    # Parse
    raw = detect_sections(str(pdf_path))
    filtered = filter_real_sections(raw)
    doc = build_document(str(pdf_path), filtered)
    
    results = {
        "pdf": expected["source_file"],
        "total_sections": len(doc.sections),
        "checks": [],
        "score": 0,
        "max_score": 0,
    }
    
    # Check 1: Section count matches
    exp_count = len(expected["expected_sections"])
    check = {
        "check": f"Section count: expected {exp_count}, got {len(doc.sections)}",
        "passed": len(doc.sections) >= expected["min_sections"],
    }
    results["checks"].append(check)
    results["max_score"] += 1
    if check["passed"]: results["score"] += 1
    
    # Check 2: Each expected section is present
    for exp in expected["expected_sections"]:
        # Find a real section whose heading or content contains the expected keyword
        keyword = exp["heading_contains"].lower()
        matches = [
            s for s in doc.sections
            if keyword in s.heading.lower() or keyword in s.content[:200].lower()
        ]
        
        check = {
            "check": f"Section with '{exp['heading_contains']}' present",
            "passed": len(matches) > 0,
        }
        results["checks"].append(check)
        results["max_score"] += 1
        if check["passed"]: results["score"] += 1
        
        # Check content keywords
        if matches:
            best_match = matches[0]
            for kw in exp["must_contain_keywords"]:
                found = kw.lower() in best_match.content.lower()
                check = {
                    "check": f"  '{kw}' found in {exp['id']} content",
                    "passed": found,
                }
                results["checks"].append(check)
                results["max_score"] += 1
                if check["passed"]: results["score"] += 1
    
    return results


def eval_paper2_pdf() -> dict:
    """Evaluate parsing of paper2.pdf against looser ground truth."""
    with open(DATASETS_DIR / "paper2_expected.json") as f:
        expected = json.load(f)
    
    pdf_path = Path("paper2.pdf")
    if not pdf_path.exists():
        return {"error": "paper2.pdf not found"}
    
    raw = detect_sections(str(pdf_path))
    filtered = filter_real_sections(raw)
    doc = build_document(str(pdf_path), filtered)
    
    results = {
        "pdf": expected["source_file"],
        "total_sections": len(doc.sections),
        "checks": [],
        "score": 0,
        "max_score": 0,
    }
    
    # Check 1: minimum section count
    check = {
        "check": f"At least {expected['expected_sections_min']} sections",
        "passed": len(doc.sections) >= expected["expected_sections_min"],
    }
    results["checks"].append(check)
    results["max_score"] += 1
    if check["passed"]: results["score"] += 1
    
    # Check 2: expected headings present (fuzzy match)
    all_text = " ".join(s.heading + " " + s.content[:300] for s in doc.sections).lower()
    for heading in expected["expected_headings_include"]:
        check = {
            "check": f"Heading or content mentions '{heading}'",
            "passed": heading.lower() in all_text,
        }
        results["checks"].append(check)
        results["max_score"] += 1
        if check["passed"]: results["score"] += 1
    
    # Check 3: overall keywords present
    for kw in expected["must_contain_keywords_overall"]:
        check = {
            "check": f"Overall content mentions '{kw}'",
            "passed": kw.lower() in all_text,
        }
        results["checks"].append(check)
        results["max_score"] += 1
        if check["passed"]: results["score"] += 1
    
    return results


def print_results(results: dict):
    """Print eval results in a readable format."""
    if "error" in results:
        print(f"❌ {results['error']}")
        return
    
    print(f"\n📄 {results['pdf']}")
    print(f"   Detected {results['total_sections']} sections")
    print(f"   Score: {results['score']}/{results['max_score']} "
          f"({100 * results['score'] // max(results['max_score'], 1)}%)")
    
    for check in results["checks"]:
        icon = "✅" if check["passed"] else "❌"
        print(f"   {icon} {check['check']}")


if __name__ == "__main__":
    print("=" * 70)
    print("🧪 PARSER EVALUATION")
    print("=" * 70)
    
    r1 = eval_test_pdf()
    print_results(r1)
    
    r2 = eval_paper2_pdf()
    print_results(r2)
    
    print("\n" + "=" * 70)
    total_score = r1.get("score", 0) + r2.get("score", 0)
    total_max = r1.get("max_score", 0) + r2.get("max_score", 0)
    if total_max > 0:
        pct = 100 * total_score // total_max
        print(f"OVERALL PARSER SCORE: {total_score}/{total_max} ({pct}%)")
    print("=" * 70)