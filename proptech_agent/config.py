"""
Config — API key + model setup.

Create a .env file next to this one with:
    OPENAI_API_KEY=sk-...
"""
import os
from dotenv import load_dotenv

load_dotenv()

MODEL = "openai:gpt-4o-mini"  # cheap + fast; use "openai:gpt-4o" for higher quality

if not os.environ.get("OPENAI_API_KEY"):
    raise RuntimeError(
        "OPENAI_API_KEY not found. Create a .env file in this folder with "
        "OPENAI_API_KEY=sk-... or export it in your shell."
    )
