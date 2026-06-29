# Doc2Slides — Parser Testing Notes

Tracking what works, what breaks, and why. This is the parser's known 
behavior across different PDF types as of Day 2.

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
- ⚠️ Title scrambled (same multi-column title issue)
- ⚠️ Section "4 Experiments and Results" filtered out (0 direct words — content lives in 4.1-4.4)
- **Verdict:** Generalized to a different paper without modification

---

## column.pdf — 2001 IEEE conference paper (New Faculty 101)
**Type:** Double-column IEEE format

- ❌ Two-column layout breaks content extraction
- ❌ Drop-cap section headings (decorative first letter) confuse detector
- ❌ Body text from left and right columns gets interleaved
- ✅ Parser doesn't crash — fails gracefully with weird output
- **Verdict:** Known limitation. Future work: column-aware text extraction.

---

## Known limitations

1. **Double-column PDFs** — text from adjacent columns gets jumbled. Affects IEEE, ACM, older Nature/Science papers.
2. **Title detection on arxiv** — title spans page width with rotated arxiv ID; gets scrambled.
3. **Decorative drop-caps** — first letter of section ("INTRODUCTION" → heading "I" + body "NTRODUCTION") splits the heading. Partial fix via content-keyword filter.
4. **Heading inference** — relies on font size as primary signal. Documents with weak typographic hierarchy (some web exports, scanned PDFs) may not produce clean sections.

---

## Future improvements (post-MVP)

- Per-column text extraction for multi-column PDFs
- LLM-based section validation (Week 2 work — Summarizer agent can validate)
- Handle scanned/image-only PDFs via OCR fallback
- Detect and discard front-matter (title block, affiliations) before section detection

## Day 3 update — known limitations

- Multi-line affiliation blocks (like paper2.pdf with "University of 
  Strathclyde, Glasgow, UK") can hide the abstract section behind the 
  affiliation line. The content is still captured; only the heading 
  label is wrong.
- The auto-correct correctly handles "Abstract Interpretation" vs 
  "Abstract" disambiguation via the AMBIGUOUS_PHRASES list.
- Tradeoff accepted: stricter matching would miss more abstracts than 
  it gains. Looser matching creates false positives. Current logic 
  picks the safer side.