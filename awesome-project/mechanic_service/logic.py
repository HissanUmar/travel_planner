from llm_service import call_llm, extract_json
from .prompts import EXTRACT_PROMPT, CLARIFY_PROMPT
from .validation import validate_fields

def extract_fields(conversation: list) -> dict:
    convo_text = "\n".join(f"{m['role']}: {m['text']}" for m in conversation)
    try:
        raw = call_llm(EXTRACT_PROMPT.format(conversation=convo_text))
    except Exception:
        return {}  # LLM unreachable — treat as nothing extracted, mechanic gets asked again
    parsed = extract_json(raw)
    return validate_fields(parsed)

def generate_clarification(missing: list) -> str:
    try:
        return call_llm(CLARIFY_PROMPT.format(missing=", ".join(missing)))
    except Exception:
        return f"Could you tell me more about: {', '.join(missing)}?"

def format_confirmation(request: dict) -> str:
    return (
        "Here's what I've got — please confirm this is correct:\n\n"
        f"Car: {request['car_model']} {request['car_variant']} ({request['car_year']})\n"
        f"Part: {request['part_name']}\n"
        f"Spec: {request['spec']}\n"
        f"Preference: {request['genuine_pref']}\n\n"
        f"Reply YES to confirm and I'll start checking with dealers, or tell me what to change."
    )