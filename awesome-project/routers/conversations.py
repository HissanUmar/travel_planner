from fastapi import APIRouter
from pydantic import BaseModel
import db
import whatsapp

router = APIRouter()

class SendRequest(BaseModel):
    text: str

@router.get("/conversations")
async def conversations():
    return db.get_conversations()

@router.get("/conversations/{phone}")
async def conversation(phone: str):
    return db.get_messages(phone)

@router.post("/conversations/{phone}/send")
async def send_to_conversation(phone: str, req: SendRequest):
    whatsapp.send_message(phone, req.text)
    db.save_whatsapp_message(phone, "out", req.text)
    return {"status": "sent"}