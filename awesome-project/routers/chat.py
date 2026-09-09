from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import db
from memory import with_memory

router = APIRouter()

LLM_URL = "https://phenomenally-slavish-lilly.ngrok-free.dev/generate"

class Message(BaseModel):
    text: str

@router.get("/")
async def form():
    return FileResponse("static/index.html")

@router.post("/chat")
@with_memory(limit=10)
async def chat(msg: Message, context: str):
    r = requests.post(LLM_URL, json={"text": context})
    return r.json()

@router.get("/history")
async def history():
    return db.get_history()