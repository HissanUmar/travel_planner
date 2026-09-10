import db
import whatsapp
import json
from datetime import datetime
from llm_service import call_llm, extract_json
from .prompts import build_outreach_message, build_parse_prompt, build_dealer_persona_prompt

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
        else:
            parts.append("— price pending")
        summary = " ".join(parts)
    db.append_conversation(thread["request_id"], "llm", summary)
    db.mark_unread(thread["request_id"])

def decide_next_step(parsed: dict) -> dict:
    """Code-level decision, not left to the LLM's own judgment — determines exactly
    what's still missing and what to ask, given what's confirmed available."""
    if parsed.get("available") is False:
        return {"complete": True, "question": None}

    missing = []
    if parsed.get("price") is None:
        missing.append("price")
    if parsed.get("is_genuine") is None:
        missing.append("whether it's genuine or aftermarket")

    if not missing:
        return {"complete": True, "question": None}

    question = "Could you also let me know " + " and ".join(missing) + "?"
    return {"complete": False, "question": question}

def handle_dealer_reply(thread: dict, text: str) -> str:
    db.append_thread_conversation(thread["id"], "dealer", text)

    refreshed = db.get_open_thread_by_phone(thread["shop_phone"])
    conversation = json.loads(refreshed["conversation"]) if refreshed else json.loads(thread["conversation"])

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

    # complete — price and genuine/aftermarket both known, safe to forward to mechanic
    forward_update_to_mechanic(thread, parsed)
    reply = "Great, thank you! Let me confirm this with the mechanic and I'll get back to you shortly."
    db.append_thread_conversation(thread["id"], "llm", reply)
    return reply