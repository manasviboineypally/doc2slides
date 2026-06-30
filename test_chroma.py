"""
Day 6 sanity check — index a real PDF and search it.
"""
from app.agents.graph import pipeline
from app.agents.state import AgentState
from app.vectorstore.chroma import index_document, search


# Step 1: Parse the PDF using our existing pipeline
print("=" * 70)
print("📄 Parsing test.pdf via the LangGraph pipeline...")
print("=" * 70)

initial_state: AgentState = {
    "pdf_path": "test.pdf",
    "audience": "student",
    "slide_count": 10,
    "parsed_doc": None,
    "section_summaries": None,
    "slide_plan": None,
    "written_slides": None,
    "output_path": None,
    "errors": [],
    "current_step": "starting",
}

final_state = pipeline.invoke(initial_state)
doc = final_state["parsed_doc"]
print(f"✅ Got {doc.metadata.total_sections} sections, {doc.total_words()} words")


# Step 2: Index it into ChromaDB
print("\n" + "=" * 70)
print("📦 Indexing into ChromaDB (chunking + embedding)...")
print("=" * 70)
print("⏳ First run downloads the embedding model (~80MB) — be patient")

stats = index_document(doc)
print(f"✅ Indexed {stats['total_chunks']} chunks across {len(stats['chunks_per_section'])} sections")
print("\nChunks per section:")
for sec_id, count in stats["chunks_per_section"].items():
    print(f"  {sec_id}: {count} chunks")


# Step 3: Try some semantic searches
print("\n" + "=" * 70)
print("🔍 Testing semantic search")
print("=" * 70)

queries = [
    "what is term rewriting?",
    "how does refinement calculus work?",
    "what does the paper conclude?",
]

for query in queries:
    print(f"\n❓ Query: '{query}'")
    results = search(query, source_file="test.pdf", top_k=2)
    for i, r in enumerate(results, 1):
        print(f"\n  [{i}] From {r['metadata']['section_heading']} (page {r['metadata']['page']})")
        print(f"      Distance: {r['distance']:.3f}  (lower = more similar)")
        print(f"      Preview: {r['text'][:200]}...")

print("\n" + "=" * 70)
print("🎉 Day 6 complete — RAG search working!")
print("=" * 70)