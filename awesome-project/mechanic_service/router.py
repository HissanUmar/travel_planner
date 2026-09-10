from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import db
import whatsapp
import json
from .logic import extract_fields, generate_clarification, format_confirmation
from dealer_service.logic import broadcast_to_dealers

router = APIRouter()

class MechanicMessage(BaseModel):
    phone: str
    text: str

@router.post("/mechanic-message")
async def mechanic_message(msg: MechanicMessage):
    request = db.get_open_request(msg.phone)
    if not request:
        request_id = db.create_request(msg.phone)
        request = db.get_request(request_id)

    db.append_conversation(request["id"], "mechanic", msg.text)
    request = db.get_request(request["id"])

    if request["status"] == "AWAITING_CONFIRMATION":
        if msg.text.strip().lower() in ("yes", "y", "confirm", "correct"):
            db.set_status(request["id"], "BROADCASTING")
            confirmed_request = db.get_request(request["id"])

            contacted = broadcast_to_dealers(confirmed_request)

            reply = f"Confirmed. Contacted {len(contacted)} dealer(s), checking availability now."
            db.append_conversation(request["id"], "llm", reply)
            return {
                "status": "confirmed",
                "request": db.get_request(request["id"]),
                "contacted": contacted,
                "message": reply
            }
        else:
            db.set_status(request["id"], "COLLECTING_INFO")
            request = db.get_request(request["id"])

    conversation = json.loads(request["conversation"])
    fields = extract_fields(conversation)
    db.update_fields(request["id"], fields)
    request = db.get_request(request["id"])

    missing = db.missing_fields(request)

    if missing:
        clarification = generate_clarification(missing)
        db.append_conversation(request["id"], "llm", clarification)
        return {
            "status": "clarifying",
            "missing": missing,
            "request_id": request["id"],
            "message": clarification
        }

    db.set_status(request["id"], "AWAITING_CONFIRMATION")
    confirmation = format_confirmation(request)
    db.append_conversation(request["id"], "llm", confirmation)
    return {
        "status": "awaiting_confirmation",
        "request": request,
        "message": confirmation
    }

@router.get("/mechanic-requests/{request_id}")
async def get_mechanic_request(request_id: int):
    request = db.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="not found")
    request["conversation"] = json.loads(request["conversation"])
    return request

@router.post("/mechanic-requests/{request_id}/mark-read")
async def mark_read(request_id: int):
    db.mark_read(request_id)
    return {"status": "ok"}

@router.get("/mechanic-requests")
async def list_mechanic_requests(phone: str = None):
    return db.get_requests_for_phone(phone) if phone else db.get_all_requests()

@router.post("/mechanic-requests/{request_id}/cancel")
async def cancel_request(request_id: int):
    db.set_status(request_id, "CANCELLED")
    db.append_conversation(request_id, "llm", "Request cancelled.")
    return {"status": "cancelled"}

@router.post("/mechanic-requests/{request_id}/ping-dealers")
async def ping_dealers(request_id: int):
    threads = db.get_threads_for_request(request_id)
    pinged = 0
    for t in threads:
        if t["status"] in ("CONTACTED", "RESPONDED"):
            whatsapp.send_message(t["shop_phone"], "Just checking in — any update on availability/price?")
            db.append_thread_conversation(t["id"], "llm", "Just checking in — any update on availability/price?")
            pinged += 1
    return {"status": "pinged", "count": pinged}

