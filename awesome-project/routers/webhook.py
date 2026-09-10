from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import requests
from config import LLM_URL
import db
import whatsapp
from dealer_service.logic import handle_dealer_reply

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
    from_number, text, msg_id = whatsapp.extract_incoming(body)

    if from_number is None:
        return {"status": "ignored"}

    if db.message_already_processed(msg_id):
        return {"status": "duplicate"}

    db.save_whatsapp_message(from_number, "in", text, msg_id)

    # Check: is this a dealer replying about a specific part request?
    thread = db.get_open_thread_by_phone(from_number)
    if thread:
        try:
            reply_text = handle_dealer_reply(thread, text)
        except Exception as e:
            import traceback
            print("DEALER REPLY ERROR:", e)
            traceback.print_exc()
            reply_text = "Got it, thanks."
        whatsapp.send_message(from_number, reply_text)
        db.save_whatsapp_message(from_number, "out", reply_text)
        return {"status": "dealer_reply_handled"}

    shop = db.get_shop_by_phone(from_number)
    if shop:
        reply_text = handle_cold_dealer_message(shop, text)
        whatsapp.send_message(from_number, reply_text)
        db.save_whatsapp_message(from_number, "out", reply_text)
        return {"status": "cold_dealer_handled"}


    # Otherwise, fall back to generic chat LLM flow
    try:
        history = db.get_recent_history(limit=10)
        context = "".join(
            f"User: {h['user_message']}\nAssistant: {h['bot_response']}\n"
            for h in history
        )
        context += f"User: {text}\nAssistant:"

        r = requests.post(LLM_URL, json={"text": context}, timeout=10)
        response = r.json()
        reply_text = response.get("response") or response.get("text") or response.get("message") or str(response)
    except Exception:
        reply_text = "Sorry, I'm having trouble responding right now."

    db.save_message(text, reply_text)
    whatsapp.send_message(from_number, reply_text)
    db.save_whatsapp_message(from_number, "out", reply_text)

    return {"status": "sent"}