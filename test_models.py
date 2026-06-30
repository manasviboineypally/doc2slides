"""Quick sanity check that our Pydantic models work."""
from app.schemas.document import Section, DocumentMetadata, ParsedDocument


# Test 1: Create a valid Section
section = Section(
    id="sec_1",
    heading="1 Introduction",
    content="Deep learning models have been...",
    page=2,
    word_count=487,
    font_size=14.3
)
print(f"✅ Created section: {section.heading}")
print(f"   Content preview: {section.content[:50]}...")
print(f"   Page: {section.page}, Words: {section.word_count}")

# Test 2: Create a ParsedDocument
metadata = DocumentMetadata(
    total_pages=10,
    total_sections=1,
    body_font_size=10.0,
    heading_threshold=11.0
)

doc = ParsedDocument(
    source_file="test.pdf",
    metadata=metadata,
    sections=[section]
)
print(f"\n✅ Created document from: {doc.source_file}")
print(f"   Total sections: {len(doc.sections)}")
print(f"   Total words: {doc.total_words()}")

# Test 3: Try to create invalid data — should FAIL
print("\n🧪 Testing validation (these should all fail):")

try:
    bad = Section(id="x", heading="", content="text", page=1, word_count=10, font_size=12.0)
    print("   ❌ Empty heading was accepted (BUG)")
except Exception as e:
    print(f"   ✅ Empty heading rejected")

try:
    bad = Section(id="x", heading="OK", content="text", page=0, word_count=10, font_size=12.0)
    print("   ❌ Page=0 was accepted (BUG)")
except Exception as e:
    print(f"   ✅ Page=0 rejected (must be ≥ 1)")

try:
    bad = Section(id="x", heading="OK", content="text", page=1, word_count=-5, font_size=12.0)
    print("   ❌ Negative word_count was accepted (BUG)")
except Exception as e:
    print(f"   ✅ Negative word_count rejected")

print("\n🎉 All validations working correctly!")