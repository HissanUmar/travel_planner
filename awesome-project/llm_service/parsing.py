import json
import re

def extract_json(raw: str) -> dict:
    """Pulls the first {...} block out of an LLM response and parses it. Returns {} on failure."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}
