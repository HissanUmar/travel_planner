import db
import whatsapp
import json
from datetime import datetime
from llm_service import call_llm, extract_json
from .prompts import (
    build_outreach_message, build_parse_prompt, build_dealer_persona_prompt,
    build_extract_alternative_prompt
)
from .intent import classify_dealer_message

def broadcast_to_dealers(request: dict) -> list:
    shops = db.find_shops_for_part(request["part_name"])
    message = build_outreach_message(request)

    contacted = []
    for shop in shops:
        whatsapp.send_message(shop["phone"], message)
        db.save_whatsapp_message(shop["phone"], "out", message)
        thread_id = db.create_thread(request["id"], shop, message)
        contacted.append({"thread_id": thread_id, "shop": shop["name"], "phone": shop["phone"]})

    return contacted

def handle_cold_dealer_message(shop: dict, text: str) -> str:
    try:
        return call_llm(build_dealer_persona_prompt(shop, text))
    except Exception:
        return "Thanks for reaching out — how can I help?"

def forward_update_to_mechanic(thread: dict, parsed: dict):
    request = db.get_request(thread["request_id"])
    if not request:
        return
    if parsed.get("available") is False:
        summary = f"Update: {thread['shop_name']} doesn't have this part."
    else:
        parts = [f"Update: {thread['shop_name']}"]
        if parsed.get("available"):
            parts.append("has it in stock")
        if parsed.get("is_genuine") is not None:
            parts.append(f"({'genuine' if parsed['is_genuine'] else 'aftermarket'})")
        if parsed.get("price"):
            parts.append(f"— PKR {parsed['price']}")
        summary = " ".join(parts)
    db.append_conversation(thread["request_id"], "llm", summary, msg_type="update")
    db.mark_unread(thread["request_id"])

def decide_next_step(parsed: dict) -> dict:
    if parsed.get("available") is False:
        return {"complete": True, "question": None}
    missing = []
    if parsed.get("price") is None:
        missing.append("price")
    if parsed.get("is_genuine") is None:
        missing.append("whether it's genuine or aftermarket")
    if not missing:
        return {"complete": True, "question": None}
    return {"complete": False, "question": "Could you also let me know " + " and ".join(missing) + "?"}

def handle_availability_reply(thread: dict, text: str) -> str:
    db.append_thread_conversation(thread["id"], "dealer", text)

    refreshed = db.get_thread(thread["id"])
    conversation = json.loads(refreshed["conversation"])

    try:
        parsed = extract_json(call_llm(build_parse_prompt(conversation)))
    except Exception:
        reply = "Got it, thanks."
        db.append_thread_conversation(thread["id"], "llm", reply)
        return reply

    if parsed.get("available") is False:
        db.update_thread(thread["id"], status="REJECTED", notes=text, replied_at=datetime.utcnow().isoformat())
        forward_update_to_mechanic(thread, parsed)
        reply = "Thanks for checking, let me know if that changes."
        db.append_thread_conversation(thread["id"], "llm", reply)
        return reply

    db.update_thread(
        thread["id"],
        status="PRICED" if parsed.get("price") else "RESPONDED",
        is_genuine=str(parsed.get("is_genuine")) if parsed.get("is_genuine") is not None else thread.get("is_genuine"),
        price=parsed.get("price") if parsed.get("price") is not None else thread.get("price"),
        notes=text,
        replied_at=datetime.utcnow().isoformat()
    )

    decision = decide_next_step(parsed)
    if not decision["complete"]:
        reply = decision["question"]
        db.append_thread_conversation(thread["id"], "llm", reply)
        return reply

    forward_update_to_mechanic(thread, parsed)
    reply = "Great, thank you! Let me confirm this with the mechanic and I'll get back to you shortly."
    db.append_thread_conversation(thread["id"], "llm", reply)
    return reply

