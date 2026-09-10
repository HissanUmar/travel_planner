from fastapi import APIRouter
from pydantic import BaseModel
import db
import whatsapp

router = APIRouter()

class PartRequest(BaseModel):
    part: str

@router.post("/request-part")
async def request_part(req: PartRequest):
    shop = db.find_shop_for_part(req.part)
    if not shop:
        return {"status": "no matching shop found"}

    message = f"Hi {shop['name']}, do you have {req.part} in stock? Please reply YES or NO."
    whatsapp.send_message(shop["phone"], message)
    db.save_whatsapp_message(shop["phone"], "out", message)

    return {"status": "sent", "shop": shop["name"], "phone": shop["phone"]}
