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
from sanitize import sanitize_message

def broadcast_to_dealers(request: dict) -> list:
    shops = db.find_shops_for_part(request["part_name"])
    message = build_outreach_message(request)

    contacted = []
    for shop in shops:
        thread_id = db.create_thread(request["id"], shop, message)
        db.save_whatsapp_message(shop["phone"], "out", message)
        whatsapp.send_message(shop["phone"], message)
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
            is_gen = parsed["is_genuine"]
            is_gen_str = "genuine" if str(is_gen).lower() in ("true", "1") else "aftermarket"
            parts.append(f"({is_gen_str})")
        if parsed.get("price"):
            parts.append(f"— PKR {parsed['price']:,.0f}")
        summary = " ".join(parts)
    db.append_conversation(thread["request_id"], "llm", summary, msg_type="update")
    db.mark_unread(thread["request_id"])

def decide_next_step(state: dict) -> dict:
    if state.get("available") is False:
        return {"complete": True, "question": None}
    missing = []
    if state.get("price") is None:
        missing.append("price")
    if state.get("is_genuine") is None:
        missing.append("whether it's genuine or aftermarket")
    if not missing:
        return {"complete": True, "question": None}
    return {"complete": False, "question": "Could you also let me know " + " and ".join(missing) + "?"}

def handle_availability_reply(thread: dict, text: str) -> str:
    db.append_thread_conversation(thread["id"], "dealer", text)

    refreshed = db.get_thread(thread["id"])
    conversation = json.loads(refreshed["conversation"])

    try:
        parsed = extract_json(call_llm(build_parse_prompt(conversation, refreshed)))
    except Exception:
        reply = "Got it, thanks."
        db.append_thread_conversation(thread["id"], "llm", reply)
        return reply

    if parsed.get("available") is False:
        db.update_thread(thread["id"], status="REJECTED", notes=text, replied_at=datetime.utcnow().isoformat())
        forward_update_to_mechanic(thread, {"available": False})
        reply = "Thanks for checking, let me know if that changes."
        db.append_thread_conversation(thread["id"], "llm", reply)
        return reply

    # Merge multi-turn state: take newly parsed value or retain previously learned value
    merged_price = parsed.get("price") if parsed.get("price") is not None else refreshed.get("price")
    if parsed.get("is_genuine") is not None:
        merged_genuine = "True" if parsed["is_genuine"] is True else ("False" if parsed["is_genuine"] is False else str(parsed["is_genuine"]))
    else:
        merged_genuine = refreshed.get("is_genuine")

    new_status = "PRICED" if merged_price is not None else "RESPONDED"
    db.update_thread(
        thread["id"],
        status=new_status,
        is_genuine=merged_genuine,
        price=merged_price,
        notes=text,
        replied_at=datetime.utcnow().isoformat()
    )

    merged_state = {
        "available": True,
        "price": merged_price,
        "is_genuine": merged_genuine
    }
    updated_thread = db.get_thread(thread["id"])

    decision = decide_next_step(merged_state)
    if not decision["complete"]:
        reply = decision["question"]
        db.append_thread_conversation(thread["id"], "llm", reply)
        return reply

    # If priced, check if parent request should transition to REPORT_READY
    req = db.get_request(thread["request_id"])
    if req and req["status"] == "BROADCASTING":
        db.set_status(thread["request_id"], "REPORT_READY")

    forward_update_to_mechanic(updated_thread, merged_state)
    reply = "Great, thank you! Let me confirm this with the mechanic and I'll get back to you shortly."
    db.append_thread_conversation(thread["id"], "llm", reply)
    return reply

def handle_dealer_question(thread: dict, request: dict, text: str) -> str:
    db.append_thread_conversation(thread["id"], "dealer", text, msg_type="question")
    db.set_pending_mechanic_question(thread["id"], text)
    db.mark_thread_unread(thread["id"])
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
    db.mark_thread_unread(thread["id"])
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
    clean_text = sanitize_message(answer_text)
    db.append_thread_conversation(thread_id, "llm", clean_text)
    revert_status = "RESPONDED" if thread.get("price") or thread.get("is_genuine") else "CONTACTED"
    db.clear_pending_mechanic_question(thread_id, revert_status)
    whatsapp.send_message(thread["shop_phone"], clean_text)

def broadcast_mechanic_message_to_dealers(request_id: int, message_text: str) -> list:
    threads = db.get_threads_for_request(request_id)
    active_threads = [t for t in threads if t["status"] not in ("CLOSED", "REJECTED", "NO_RESPONSE")]
    clean_text = sanitize_message(message_text)
    sent_shops = []
    for t in active_threads:
        db.append_thread_conversation(t["id"], "mechanic", clean_text)
        whatsapp.send_message(t["shop_phone"], f"Message from mechanic: {clean_text}")
        sent_shops.append(t["shop_name"])
    return sent_shops

def generate_aggregated_report(request_id: int) -> dict:
    req = db.get_request(request_id)
    if not req:
        return {"status": "error", "message": "Request not found"}

    threads = db.get_threads_for_request(request_id)
    priced_threads = [t for t in threads if t.get("price") is not None and t["status"] not in ("REJECTED", "CLOSED", "NO_RESPONSE")]
    priced_threads.sort(key=lambda t: float(t["price"]))

    rejected_threads = [t for t in threads if t["status"] == "REJECTED"]
    pending_threads = [t for t in threads if t["status"] in ("CONTACTED", "AWAITING_MECHANIC_INPUT")]

    total = len(threads)
    priced_count = len(priced_threads)

    lines = [
        f"📊 SOURCING REPORT: {req['part_name']} ({req['car_model']} {req['car_variant']} {req['car_year']})",
        f"Spec: {req.get('spec', 'Standard')} | Preference: {req.get('genuine_pref', 'Any')}",
        f"Dealers contacted: {total} | Offers received: {priced_count} | Unavailable: {len(rejected_threads)} | Waiting: {len(pending_threads)}"
    ]

    if priced_threads:
        best = priced_threads[0]
        genuine_tag = "Genuine" if str(best.get("is_genuine")).lower() in ("true", "1") else "Aftermarket"
        lines.append(f"\n🏆 Best Offer: PKR {best['price']:,.0f} from {best['shop_name']} ({genuine_tag})")
        lines.append("\nAll Offers:")
        for idx, t in enumerate(priced_threads, 1):
            gen = "Genuine" if str(t.get("is_genuine")).lower() in ("true", "1") else "Aftermarket"
            status_tag = " — ✅ Confirmed" if t["status"] == "SELECTED" else ""
            lines.append(f"  {idx}. {t['shop_name']}: PKR {t['price']:,.0f} ({gen}){status_tag}")
    else:
        lines.append("\nNo priced offers received yet. We are still awaiting dealer responses.")

    if rejected_threads:
        shop_names = ", ".join(t["shop_name"] for t in rejected_threads)
        lines.append(f"\nUnavailable at: {shop_names}")

    report_text = "\n".join(lines)

    db.append_conversation(request_id, "llm", report_text, msg_type="report")
    if req["status"] == "BROADCASTING" and priced_threads:
        db.set_status(request_id, "REPORT_READY")
    db.mark_unread(request_id)

    return {
        "status": "report_generated",
        "request_id": request_id,
        "report_text": report_text,
        "priced_count": priced_count,
        "total_contacted": total
    }

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