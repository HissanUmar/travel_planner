from llm_service import call_llm
from .prompts import build_dealer_classify_prompt

VALID_LABELS = {"ANSWERING_AVAILABILITY", "ASKING_QUESTION", "OFFERING_ALTERNATIVE"}

def classify_dealer_message(request: dict, thread: dict, text: str) -> str:
    prompt = build_dealer_classify_prompt(request, thread, text)
    try:
        raw = call_llm(prompt).strip().upper()
    except Exception:
        return "ANSWERING_AVAILABILITY"  # safe fallback — degrade to old behavior

    for label in VALID_LABELS:
        if label in raw:
            return label

    return "ANSWERING_AVAILABILITY"