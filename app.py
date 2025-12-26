import os
import json
import requests
from fastapi import FastAPI, Request, HTTPException, Query

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TV_SECRET = os.getenv("TV_SECRET")

if not BOT_TOKEN or not CHAT_ID or not TV_SECRET:
    raise RuntimeError("Missing environment variables (BOT_TOKEN, CHAT_ID, TV_SECRET)")

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ok"}


def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=20)
    if not r.ok:
        raise RuntimeError(r.text)


def build_gold_message(data: dict) -> str:
    # ожидаем такие ключи:
    # side: "SELL" / "BUY"
    # entry_from, entry_to
    # sl
    # tps: список тейков (или tp1..tp5)
    side = (data.get("side") or "").upper() or "SELL"

    entry_from = data.get("entry_from")
    entry_to = data.get("entry_to")

    sl = data.get("sl")

    tps = data.get("tps")
    if not isinstance(tps, list):
        # если пришли отдельные tp1..tp5
        tps = []
        for k in ["tp1", "tp2", "tp3", "tp4", "tp5"]:
            v = data.get(k)
            if v not in (None, "", "na"):
                tps.append(v)

    lines = []

    # 1 строка как ты хочешь:
    if entry_from is not None and entry_to is not None:
        lines.append(f"GOLD {side} NOW {entry_from}-{entry_to}")
    else:
        # запасной вариант, если диапазон не передали
        price = data.get("price")
        lines.append(f"GOLD {side} NOW {price}" if price is not None else f"GOLD {side} NOW")

    if sl is not None:
        lines.append(f"SL {sl}")

    for tp in tps:
        lines.append(f"TP {tp}")

    # (опционально) таймфрейм
    tf = data.get("tf") or data.get("timeframe")
    if tf:
        lines.append(f"TF {tf}")

    return "\n".join(lines)


@app.post("/tv-webhook")
async def tv_webhook(secret: str = Query(...), request: Request = None):
    # 1) секрет только из query: ?secret=...
    if secret != TV_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    # 2) пытаемся принять JSON, но TradingView иногда шлёт plain text
    body = await request.body()
    raw = body.decode("utf-8", errors="ignore").strip()

    data = None
    try:
        data = json.loads(raw) if raw else {}
    except Exception:
        # если пришёл просто текст — отправим как есть
        send_telegram(raw if raw else "Empty alert")
        return {"ok": True, "mode": "text"}

    msg = build_gold_message(data)
    send_telegram(msg)
    return {"ok": True, "mode": "json"}
