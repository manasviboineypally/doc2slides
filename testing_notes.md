# Doc2Slides — Parser Testing Notes

Tracking what works, what breaks, and why. Updated as the project evolves.

---

## test.pdf — Reading Model Compilation Through the Lens of Formal Theories
**Type:** Single-column arxiv paper (cs.PL, 2026)

- ✅ Detected 9 real sections after filtering
- ✅ Body font auto-detected as 10.0
- ✅ Abstract, Introduction, all numbered sections, Conclusion, References — all captured
- ⚠️ Abstract heading initially detected as just "A" (drop-cap issue) — fixed via content-keyword filter
- ⚠️ Title scrambled across columns (multi-position title text)
- **Verdict:** Works as designed

---

## paper2.pdf — Vulnerability of Natural Language Classifiers (GAversary)
**Type:** Single-column arxiv paper (cs.AI, 2026)

- ✅ Detected 16 sections including sub-sections (3.1, 3.2, ..., 4.4)
- ✅ Body font auto-detected as 10.9 (different from test.pdf)
- ✅ Hierarchical structure preserved
- ⚠️ Multi-line affiliation block hides the abstract section behind the affiliation line — content captured, only label is wrong
- **Verdict:** Generalized to a different paper without modification

---

## column.pdf — 2001 IEEE conference paper (New Faculty 101)
**Type:** Double-column IEEE format

- ❌ Two-column layout breaks content extraction
- ❌ Drop-cap section headings confuse detector
- ❌ Body text from left and right columns gets interleaved
- ✅ Parser doesn't crash — fails gracefully with weird output
- **Verdict:** Known limitation. Future work: column-aware text extraction.

---

## Known limitations

1. **Double-column PDFs** — text from adjacent columns gets jumbled. Affects IEEE, ACM, older Nature/Science papers.
2. **Title detection on arxiv** — title spans page width with rotated arxiv ID; gets scrambled.
3. **Decorative drop-caps** — first letter of section splits from body. Partial fix via content-keyword filter.
4. **Heading inference** — relies on font size as primary signal. Documents with weak typographic hierarchy may not produce clean sections.
5. **Affiliation blocks** — first section can appear under affiliation heading instead of "Abstract". Content captured correctly; label cosmetic.

---

## Progress log

### Pydantic data models
- Section, DocumentMetadata, ParsedDocument typed and validated
- Parser refactored to return ParsedDocument instead of dicts
- Auto-correct logic handles "Abstract" vs "Abstract Interpretation" disambiguation via AMBIGUOUS_PHRASES list

### LangGraph orchestration
- Parser wrapped as first node in a StateGraph
- Shared AgentState (TypedDict) ready for future agents
- Successfully invoked on test.pdf and paper2.pdf
- Adding new agents is now a 2-line change to graph.py

### HTTP API
- FastAPI endpoint `POST /jobs/` accepts PDF uploads
- Interactive Swagger UI at `/docs`
- Verified end-to-end via HTTP flow

### ChromaDB vector store
- Chunk size 500 words, overlap 50 words
- Uses default all-MiniLM-L6-v2 embedding model (~80 MB auto-download)
- Semantic search with metadata filtering by source_file

### Summarizer agent
- Attempted Gemini integration first; hit account-specific 401 UNAUTHENTICATED errors
- Switched to OpenAI gpt-4o-mini
- Clean architecture made LLM provider swap a 5-line change
- Real cost verified: 18 API calls = ~$0.002 total

### Planner agent
- OpenAI gpt-4o-mini with JSON mode + Pydantic validation
- Two-layer structured output: JSON mode guarantees valid JSON, Pydantic guarantees correct schema
- Wired into LangGraph as third node
- Verified different audiences produce meaningfully different plans

### Writer agent
- Audience-adaptive prompts (kid/student/engineer/executive)
- Each slide: title, 3-5 bullets (5-15 words each), 1-3 sentence speaker notes
- Fallback stub-slide on failure so pipeline never breaks completely

