from llm_service import call_llm
from .prompts import CLASSIFY_PROMPT
import json

VALID_LABELS = {"PROVIDING_FIELDS", "ASKING_QUESTION", "REQUESTING_CHANGE", "ANSWERING_DEALER_QUESTION"}

def classify_mechanic_message(request: dict, text: str) -> str:
    missing = [f for f in ["car_model", "car_variant", "car_year", "part_name", "spec", "genuine_pref"] if not request.get(f)]
    has_pending = bool(request.get("pending_dealer_question"))

    prompt = CLASSIFY_PROMPT.format(
        status=request["status"],
        car_model=request.get("car_model") or "unknown",
        part_name=request.get("part_name") or "unknown",
        missing=", ".join(missing) if missing else "none",
        has_pending_question="Yes" if has_pending else "No",
        text=text
    )

    try:
        raw = call_llm(prompt).strip().upper()
    except Exception:
        return "PROVIDING_FIELDS"  # safe fallback — degrade to old behavior

    for label in VALID_LABELS:
        if label in raw:
            # ANSWERING_DEALER_QUESTION only valid if one is actually pending
            if label == "ANSWERING_DEALER_QUESTION" and not has_pending:
                continue
            return label

    return "PROVIDING_FIELDS"  # default fallback if classification is unclear