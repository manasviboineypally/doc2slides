## Progress log

### Pydantic data models
- Section, DocumentMetadata, ParsedDocument typed and validated
- Parser refactored to return ParsedDocument instead of dicts
- Auto-correct logic handles "Abstract" vs "Abstract Interpretation" disambiguation via AMBIGUOUS_PHRASES list
- Tradeoff accepted: stricter matching would miss more abstracts than it gains; looser matching creates false positives. Current logic picks the safer side.

### LangGraph orchestration
- Parser wrapped as first node in a StateGraph
- Shared AgentState (TypedDict) ready for future agents
- Successfully invoked on test.pdf and paper2.pdf via `python -m app.agents.graph`
- Notes: Adding new agents is now a 2-line change to graph.py

### HTTP API
- FastAPI endpoint `POST /jobs/` accepts PDF uploads
- Interactive Swagger UI auto-generated at `/docs`
- Pipeline runs synchronously per request (async upgrade planned)
- Verified end-to-end: test.pdf → 9 sections returned as clean JSON
- Uploaded files stay in `uploads/` between requests (no cleanup yet)
- No job persistence — each request is independent (PostgreSQL planned)

### ChromaDB vector store
- Installed ChromaDB with persistent storage
- Built chunk_text() with 500-word chunks and 50-word overlap
- Built index_document() to chunk, embed, and store sections
- Built search() with semantic similarity + metadata filtering
- Verified end-to-end: semantic search returns topic-relevant chunks
- Uses default all-MiniLM-L6-v2 embedding model (auto-downloaded ~80MB)

### Summarizer agent
- Attempted Gemini integration, hit account-specific 401 UNAUTHENTICATED errors
- Switched to OpenAI gpt-4o-mini after extensive Gemini debugging
- Built Summarizer agent using RAG retrieval + LLM prompt
- Wired into LangGraph as second node (parser → summarizer → END)
- Tested on test.pdf (9 summaries) and paper2.pdf (16 summaries)
- Confirmed real cost: 18 API calls = $0.002 total spend
- Notes: Clean architecture made LLM provider swap a 5-line change in summarizer.py