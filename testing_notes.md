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


### Planner agent
- Built with OpenAI gpt-4o-mini using JSON mode + Pydantic validation
- Two-layer structured output: `response_format={"type": "json_object"}` guarantees valid JSON, Pydantic guarantees correct schema
- Wired into LangGraph as third node (parser → summarizer → planner → END)
- API endpoint accepts audience (kid/student/engineer/executive) and slide_count (5/10/15)
- Verified different audiences produce meaningfully different plans (e.g., "Fun with Compilers!" for kid vs "Advancements in Compiler Design: Leveraging Formal Theories" for executive)
- Observation: highly technical papers limit how simple even "kid" plans can be — Writer agent will need strong analogy generation

### Writer agent
- Built with OpenAI gpt-4o-mini + JSON mode + Pydantic validation (Slide, WrittenDeck)
- Reads slide_plan + section_summaries + parsed_doc; writes structured slide content
- Each slide: title, 3-5 bullets (5-15 words each), 1-3 sentence speaker notes
- Audience-adaptive prompts (kid/student/engineer/executive)
- Fallback stub-slide on failure so pipeline never breaks completely
- Verified: same paper produces meaningfully different slide content per audience
  - Kid: "Like magic spells for computers"
  - Student: "Term rewriting uses rules to transform expressions"

### Builder agent + HTTP download endpoint
- Uses python-pptx to generate real editable PowerPoint files
- Title slide + one slide per written entry (title + bullets + speaker notes)
- Output saved to outputs/ (gitignored) with format {job_id}_{doc}_{audience}_{count}slides.pptx
- New GET /jobs/download/{filename} endpoint serves generated files with proper MIME type
- Verified end-to-end HTTP flow: upload via Swagger → pipeline runs → download URL returned → file downloads → opens correctly in PowerPoint


### Design choice: Slide count and content density

The Planner respects the user's requested slide count exactly. This is a
deliberate design choice — users have real constraints (presentation time
slots, class rules, executive attention spans) and silent AI overrides
break user trust.

**Tradeoff:** when the paper's actual content density doesn't match the
requested slide count, the LLM may pad shallow sections or compress dense
ones. This creates mild redundancy at high slide counts (e.g., 15 slides
from a 9-section paper occasionally produces meta-slides like "References"
or overlapping topic slides).

**Rejected quick fix:** using section word count as a proxy for content
density. Word count is not density — a short section may contain multiple
distinct ideas while a long section may ramble around one idea.

**Proper solution deferred:** content-aware slide allocation with LLM
judgment, verified by an evaluation harness that measures output quality
against ground truth. Requires infrastructure work not appropriate for the
initial version.

**Current approach:** ship with predictable user control, document the
tradeoff honestly, revisit with real user feedback and eval infrastructure.


### Async job processing

Refactored `POST /jobs/` to return immediately (~1 second) with a job_id
instead of blocking for 60-90 seconds while the pipeline runs. Uses FastAPI
BackgroundTasks with a simple in-memory job store (dict).

Flow:
- POST /jobs/ → returns { job_id, status: "pending" } immediately
- Pipeline runs in background thread (Parser → Summarizer → Planner → Writer → Builder)
- GET /jobs/{job_id} → returns current status ("pending" → "processing" → "completed" or "failed")
- GET /jobs/download/{filename} → serves the .pptx once completed

Verified end-to-end: response time on POST is ~1s (was 60-90s). Timestamps
show pipeline runs asynchronously — created_at and started_at within 10ms,
completed_at 42 seconds later.

Known limitation: in-memory job store means jobs disappear on server
restart. PostgreSQL persistence is next.




### Evaluation harness (planned)
- Parser: section detection precision/recall against ground truth
- RAG: retrieval precision@K on hand-labeled query→chunk pairs
- Summarizer: LLM-as-judge scoring on faithfulness, completeness, clarity