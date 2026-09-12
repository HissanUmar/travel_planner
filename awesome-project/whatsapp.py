import requests
import os
from dotenv import load_dotenv

load_dotenv()

import logging

logger = logging.getLogger(__name__)

PHONE_NUMBER_ID = os.getenv("WA_PHONE_NUMBER_ID", "")
ACCESS_TOKEN = os.getenv("WA_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.getenv("WA_VERIFY_TOKEN", "")

def send_message(to: str, text: str) -> dict:
    """Sends a WhatsApp text message via Meta Graph API.
    Does not crash on HTTP or network errors; logs and returns status dict.
    """
    if not PHONE_NUMBER_ID or not ACCESS_TOKEN:
        logger.warning(f"Cannot send WhatsApp message to {to}: WA_PHONE_NUMBER_ID or WA_ACCESS_TOKEN is not configured.")
        return {"success": False, "error": "Missing WhatsApp credentials"}

    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        return {"success": True, "data": r.json()}
    except Exception as e:
        logger.error(f"WhatsApp send_message to {to} failed: {e}")
        return {"success": False, "error": str(e)}

def extract_incoming(body: dict):
    """Returns (from_number, text, message_id) or (None, None, None) if not a text message."""
    try:
        value = body["entry"][0]["changes"][0]["value"]
        message = value["messages"][0]
        return message["from"], message["text"]["body"], message["id"]
    except (KeyError, IndexError):
        return None, None, None
