from llm_service import call_llm, extract_json
from .prompts import EXTRACT_PROMPT, CLARIFY_PROMPT, ANSWER_QUESTION_PROMPT
from .validation import validate_fields
import db

def extract_fields(conversation: list) -> dict:
    convo_text = "\n".join(f"{m['role']}: {m['text']}" for m in conversation)
    try:
        raw = call_llm(EXTRACT_PROMPT.format(conversation=convo_text))
    except Exception:
        return {}
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

def answer_mechanic_question(request: dict, text: str) -> str:
    threads = db.get_threads_for_request(request["id"])
    if threads:
        summary = "; ".join(
            f"{t['shop_name']}: {t['status']}" + (f" (PKR {t['price']})" if t.get("price") else "")
            for t in threads
        )
    else:
        summary = "no dealers contacted yet"

    prompt = ANSWER_QUESTION_PROMPT.format(
        status=request["status"],
        part_name=request.get("part_name") or "not yet specified",
        car_model=request.get("car_model") or "",
        car_variant=request.get("car_variant") or "",
        car_year=request.get("car_year") or "",
        dealer_summary=summary,
        text=text
    )
    try:
        return call_llm(prompt)
    except Exception:
        return "I'm having trouble answering right now — please try again shortly."