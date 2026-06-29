"""
Pydantic models for parsed documents.

These are the strict data contracts that every part of the pipeline
agrees on. The Parser produces these. The Summarizer consumes these.
The Planner reads from them. And so on.

If a model fails to validate, we know immediately — before bad data 
propagates downstream.
"""
from pydantic import BaseModel, Field
from typing import Optional


class Section(BaseModel):
    """A single logical section of a document (Introduction, Methods, etc.)."""
    
    id: str = Field(..., description="Unique ID like 'sec_1', 'sec_2'")
    heading: str = Field(..., min_length=1, description="The detected heading text")
    content: str = Field(..., description="The body text under this heading")
    page: int = Field(..., ge=1, description="Page number where section starts")
    word_count: int = Field(..., ge=0, description="Words in this section")
    font_size: float = Field(..., gt=0, description="Detected font size of the heading")


class DocumentMetadata(BaseModel):
    """Overall metadata about the parsed document."""
    
    total_pages: int = Field(..., ge=1)
    total_sections: int = Field(..., ge=0)
    body_font_size: float = Field(..., gt=0)
    heading_threshold: float = Field(..., gt=0)


class ParsedDocument(BaseModel):
    """The complete output of the Parser agent."""
    
    source_file: str = Field(..., description="Path to the original PDF")
    metadata: DocumentMetadata
    sections: list[Section]
    
    def total_words(self) -> int:
        """Helper: total word count across all sections."""
        return sum(s.word_count for s in self.sections)