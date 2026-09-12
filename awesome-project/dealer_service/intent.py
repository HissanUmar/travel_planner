import json
from llm_service import call_llm
from .prompts import build_dealer_classify_prompt

VALID_LABELS = {"ANSWERING_AVAILABILITY", "ASKING_QUESTION", "OFFERING_ALTERNATIVE"}

def classify_dealer_message(request: dict, thread: dict, text: str) -> str:
    last_system_msg = None
    if thread and thread.get("conversation"):
        try:
            convo = json.loads(thread["conversation"]) if isinstance(thread["conversation"], str) else thread["conversation"]
            for m in reversed(convo):
                if m.get("role") in ("llm", "mechanic"):
                    last_system_msg = m.get("text")
                    break
        except Exception:
            pass

    prompt = build_dealer_classify_prompt(request, thread, text, last_system_msg)
    try:
        raw = call_llm(prompt).strip().upper()
    except Exception:
        return "ANSWERING_AVAILABILITY"  # safe fallback — degrade to old behavior

    for label in VALID_LABELS:
        if label in raw:
            return label

    return "ANSWERING_AVAILABILITY"