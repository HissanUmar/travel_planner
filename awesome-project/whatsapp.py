import requests
import os
from dotenv import load_dotenv

load_dotenv()

PHONE_NUMBER_ID = os.environ["WA_PHONE_NUMBER_ID"]
ACCESS_TOKEN = os.environ["WA_ACCESS_TOKEN"]
VERIFY_TOKEN = os.environ["WA_VERIFY_TOKEN"]

def send_message(to: str, text: str):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()

def extract_incoming(body: dict):
    """Returns (from_number, text, message_id) or (None, None, None) if not a text message."""
    try:
        value = body["entry"][0]["changes"][0]["value"]
        message = value["messages"][0]
        return message["from"], message["text"]["body"], message["id"]
    except (KeyError, IndexError):
        return None, None, None
