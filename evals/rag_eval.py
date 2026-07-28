"""
RAG eval — measures if ChromaDB retrieves the right chunks for known queries.

Loads each test PDF, indexes it into ChromaDB, then runs the queries from
the ground truth files. Checks whether the top-K results include a chunk
from the expected section.

Scores:
- Top-1 precision: was the FIRST result from the expected section?
- Top-3 precision: was ANY of the top 3 results from the expected section?
"""
import json
from pathlib import Path
from app.parser.sections import detect_sections, filter_real_sections, build_document
from app.vectorstore.chroma import index_document, search

EVAL_DIR = Path(__file__).parent
DATASETS_DIR = EVAL_DIR / "datasets"


def eval_rag_for_pdf(pdf_name: str, dataset_name: str) -> dict:
    """Run all RAG queries for one PDF against expected sections."""
    with open(DATASETS_DIR / dataset_name) as f:
        expected = json.load(f)
    
    pdf_path = Path(pdf_name)
    if not pdf_path.exists():
        return {"error": f"{pdf_name} not found"}
    
    # Parse + index
    raw = detect_sections(str(pdf_path))
    filtered = filter_real_sections(raw)
    doc = build_document(str(pdf_path), filtered)
    index_document(doc)
    
    queries = expected.get("rag_queries", [])
    
    results = {
        "pdf": pdf_name,
        "total_queries": len(queries),
        "top1_hits": 0,
        "top3_hits": 0,
        "details": [],
    }
    
    for q in queries:
        query_text = q["query"]
        expected_id = q.get("expected_section_id")
        expected_heading = q.get("expected_heading_contains", "").lower()
        
        # Retrieve top 3
        hits = search(query_text, source_file=str(pdf_path), top_k=3)
        
        # Check top-1
        top1_match = False
        if hits:
            top_meta = hits[0]["metadata"]
            if expected_id and top_meta.get("section_id") == expected_id:
                top1_match = True
            elif expected_heading and expected_heading in top_meta.get("section_heading", "").lower():
                top1_match = True
        
        # Check top-3
        top3_match = False
        for hit in hits:
            meta = hit["metadata"]
            if expected_id and meta.get("section_id") == expected_id:
                top3_match = True
                break
            if expected_heading and expected_heading in meta.get("section_heading", "").lower():
                top3_match = True
                break
        
        if top1_match: results["top1_hits"] += 1
        if top3_match: results["top3_hits"] += 1
        
        results["details"].append({
            "query": query_text,
            "expected": expected_id or expected_heading,
            "top1_match": top1_match,
            "top3_match": top3_match,
            "top_result_heading": hits[0]["metadata"].get("section_heading", "-") if hits else "-",
            "top_distance": round(hits[0]["distance"], 3) if hits else -1,
        })
    
    return results


def print_results(results: dict):
    if "error" in results:
        print(f"❌ {results['error']}")
        return
    
    total = results["total_queries"]
    top1_pct = (100 * results["top1_hits"] // total) if total else 0
    top3_pct = (100 * results["top3_hits"] // total) if total else 0
    
    print(f"\n📄 {results['pdf']}")
    print(f"   Queries: {total}")
    print(f"   Top-1 precision: {results['top1_hits']}/{total} ({top1_pct}%)")
    print(f"   Top-3 precision: {results['top3_hits']}/{total} ({top3_pct}%)")
    
    for d in results["details"]:
        top1_icon = "✅" if d["top1_match"] else "❌"
        top3_icon = "✅" if d["top3_match"] else "❌"
        print(f"\n   Query: '{d['query']}'")
        print(f"     Expected: {d['expected']}")
        print(f"     Top result: {d['top_result_heading']} (dist: {d['top_distance']})")
        print(f"     Top-1: {top1_icon}  |  Top-3: {top3_icon}")


if __name__ == "__main__":
    print("=" * 70)
    print("🔍 RAG RETRIEVAL EVALUATION")
    print("=" * 70)
    
    r1 = eval_rag_for_pdf("test.pdf", "test_expected.json")
    print_results(r1)
    
    r2 = eval_rag_for_pdf("paper2.pdf", "paper2_expected.json")
    print_results(r2)
    
    print("\n" + "=" * 70)
    total_queries = r1.get("total_queries", 0) + r2.get("total_queries", 0)
    total_top1 = r1.get("top1_hits", 0) + r2.get("top1_hits", 0)
    total_top3 = r1.get("top3_hits", 0) + r2.get("top3_hits", 0)
    if total_queries > 0:
        top1_pct = 100 * total_top1 // total_queries
        top3_pct = 100 * total_top3 // total_queries
        print(f"OVERALL RAG SCORES:")
        print(f"  Top-1 precision: {total_top1}/{total_queries} ({top1_pct}%)")
        print(f"  Top-3 precision: {total_top3}/{total_queries} ({top3_pct}%)")
    print("=" * 70)