from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
import db
import asyncio
from dotenv import load_dotenv
load_dotenv()

from mechanic_service.router import router as mechanic_router
from dealer_service.router import router as dealer_router
from routers import webhook, chat, conversations, parts

db.init_all()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(mechanic_router)
app.include_router(dealer_router)
app.include_router(webhook.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(parts.router)

async def stale_thread_checker():
    while True:
        try:
            closed = check_stale_threads(hours=6)
            if closed:
                print(f"Closed {closed} stale dealer thread(s)")
        except Exception as e:
            print("Stale thread check error:", e)
        await asyncio.sleep(15 * 60)  # every 15 minutes

@app.on_event("startup")
async def start_background_tasks():
    asyncio.create_task(stale_thread_checker())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
