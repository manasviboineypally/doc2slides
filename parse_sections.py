"""
Day 2: Detect section headings by font size.
Group body text under each detected heading.
"""
import pdfplumber
from collections import Counter
from statistics import median
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
    # Group characters by their vertical position
    lines = {}
    for char in page.chars:
        line_y = round(char["top"])
        if line_y not in lines:
            lines[line_y] = []
        lines[line_y].append(char)
    
    # For each line, sort characters left-to-right by x position
    result = []
    for y in sorted(lines.keys()):
        chars = sorted(lines[y], key=lambda c: c["x0"])
        
        # Build text + add spaces where gaps suggest word boundaries
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

def detect_sections(pdf_path: str) -> ParsedDocument:
    """
    Walk through the PDF, detect headings, and group body text under each.
    Returns a validated ParsedDocument with Section objects.
    """
    raw_sections = []
    current_section = None
    
    with pdfplumber.open(pdf_path) as pdf:
        body_size = get_body_font_size(pdf)
        heading_threshold = body_size + 1.0
        total_pages = len(pdf.pages)
        
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
    
    # Return as raw dicts for now — filter_real_sections still uses dicts
    return raw_sections


def build_document(pdf_path: str, filtered_sections: list[dict]) -> ParsedDocument:
    """
    Convert filtered dicts into a fully-validated ParsedDocument.
    This is where dicts become Pydantic models.
    """
    with pdfplumber.open(pdf_path) as pdf:
        body_size = get_body_font_size(pdf)
        total_pages = len(pdf.pages)
    
    # Convert each filtered dict into a validated Section
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
    
    # Build the metadata
    metadata = DocumentMetadata(
        total_pages=total_pages,
        total_sections=len(sections),
        body_font_size=body_size,
        heading_threshold=body_size + 1.0,
    )
    
    # Wrap it all in a ParsedDocument — Pydantic validates everything
    return ParsedDocument(
        source_file=pdf_path,
        metadata=metadata,
        sections=sections,
    )


def print_sections(sections: list[dict]) -> None:
    """Print detected sections in a readable format."""
    print(f"Found {len(sections)} sections:\n")
    print("=" * 70)
    
    for i, s in enumerate(sections, start=1):
        word_count = len(s["content"].split())
        print(f"\n[{i}] SECTION: {s['heading']}")
        print(f"    Page: {s['page']}  |  Font size: {s['size']}  |  Words: {word_count}")
        print(f"    Preview: {s['content'][:200]}...")
        print("-" * 70)


def filter_real_sections(sections: list[dict]) -> list[dict]:
    """
    Remove false positives from heading detection.
    
    A real section heading should EITHER:
    - have substantial content (>30 words) AND a heading >2 chars, OR
    - be a recognizable section name even if the heading text is fragmented
    """
    # Common section names we want to keep even if heading detection is messy
    KNOWN_SECTION_KEYWORDS = [
        "abstract", "introduction", "background", "related work",
        "method", "approach", "experiment", "result", "discussion",
        "conclusion", "reference", "appendix", "acknowledg",
    ]
    
    real_sections = []
    for s in sections:
        content_words = len(s["content"].split())
        heading_lower = s["heading"].lower()
        
        # Combine heading + first 50 chars of content to catch fragmented headings
        # Example: heading "A" + content starting with "BSTRACT..." = "a bstract..."
        # Strip spaces and join — handles fragmented headings like 'A' + 'BSTRACT...'
        combined = (heading_lower.replace(" ", "") + s["content"][:50].lower().replace(" ", ""))
        
        # Rule A: does this look like a known section based on heading + content start?
        is_known_section = any(kw in combined for kw in KNOWN_SECTION_KEYWORDS)
        
        if is_known_section and content_words >= 20:
            real_sections.append(s)
            continue
        
        # Rule B: standard filter — substantial heading + substantial content
        if len(s["heading"].strip()) > 2 and content_words >= 30:
            # Skip all-caps fragments with few words
            if s["heading"].isupper() and len(s["heading"].split()) < 3:
                continue
            real_sections.append(s)
    
    # Auto-correct common section labels from content if heading is fragmented
    # e.g. heading="A" + content="BSTRACT n u Compiler..." → heading becomes "Abstract"
    SECTION_LABELS = {
        "abstract": "Abstract",
        "introduction": "Introduction",
        "conclusion": "Conclusion",
        "references": "References",
        "background": "Background",
        "discussion": "Discussion",
        "acknowledg": "Acknowledgments",
    }
    
    for s in real_sections:
        # Combine heading + start of content, stripping spaces
        combined_start = (
            s["heading"].lower().replace(" ", "") + 
            s["content"][:80].lower().replace(" ", "")
        )
        # Limit search to first 80 chars — keyword must appear near the start
        search_zone = combined_start[:80]
        
        for keyword, label in SECTION_LABELS.items():
            if keyword in search_zone:
                s["heading"] = label
                break
    return real_sections


if __name__ == "__main__":
    import sys
    
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else "test.pdf"
    
    try:
        # Step 1: Raw detection (returns dicts)
        raw_sections = detect_sections(pdf_file)
        print(f"Raw detection found {len(raw_sections)} candidates.")
        
        # Step 2: Filter false positives
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