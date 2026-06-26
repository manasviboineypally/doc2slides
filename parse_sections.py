"""
Day 2: Detect section headings by font size.
Group body text under each detected heading.
"""
import pdfplumber
from collections import Counter
from statistics import median


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

def detect_sections(pdf_path: str) -> list[dict]:
    """
    Walk through the PDF, detect headings, and group body text under each.
    Returns a list of sections: [{heading, content, page}, ...]
    """
    sections = []
    current_section = None
    
    with pdfplumber.open(pdf_path) as pdf:
        body_size = get_body_font_size(pdf)
        # Anything more than 1pt larger than body text counts as a heading
        heading_threshold = body_size + 1.0
        
        print(f"Body font size: {body_size}")
        print(f"Heading threshold: > {heading_threshold}\n")
        
        for page_num, page in enumerate(pdf.pages, start=1):
            lines = extract_lines_with_size(page)
            
            for line in lines:
                if line["size"] > heading_threshold:
                    # This line is a heading — start a new section
                    if current_section:
                        sections.append(current_section)
                    current_section = {
                        "heading": line["text"],
                        "size": line["size"],
                        "page": page_num,
                        "content": [],
                    }
                else:
                    # Body text — add to current section
                    if current_section:
                        current_section["content"].append(line["text"])
                    # If no section started yet, ignore (front matter)
        
        # Don't forget the last section
        if current_section:
            sections.append(current_section)
    
    # Join the content lines into a single string
    for s in sections:
        s["content"] = " ".join(s["content"])
    
    return sections


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
    
    return real_sections


if __name__ == "__main__":
    import sys
    
    # Allow PDF filename as command line argument, default to test.pdf
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else "test.pdf"
    
    try:
        sections = detect_sections(pdf_file)
    except FileNotFoundError:
        print(f"ERROR: Could not find '{pdf_file}'")
        print(f"\nMake sure the PDF is in: {__file__.rsplit(chr(92), 1)[0]}")
        sys.exit(1)
    
    print(f"\nRaw detection found {len(sections)} candidates.")
    
    # DEBUG: show ALL raw candidates so we can see what's there
    print("\n--- ALL RAW CANDIDATES ---")
    for i, s in enumerate(sections, start=1):
        word_count = len(s["content"].split())
        heading_preview = s["heading"][:50]
        content_preview = s["content"][:80]
        print(f"[{i}] heading='{heading_preview}' | words={word_count}")
        print(f"    content_start='{content_preview}'")
    print("--- END RAW CANDIDATES ---\n")
    
    real_sections = filter_real_sections(sections)
    print(f"After filtering: {len(real_sections)} real sections.\n")
    
    print_sections(real_sections)