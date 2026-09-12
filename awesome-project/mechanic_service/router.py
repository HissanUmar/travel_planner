from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import db
import whatsapp
import json
from .logic import extract_fields, generate_clarification, format_confirmation, answer_mechanic_question
from .intent import classify_mechanic_message
from dealer_service.logic import (
    broadcast_to_dealers,
    send_mechanic_answer_to_dealer,
    broadcast_mechanic_message_to_dealers,
    generate_aggregated_report
)

router = APIRouter()

class MechanicMessage(BaseModel):
    phone: str
    text: str
    request_id: Optional[int] = None

class AnswerDealerQuestion(BaseModel):
    text: str

@router.post("/mechanic-message")
async def mechanic_message(msg: MechanicMessage):
    request = None
    if msg.request_id:
        request = db.get_request(msg.request_id)
    if not request:
        request = db.get_open_request(msg.phone)
    if not request:
        request_id = db.create_request(msg.phone)
        request = db.get_request(request_id)

    db.append_conversation(request["id"], "mechanic", msg.text)
    request = db.get_request(request["id"])

    # Confirmation step takes priority over classification
    if request["status"] == "AWAITING_CONFIRMATION":
        if "yes" in msg.text.strip().lower():
            db.set_status(request["id"], "BROADCASTING")
            confirmed_request = db.get_request(request["id"])
            contacted = broadcast_to_dealers(confirmed_request)
            reply = f"Confirmed. Contacted {len(contacted)} dealer(s), checking availability now."
            db.append_conversation(request["id"], "llm", reply)
            return {"status": "confirmed", "request": db.get_request(request["id"]), "contacted": contacted, "message": reply}
        else:
            db.set_status(request["id"], "COLLECTING_INFO")
            request = db.get_request(request["id"])

    # If the request is already broadcasting or tickets are in progress, route intelligently
    if request["status"] in ("BROADCASTING", "REPORT_READY", "TICKET_CREATED"):
        intent = classify_mechanic_message(request, msg.text)

        if intent == "GENERATE_REPORT":
            report_res = generate_aggregated_report(request["id"])
            return {"status": "report_ready", "message": report_res.get("report_text")}

        if intent == "ASKING_QUESTION":
            answer = answer_mechanic_question(request, msg.text)
            db.append_conversation(request["id"], "llm", answer)
            return {"status": "question_answered", "message": answer}

        if intent == "REQUESTING_CHANGE":
            reply = "This request is already locked in with dealers — I can't change it now. Cancel this request and start a new one if the details need to change."
            db.append_conversation(request["id"], "llm", reply)
            return {"status": "change_denied", "message": reply}

        # Default for active requests: broadcast message to all active dealers
        sent_dealers = broadcast_mechanic_message_to_dealers(request["id"], msg.text)
        if sent_dealers:
            reply = f"Broadcasted your message to {len(sent_dealers)} dealer(s) ({', '.join(sent_dealers)}). Their replies will appear in their chat tabs."
        else:
            reply = "No active dealers currently connected to receive this message."
        db.append_conversation(request["id"], "llm", reply)
        return {"status": "broadcast_to_dealers", "message": reply, "sent_to": sent_dealers}

    intent = classify_mechanic_message(request, msg.text)

    if intent == "ASKING_QUESTION":
        answer = answer_mechanic_question(request, msg.text)
        db.append_conversation(request["id"], "llm", answer)
        return {"status": "question_answered", "message": answer}

    if intent == "REQUESTING_CHANGE":
        if request["status"] in ("COLLECTING_INFO", "AWAITING_CONFIRMATION"):
            pass  # fall through to normal extraction — still editable
        else:
            reply = "This request is already locked in with dealers — I can't change it now. Cancel this request and start a new one if the details need to change."
            db.append_conversation(request["id"], "llm", reply)
            return {"status": "change_denied", "message": reply}

    # default: PROVIDING_FIELDS (or REQUESTING_CHANGE while still editable)
    conversation = json.loads(request["conversation"])
    fields = extract_fields(conversation)
    db.update_fields(request["id"], fields)
    request = db.get_request(request["id"])

    missing = db.missing_fields(request)

    if missing:
        clarification = generate_clarification(missing)
        db.append_conversation(request["id"], "llm", clarification)
        return {"status": "clarifying", "missing": missing, "request_id": request["id"], "message": clarification}

    db.set_status(request["id"], "AWAITING_CONFIRMATION")
    confirmation = format_confirmation(request)
    db.append_conversation(request["id"], "llm", confirmation)
    return {"status": "awaiting_confirmation", "request": request, "message": confirmation}

@router.post("/mechanic-requests/{request_id}/generate-report")
async def generate_report_route(request_id: int):
    return generate_aggregated_report(request_id)

@router.post("/mechanic-requests/{request_id}/mark-read")
async def mark_read(request_id: int):
    db.mark_read(request_id)
    return {"status": "ok"}

@router.post("/mechanic-requests/{request_id}/cancel")
async def cancel_request(request_id: int):
    db.set_status(request_id, "CANCELLED")
    db.append_conversation(request_id, "llm", "Request cancelled.")
    return {"status": "cancelled"}

@router.post("/mechanic-requests/{request_id}/ping-dealers")
async def ping_dealers(request_id: int):
    threads = db.get_threads_for_request(request_id)
    pinged = 0
    msg = "Just checking in — any update on availability/price?"
    for t in threads:
        if t["status"] in ("CONTACTED", "RESPONDED"):
            db.append_thread_conversation(t["id"], "llm", msg)
            whatsapp.send_message(t["shop_phone"], msg)
            pinged += 1
    return {"status": "pinged", "count": pinged}

@router.get("/mechanic-requests/{request_id}")
async def get_mechanic_request(request_id: int):
    request = db.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="not found")
    request["conversation"] = json.loads(request["conversation"])
    if request.get("pending_dealer_question"):
        request["pending_dealer_question"] = json.loads(request["pending_dealer_question"])
    return request

@router.get("/mechanic-requests")
async def list_mechanic_requests(phone: str = None):
    return db.get_requests_for_phone(phone) if phone else db.get_all_requests()