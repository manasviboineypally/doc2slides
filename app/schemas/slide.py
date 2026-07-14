"""
Pydantic models for written slide content.

The Writer agent produces these — one Slide per plan entry.
The Builder agent (Day 10) will use these to generate the .pptx file.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class Slide(BaseModel):
    """A single fully-written slide, ready to build."""
    
    index: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=120)
    bullets: List[str] = Field(default_factory=list, description="Slide body content, one bullet per point")
    speaker_notes: Optional[str] = Field(None, description="Presenter notes shown to speaker, not the audience")


class WrittenDeck(BaseModel):
    """The complete written slide deck."""
    
    audience: str
    total_slides: int = Field(..., ge=1)
    slides: List[Slide]