from llm_service import call_llm
from .prompts import CLASSIFY_PROMPT

VALID_LABELS = {
    "PROVIDING_FIELDS",
    "BROADCAST_TO_DEALERS",
    "GENERATE_REPORT",
    "ASKING_QUESTION",
    "REQUESTING_CHANGE"
}

def classify_mechanic_message(request: dict, text: str) -> str:
    missing = [f for f in ["car_model", "car_variant", "car_year", "part_name", "spec", "genuine_pref"] if not request.get(f)]

    prompt = CLASSIFY_PROMPT.format(
        status=request["status"],
        car_model=request.get("car_model") or "unknown",
        part_name=request.get("part_name") or "unknown",
        missing=", ".join(missing) if missing else "none",
        text=text
    )

    try:
        raw = call_llm(prompt).strip().upper()
    except Exception:
        if request.get("status") in ("BROADCASTING", "REPORT_READY"):
            return "BROADCAST_TO_DEALERS"
        return "PROVIDING_FIELDS"

    for label in VALID_LABELS:
        if label in raw:
            return label

    if request.get("status") in ("BROADCASTING", "REPORT_READY"):
        return "BROADCAST_TO_DEALERS"
    return "PROVIDING_FIELDS"