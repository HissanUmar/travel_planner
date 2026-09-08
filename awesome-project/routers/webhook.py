from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import requests
import db
import whatsapp
from routers.chat import LLM_URL

router = APIRouter()

@router.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == whatsapp.VERIFY_TOKEN:
        return PlainTextResponse(params.get("hub.challenge"))
    return PlainTextResponse("invalid token", status_code=403)

@router.post("/webhook")
async def receive_webhook(request: Request):
    body = await request.json()
    from_number, text = whatsapp.extract_incoming(body)

    if from_number is None:
        return {"status": "ignored"}

    db.save_whatsapp_message(from_number, "in", text)

    history = db.get_recent_history(limit=10)
    context = "".join(
        f"User: {h['user_message']}\nAssistant: {h['bot_response']}\n"
        for h in history
    )
    context += f"User: {text}\nAssistant:"

    r = requests.post(LLM_URL, json={"text": context})
    response = r.json()
    reply_text = response.get("text") or response.get("message") or str(response)

    db.save_message(text, reply_text)
    whatsapp.send_message(from_number, reply_text)
    db.save_whatsapp_message(from_number, "out", reply_text)

    return {"status": "sent"}