def handle_dealer_question(thread: dict, request: dict, text: str) -> str:
    db.append_thread_conversation(thread["id"], "dealer", text, msg_type="question")
    db.set_pending_mechanic_question(thread["id"], text)
    db.set_pending_dealer_question(request["id"], thread["id"], thread["shop_name"], text)
    db.append_conversation(
        request["id"], "llm",
        f"❓ {thread['shop_name']} is asking: {text}",
        msg_type="dealer_question", thread_id=thread["id"]
    )
    db.mark_unread(request["id"])
    reply = "Let me check with the mechanic and get back to you."
    db.append_thread_conversation(thread["id"], "llm", reply)
    return reply

def handle_alternative_offer(thread: dict, request: dict, text: str) -> str:
    db.append_thread_conversation(thread["id"], "dealer", text, msg_type="alternative")
    try:
        offer = extract_json(call_llm(build_extract_alternative_prompt(text)))
    except Exception:
        offer = {"description": text, "price": None}

    db.set_alternative_offer(thread["id"], offer)
    summary = f"🔄 {thread['shop_name']} offered an alternative: {offer.get('description', text)}"
    if offer.get("price"):
        summary += f" — PKR {offer['price']}"
    db.append_conversation(
        request["id"], "llm", summary,
        msg_type="alternative_offer", thread_id=thread["id"]
    )
    db.mark_unread(request["id"])
    reply = "Thanks, I'll pass this alternative along to the mechanic."
    db.append_thread_conversation(thread["id"], "llm", reply)
    return reply

def handle_dealer_reply(thread: dict, text: str) -> str:
    request = db.get_request(thread["request_id"])
    if not request:
        return "Got it, thanks."

    intent = classify_dealer_message(request, thread, text)

    if intent == "ASKING_QUESTION":
        return handle_dealer_question(thread, request, text)

    if intent == "OFFERING_ALTERNATIVE":
        return handle_alternative_offer(thread, request, text)

    return handle_availability_reply(thread, text)

def send_mechanic_answer_to_dealer(thread_id: int, answer_text: str):
    thread = db.get_thread(thread_id)
    if not thread:
        return
    whatsapp.send_message(thread["shop_phone"], answer_text)
    db.append_thread_conversation(thread_id, "llm", answer_text)
    # revert to whatever made sense before the question — RESPONDED is a safe general default
    revert_status = "RESPONDED" if thread.get("price") or thread.get("is_genuine") else "CONTACTED"
    db.clear_pending_mechanic_question(thread_id, revert_status)

def check_stale_threads(hours: int = 6) -> int:
    stale = db.get_stale_threads(hours)
    for thread in stale:
        db.close_stale_thread(thread["id"])
        request = db.get_request(thread["request_id"])
        if request:
            summary = f"Update: {thread['shop_name']} did not respond within {hours} hours — marked as no response."
            db.append_conversation(thread["request_id"], "llm", summary, msg_type="update")
            db.mark_unread(thread["request_id"])
    return len(stale)


def handle_dealer_question(thread: dict, request: dict, text: str) -> str:
    db.append_thread_conversation(thread["id"], "dealer", text, msg_type="question")
    db.set_pending_mechanic_question(thread["id"], text)
    db.mark_thread_unread(thread["id"])
    db.mark_unread(request["id"])  # sidebar dot only — content lives in the thread, not the general feed
    reply = "Let me check with the mechanic and get back to you."
    db.append_thread_conversation(thread["id"], "llm", reply)
    return reply

def handle_alternative_offer(thread: dict, request: dict, text: str) -> str:
    db.append_thread_conversation(thread["id"], "dealer", text, msg_type="alternative")
    try:
        offer = extract_json(call_llm(build_extract_alternative_prompt(text)))
    except Exception:
        offer = {"description": text, "price": None}

    db.set_alternative_offer(thread["id"], offer)
    db.mark_thread_unread(thread["id"])
    db.mark_unread(request["id"])  # sidebar dot only
    reply = "Thanks, I'll pass this alternative along to the mechanic."
    db.append_thread_conversation(thread["id"], "llm", reply)
    return reply