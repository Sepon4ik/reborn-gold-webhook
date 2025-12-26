import os
import json
from datetime import datetime, timezone

import requests
from fastapi import FastAPI, Request, HTTPException, Query

# ===== ENV =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TV_SECRET = os.getenv("TV_SECRET")

if not BOT_TOKEN or not CHAT_ID or not TV_SECRET:
    raise RuntimeError("Missing environment variables (BOT_TOKEN, CHAT_ID, TV_SECRET)")

app = FastAPI()

# ===== LOGGING =====
LOG_FILE = os.getenv("LOG_FILE", "signals.log")  # можно поменять через ENV, но не обязательно


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def log_event(event: str, payload: dict):
    """
    Пишем лог и в stdout (Render Logs), и в файл (JSONL).
    """
    record = {
        "ts": now_iso(),
        "event": event,
        "payload": payload,
    }

    line = json.dumps(record, ensure_ascii=False)

    # 1) stdout — видно в Render -> Logs
    print(line, flush=True)

    # 2) файл — на всякий случай (на free может быть не-персистентно)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        # если файл не пишется — не валим сервис
        print(json.dumps({"ts": now_iso(), "event": "log_file_write_error", "error": str(e)}, ensure_ascii=False),
              flush=True)


# ===== ROUTES =====
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
    return r


@app.post("/tv-webhook")
async def tv_webhook(
    request: Request,
    secret: str = Query(...),   # <-- ВАЖНО: secret берём из query (?secret=...)
):
    # 1) проверка секрета
    if secret != TV_SECRET:
        log_event("tv_webhook_invalid_secret", {
            "remote": request.client.host if request.client else None,
            "provided_secret": secret
        })
        raise HTTPException(status_code=403, detail="Invalid secret")

    # 2) читаем JSON от TradingView
    data = await request.json()

    log_event("tv_webhook_received", {
        "remote": request.client.host if request.client else None,
        "data": data
    })

    # 3) формируем текст (пока простой — ты дальше скажешь формат "GOLD SELL NOW...")
    #   сейчас берём то, что пришло: symbol/side/price/timeframe
    symbol = data.get("symbol")
    side = data.get("side")
    price = data.get("price")
    tf = data.get("timeframe")

    text = (
        f"📈 {symbol}\n"
        f"Side: {side}\n"
        f"Price: {price}\n"
        f"TF: {tf}"
    )

    # 4) отправляем в Telegram + логируем результат
    try:
        resp = send_telegram(text)
        ok = resp.ok
        body = None
        try:
            body = resp.json()
        except Exception:
            body = resp.text

        log_event("telegram_send_result", {
            "ok": ok,
            "status_code": resp.status_code,
            "response": body
        })

        if not ok:
            raise RuntimeError(f"Telegram error: {resp.status_code} {resp.text}")

    except Exception as e:
        log_event("telegram_send_error", {"error": str(e)})
        raise

    return {"ok": True}
