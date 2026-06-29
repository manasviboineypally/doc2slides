"""
Doc2Slides — PDF section parser.
Detects section headings using font size and groups body text under each.
Returns a validated ParsedDocument (Pydantic) ready for the next agent.
"""
import re
import pdfplumber
from collections import Counter
from schemas.document import Section, DocumentMetadata, ParsedDocument


def get_body_font_size(pdf) -> float:
    """Find the most common font size — that's the body text."""
    sizes = []
    for page in pdf.pages:
        for char in page.chars:
            sizes.append(round(char["size"], 1))
    return Counter(sizes).most_common(1)[0][0]


def extract_lines_with_size(page):
    """
    Group characters into lines, sorting left-to-right within each line.
    Returns a list of dicts: [{text, size}, ...]
    """
    lines = {}
    for char in page.chars:
        line_y = round(char["top"])
        if line_y not in lines:
            lines[line_y] = []
        lines[line_y].append(char)
    
    result = []
    for y in sorted(lines.keys()):
        chars = sorted(lines[y], key=lambda c: c["x0"])
        
        text_parts = []
        prev_x = None
        for c in chars:
            if prev_x is not None and (c["x0"] - prev_x) > 2:
                text_parts.append(" ")
            text_parts.append(c["text"])
            prev_x = c["x1"]
        
        text = "".join(text_parts).strip()
        max_size = max(c["size"] for c in chars)
        
        if text:
            result.append({
                "text": text,
                "size": round(max_size, 1),
            })
    return result


def detect_sections(pdf_path: str) -> list[dict]:
    """
    Walk through the PDF, detect headings, and group body text under each.
    Returns raw section dicts (will be filtered and converted to Pydantic later).
    """
    raw_sections = []
    current_section = None
    
    with pdfplumber.open(pdf_path) as pdf:
        body_size = get_body_font_size(pdf)
        heading_threshold = body_size + 1.0
        
        print(f"Body font size: {body_size}")
        print(f"Heading threshold: > {heading_threshold}\n")
        
        for page_num, page in enumerate(pdf.pages, start=1):
            lines = extract_lines_with_size(page)
            
            for line in lines:
                if line["size"] > heading_threshold:
                    if current_section:
                        raw_sections.append(current_section)
                    current_section = {
                        "heading": line["text"],
                        "size": line["size"],
                        "page": page_num,
                        "content": [],
                    }
                else:
                    if current_section:
                        current_section["content"].append(line["text"])
        
        if current_section:
            raw_sections.append(current_section)
    
    # Join content into single strings
    for s in raw_sections:
        s["content"] = " ".join(s["content"])
    
    return raw_sections


