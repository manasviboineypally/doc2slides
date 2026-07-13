"""Sanity check — does OpenAI respond to a simple prompt?"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ OPENAI_API_KEY not found in .env")
    exit(1)

print(f"✅ Key loaded (starts with: {api_key[:10]}...)")

client = OpenAI(api_key=api_key)

print("🤖 Asking GPT a question...")
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "In 2 sentences, what is a research paper abstract?"}
    ],
)

print(f"\n✅ Got response:\n{response.choices[0].message.content}")