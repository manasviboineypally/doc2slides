"""Test if the summarizer's function works standalone."""
from app.agents.summarizer import summarize_section

result = summarize_section(
    heading="X",
    content="Y"
)
print(f"\nResponse:\n{result}")