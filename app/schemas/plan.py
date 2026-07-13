"""
Pydantic models for slide plans.

The Planner agent produces one of these. The Writer agent consumes it.
Every slide in the plan has a type, theme, and source sections it draws from.
"""
from pydantic import BaseModel, Field
from typing import List


class SlidePlan(BaseModel):
    """A single slide's plan — what it covers and why."""
    
    index: int = Field(..., ge=1, description="Slide number, starting at 1")
    type: str = Field(..., description="Type of slide: title, context, concept, comparison, example, conclusion")
    title: str = Field(..., min_length=1, description="Short slide title")
    theme: str = Field(..., description="What angle/message this slide should convey")
    sources: List[str] = Field(default_factory=list, description="Section IDs this slide draws from")


class DeckPlan(BaseModel):
    """The full slide deck plan."""
    
    audience: str = Field(..., description="Target audience for the deck")
    total_slides: int = Field(..., ge=1, le=30)
    slides: List[SlidePlan]
    
    def summary(self) -> str:
        """Quick human-readable overview."""
        return "\n".join(
            f"  Slide {s.index} [{s.type}]: {s.title}"
            for s in self.slides
        )