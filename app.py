app.py
import os
from fastapi import FastAPI, Request, HTTPException
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TV_SECRET = os.getenv("TV_SECRET")

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/tv-webhook")
async def tv_webhook(request: Request, secret: str):
    if secret != TV_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    data = await request.json()

    text = (
        f"📊 {data.get('symbol')} | {data.get('side')}\n"
        f"⏱ TF: {data.get('tf')}\n\n"
        f"📌 Zone: {data.get('zone_low')} - {data.get('zone_high')}\n"
        f"🛑 SL: {data.get('sl')}\n"
        f"🎯 TP1: {data.get('tp1')}\n"
        f"🎯 TP2: {data.get('tp2')}\n"
        f"🎯 TP3: {data.get('tp3')}\n"
        f"🕒 {data.get('time')}"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }

    r = requests.post(url, json=payload)
    if not r.ok:
        raise HTTPException(status_code=500, detail="Telegram error")

    return {"status": "sent"}