### Builder agent + HTTP download endpoint
- Uses python-pptx to generate real editable PowerPoint files
- Title slide + one slide per written entry (title + bullets + speaker notes)
- Output saved to outputs/ (gitignored) with format {job_id}_{doc}_{audience}_{count}slides.pptx
- GET /jobs/download/{filename} endpoint serves generated files with proper MIME type

### Design choice: Slide count and content density

The Planner respects the user's requested slide count exactly. Deliberate choice — users have real constraints and silent AI overrides break trust.

Tradeoff: when the paper's actual content density doesn't match the requested slide count, the LLM may pad shallow sections or compress dense ones.

Rejected quick fix: using section word count as a proxy for content density. Word count is not density — a short section may contain multiple distinct ideas while a long section may ramble around one.

Proper solution deferred: content-aware slide allocation with LLM judgment, verified by an evaluation harness. Requires infrastructure not appropriate for the initial version.

### Async job processing
- Refactored POST /jobs/ to return immediately (~1s) with a job_id instead of blocking for 60-90s
- Uses FastAPI BackgroundTasks with an in-memory job store (dict)
- Verified: created_at and started_at timestamps within 10ms, completed_at 42s later
- Known limitation at the time: in-memory job store meant jobs disappeared on server restart

### PostgreSQL persistence
- Replaced in-memory dict-based job_store with SQLAlchemy + PostgreSQL
- Job model in app/db/models.py
- Session management in app/db/session.py
- Repository pattern in app/api/job_store.py (create/get/update/all_jobs)
- Database URL from environment (DATABASE_URL in .env)
- Verified: server can be restarted mid-session, previously created jobs remain queryable
- Design decision: env-driven database URL means SQLite dev → PostgreSQL prod is a one-line change

### HTML UI
- Modern dark-themed single-page frontend at static/index.html
- Drag-and-drop file upload with file info preview
- Visual audience cards (kid/student/engineer/executive)
- Free number input for slide count (3-50)
- Real-time job polling every 2 seconds with animated progress bar
- Status badges with color coding
- Chose vanilla HTML/CSS/JS over React: zero build step, portable, transparent

### Evaluation harness

Three eval strategies matching pipeline stages:

**Parser evals** (`evals/parser_eval.py`)
- Ground truth in `evals/datasets/*_expected.json`
- Hard assertions: section count, heading presence, content keywords
- Result: 100% (34/34) on test.pdf + paper2.pdf

**RAG evals** (`evals/rag_eval.py`)
- Hand-labeled query→section pairs
- Measures top-1 and top-3 precision
- Result: 42% top-1, 57% top-3 across 7 queries
- Known limitation revealed: hierarchical sections (3.1, 3.6) rank higher than parent sections for broad queries — sub-section retrieval issue

**Summarizer evals** (`evals/summary_eval.py`)
- LLM-as-judge with gpt-4o-mini
- Scores faithfulness/completeness/clarity on 1-5 scale
- Result: F 4.33 / C 4.0 / L 4.89 on test.pdf (9 sections)
- Pattern observed: longer sections lose more information at 3-sentence limit

### Deployment (Railway)

Live URL: https://web-production-6eded.up.railway.app

- Deployed as a Railway service pulling from GitHub main branch
- PostgreSQL provisioned as a separate Railway service, connected via DATABASE_URL env var
- OPENAI_API_KEY set as Railway variable
- Auto-deploys on every git push to main
- Container runtime: Python 3.13.14
- Region: US West

Verified end-to-end on production URL:
- Upload PDF → progress polling → download .pptx works
- Tested with real academic paper (Postcolonial Theory book excerpt)
- Generation time: 30-40 seconds

Design decision: env-driven DATABASE_URL means the local SQLite dev pattern 
"just worked" in production. Only change needed: prefix `postgresql+psycopg2://` 
so SQLAlchemy uses the right driver.

Known limitation: Railway free trial ($5 credit) will expire after ~1 month 
of active usage. Portfolio-worthy demo period is 25-30 days from deployment.