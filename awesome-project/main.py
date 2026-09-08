from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import uvicorn
import db
from memory import with_memory


db.init_db()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

LLM_URL = "https://mayflower-lily-clique.ngrok-free.dev/generate"

class Message(BaseModel):
    text: str

chat_history = []

@app.get("/")
async def form():
    return FileResponse("static/index.html")

@app.post("/chat")
@with_memory(limit=10)
async def chat(msg: Message, context: str):
    r = requests.post(LLM_URL, json={"text": context})
    return r.json()

@app.get("/history")
async def history():
    return db.get_history()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)