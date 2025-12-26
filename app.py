import os
import requests
from fastapi import FastAPI, Request, HTTPException

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TV_SECRET = os.getenv("TV_SECRET")

if not BOT_TOKEN or not CHAT_ID or not TV_SECRET:
    raise RuntimeError("Missing environment variables")

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ok"}


def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": text},
        timeout=20
    )
    if not r.ok:
        raise RuntimeError(r.text)


@app.post("/tv-webhook")
async def tv_webhook(request: Request):
    data = await request.json()

    # проверка секрета
    if data.get("secret") != TV_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    text = (
        f"📊 {data.get('symbol')}\n"
        f"Side: {data.get('side')}\n"
        f"Price: {data.get('price')}\n"
        f"TF: {data.get('timeframe')}"
    )

    send_telegram(text)
    return {"ok": True}
