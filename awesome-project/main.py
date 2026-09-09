from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
import db

from routers import chat, webhook, parts, conversations

from routers import mechanic


db.init_all()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(chat.router)
app.include_router(webhook.router)
app.include_router(parts.router)
app.include_router(conversations.router)

app.include_router(mechanic.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)