from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import db
import whatsapp
from .logic import broadcast_to_dealers

router = APIRouter()

class NegotiateMessage(BaseModel):
    text: str

@router.get("/dealer-threads/{request_id}")
async def get_dealer_threads(request_id: int):
    return db.get_threads_for_request(request_id)

@router.post("/dealer-threads/{thread_id}/negotiate")
async def negotiate(thread_id: int, msg: NegotiateMessage):
    thread = db.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread not found")
    whatsapp.send_message(thread["shop_phone"], msg.text)
    db.append_thread_conversation(thread_id, "llm", msg.text)
    db.update_thread(thread_id, status="RESPONDED")
    return {"status": "sent"}

@router.post("/dealer-threads/{thread_id}/confirm")
async def confirm(thread_id: int):
    thread = db.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread not found")
    if not thread.get("price"):
        raise HTTPException(status_code=400, detail="no price on this offer yet")

    ticket_id = db.create_ticket(thread["request_id"], thread)
    db.update_thread(thread_id, status="SELECTED")
    db.set_status(thread["request_id"], "TICKET_CREATED")

    part_name = db.get_request(thread["request_id"])["part_name"]
    confirm_msg = f"Great news — the mechanic has confirmed. Please prepare the {part_name} at PKR {thread['price']}. We'll follow up on delivery details."
    whatsapp.send_message(thread["shop_phone"], confirm_msg)
    db.append_thread_conversation(thread_id, "llm", confirm_msg)

    declined = db.close_other_threads(thread["request_id"], thread_id)
    for d in declined:
        decline_msg = "Thanks for the offer — the mechanic went with another dealer this time. We'll reach out again next time!"
        whatsapp.send_message(d["shop_phone"], decline_msg)
        db.append_thread_conversation(d["id"], "llm", decline_msg)

    db.append_conversation(
        thread["request_id"], "llm",
        f"Ticket #{ticket_id} created with {thread['shop_name']} — PKR {thread['price']}, {thread['is_genuine']}."
    )
    db.mark_unread(thread["request_id"])
    return {"status": "ticket_created", "ticket_id": ticket_id}

@router.post("/dealer-threads/{thread_id}/pursue-alternative")
async def pursue_alternative(thread_id: int):
    thread = db.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread not found")
    whatsapp.send_message(thread["shop_phone"], "The mechanic is interested in your alternative offer — could you confirm the exact price and whether it's genuine or aftermarket?")
    db.append_thread_conversation(thread_id, "llm", "The mechanic is interested in your alternative offer — could you confirm the exact price and whether it's genuine or aftermarket?")
    db.update_thread(thread_id, status="RESPONDED")
    return {"status": "sent"}

@router.post("/dealer-threads/{thread_id}/decline-alternative")
async def decline_alternative(thread_id: int):
    thread = db.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread not found")
    whatsapp.send_message(thread["shop_phone"], "Thanks for the offer, but the mechanic needs the exact part as requested.")
    db.append_thread_conversation(thread_id, "llm", "Thanks for the offer, but the mechanic needs the exact part as requested.")
    return {"status": "declined"}