def filter_real_sections(sections: list[dict]) -> list[dict]:
    """
    Remove false positives from heading detection, then auto-correct
    common section labels (Abstract, Introduction, Conclusion, etc.).
    """
    KNOWN_SECTION_KEYWORDS = [
        "abstract", "introduction", "background", "related work",
        "method", "approach", "experiment", "result", "discussion",
        "conclusion", "reference", "appendix", "acknowledg",
    ]
    
    real_sections = []
    for s in sections:
        content_words = len(s["content"].split())
        heading_lower = s["heading"].lower()
        
        # Combined heading + content start, no spaces — catches fragmented headings
        combined = (heading_lower.replace(" ", "") + s["content"][:50].lower().replace(" ", ""))
        
        # Rule A: known section name (even if heading is fragmented)
        is_known_section = any(kw in combined for kw in KNOWN_SECTION_KEYWORDS)
        if is_known_section and content_words >= 20:
            real_sections.append(s)
            continue
        
        # Rule B: standard filter — substantial heading + substantial content
        if len(s["heading"].strip()) > 2 and content_words >= 30:
            if s["heading"].isupper() and len(s["heading"].split()) < 3:
                continue
            real_sections.append(s)
    
    # ── Auto-correct common section labels ─────────────────────────────────────
    SECTION_LABELS = {
        "abstract": "Abstract",
        "introduction": "Introduction",
        "conclusion": "Conclusion",
        "references": "References",
        "background": "Background",
        "discussion": "Discussion",
        "acknowledg": "Acknowledgments",
    }
    
    # Phrases that contain a keyword but mean something different — skip rename
    AMBIGUOUS_PHRASES = {
        "abstract": ["interpretation", "syntax", "class", "data type", "algebra"],
    }
    
    for s in real_sections:
        original_heading = s["heading"].strip()
        # Strip leading digits/spaces (e.g. "7 Conclusion" → "Conclusion")
        cleaned = re.sub(r"^[\d\s]+", "", original_heading).strip().lower()
        # Combined string for ambiguity checks (keeps spaces for phrase detection)
        combined = (original_heading + " " + s["content"][:80]).lower()
        # Squashed (no spaces) version handles fragmented headings
        # e.g. "A" + "BSTRACT n u Compiler..." → "abstractnucompiler..."
        squashed = combined.replace(" ", "")
        
        for keyword, label in SECTION_LABELS.items():
            # Skip if this is actually a different concept like "Abstract Interpretation"
            ambiguous = AMBIGUOUS_PHRASES.get(keyword, [])
            if any(phrase in combined for phrase in ambiguous):
                continue
            
            # Case 1: cleaned heading exactly equals the label
            # (e.g. "7 Conclusion" → "Conclusion", "Introduction" → "Introduction")
            if cleaned == keyword:
                s["heading"] = label
                break
            # Case 2: squashed-no-space starts with the keyword
            # (catches fragmented headings like "A" + "BSTRACT n u...")
            if squashed.startswith(keyword):
                s["heading"] = label
                break
    
    return real_sections


def build_document(pdf_path: str, filtered_sections: list[dict]) -> ParsedDocument:
    """
    Convert filtered dicts into a fully-validated ParsedDocument.
    This is where dicts become Pydantic models.
    """
    with pdfplumber.open(pdf_path) as pdf:
        body_size = get_body_font_size(pdf)
        total_pages = len(pdf.pages)
    
    sections = []
    for i, s in enumerate(filtered_sections, start=1):
        section = Section(
            id=f"sec_{i}",
            heading=s["heading"],
            content=s["content"],
            page=s["page"],
            word_count=len(s["content"].split()),
            font_size=s["size"],
        )
        sections.append(section)
    
    metadata = DocumentMetadata(
        total_pages=total_pages,
        total_sections=len(sections),
        body_font_size=body_size,
        heading_threshold=body_size + 1.0,
    )
    
    return ParsedDocument(
        source_file=pdf_path,
        metadata=metadata,
        sections=sections,
    )


if __name__ == "__main__":
    import sys
    
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else "test.pdf"
    
    try:
        # Step 1: Raw detection
        raw_sections = detect_sections(pdf_file)
        print(f"Raw detection found {len(raw_sections)} candidates.")
        
        # Step 2: Filter false positives + auto-correct labels
        filtered = filter_real_sections(raw_sections)
        print(f"After filtering: {len(filtered)} real sections.\n")
        
        # Step 3: Build the validated ParsedDocument
        document = build_document(pdf_file, filtered)
        
        # Step 4: Show the result
        print("=" * 70)
        print(f"📄 Document: {document.source_file}")
        print(f"   Total pages: {document.metadata.total_pages}")
        print(f"   Sections found: {document.metadata.total_sections}")
        print(f"   Total words: {document.total_words()}")
        print("=" * 70)
        
        for s in document.sections:
            print(f"\n[{s.id}] {s.heading}")
            print(f"  Page: {s.page} | Words: {s.word_count} | Font: {s.font_size}")
            print(f"  Preview: {s.content[:150]}...")
        
    except FileNotFoundError:
        print(f"ERROR: Could not find '{pdf_file}'")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)