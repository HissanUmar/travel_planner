from fastapi import APIRouter
from pydantic import BaseModel
import db
import whatsapp
from llm_extraction import extract_fields, generate_clarification

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
    request = db.get_request(request["id"])  # refresh with new conversation

    fields = extract_fields(request["conversation"] and __import__("json").loads(request["conversation"]) or [])
    db.update_fields(request["id"], fields)
    request = db.get_request(request["id"])

    missing = db.missing_fields(request)

    if missing:
        clarification = generate_clarification(missing)
        db.append_conversation(request["id"], "llm", clarification)
        whatsapp.send_message(msg.phone, clarification)
        return {"status": "clarifying", "missing": missing, "request_id": request["id"], "message": clarification}
    else:
        db.set_status(request["id"], "BROADCASTING")
        summary = (
            f"Got it — {request['car_model']} {request['car_variant']} ({request['car_year']}), "
            f"{request['part_name']}, {request['spec']}, {request['genuine_pref']}. "
            f"Checking with dealers now, will update you."
        )
        db.append_conversation(request["id"], "llm", summary)
        whatsapp.send_message(msg.phone, summary)
        return {"status": "ready_for_dealers", "request": request, "message": summary}