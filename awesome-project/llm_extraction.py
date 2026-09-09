import requests
import json
import re
from config import LLM_URL

EXTRACT_PROMPT = """You are extracting a car part request from a conversation.
Required fields: car_model, car_variant, car_year, part_name, spec, genuine_pref (genuine/aftermarket/either).

Conversation so far:
{conversation}

Return ONLY a JSON object with any of these fields you can determine. Use null for fields not mentioned.
Example: {{"car_model": "Honda City", "car_variant": null, "car_year": null, "part_name": "front bumper", "spec": null, "genuine_pref": null}}
JSON:"""

CLARIFY_PROMPT = """A mechanic is requesting a car part. These fields are still missing: {missing}.
Ask ONE short, natural message asking for just these missing details. Don't repeat what's already known.
Missing fields: {missing}
Message:"""

def call_llm(prompt: str) -> str:
    r = requests.post(LLM_URL, json={"text": prompt}, timeout=15)
    data = r.json()
    return data.get("response") or data.get("text") or data.get("message") or str(data)

def extract_fields(conversation: list) -> dict:
    convo_text = "\n".join(f"{m['role']}: {m['text']}" for m in conversation)
    raw = call_llm(EXTRACT_PROMPT.format(conversation=convo_text))
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}

def generate_clarification(missing: list) -> str:
    return call_llm(CLARIFY_PROMPT.format(missing=", ".join(missing)))