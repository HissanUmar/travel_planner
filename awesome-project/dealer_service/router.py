# Dealer-side endpoints go here: broadcasting part requests to dealers,
# parsing dealer replies (availability, price, genuine/aftermarket, photos).
# Stub for now — build out logic.py and prompts.py alongside this
# following the same pattern as mechanic_service.

from fastapi import APIRouter, HTTPException
import db
from .logic import broadcast_to_dealers

router = APIRouter()

@router.get("/dealer-threads/{request_id}")
async def get_dealer_threads(request_id: int):
    return db.get_threads_for_request(request_id)