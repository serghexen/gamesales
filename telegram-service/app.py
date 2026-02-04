import os
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
API_KEY = os.getenv("TELEGRAM_API_KEY", "")

app = FastAPI()


def _require_api_key(key: str | None):
    if not API_KEY:
        return
    if not key or key != API_KEY:
        raise HTTPException(401, "Unauthorized")


def _client(session_string: str):
    if not API_ID or not API_HASH:
        raise HTTPException(500, "Telegram API credentials missing")
    return TelegramClient(StringSession(session_string or ""), API_ID, API_HASH)


class AuthStartIn(BaseModel):
    phone: str
    session_string: str | None = ""


class AuthConfirmIn(BaseModel):
    phone: str
    code: str
    phone_code_hash: str
    session_string: str | None = ""


class AuthPasswordIn(BaseModel):
    password: str
    session_string: str | None = ""


class DialogsIn(BaseModel):
    session_string: str
    limit: int = 50


class MessagesIn(BaseModel):
    session_string: str
    chat_id: int
    limit: int = 50


class SendMessageIn(BaseModel):
    session_string: str
    chat_id: int
    text: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/auth/start")
async def auth_start(payload: AuthStartIn, x_api_key: str | None = Header(None)):
    _require_api_key(x_api_key)
    client = _client(payload.session_string or "")
    await client.connect()
    try:
        result = await client.send_code_request(payload.phone)
        return {
            "phone_code_hash": result.phone_code_hash,
            "session_string": client.session.save(),
        }
    finally:
        await client.disconnect()


@app.post("/auth/confirm")
async def auth_confirm(payload: AuthConfirmIn, x_api_key: str | None = Header(None)):
    _require_api_key(x_api_key)
    client = _client(payload.session_string or "")
    await client.connect()
    try:
        try:
            await client.sign_in(
                phone=payload.phone,
                code=payload.code,
                phone_code_hash=payload.phone_code_hash,
            )
        except SessionPasswordNeededError:
            return {"status": "password_required", "session_string": client.session.save()}
        except PhoneCodeInvalidError:
            raise HTTPException(400, "Invalid code")
        except PhoneCodeExpiredError:
            raise HTTPException(400, "Code expired")
        return {"status": "ok", "session_string": client.session.save()}
    finally:
        await client.disconnect()


@app.post("/auth/password")
async def auth_password(payload: AuthPasswordIn, x_api_key: str | None = Header(None)):
    _require_api_key(x_api_key)
    client = _client(payload.session_string or "")
    await client.connect()
    try:
        try:
            await client.sign_in(password=payload.password)
        except Exception as exc:
            raise HTTPException(400, f"Password error: {exc}")
        return {"status": "ok", "session_string": client.session.save()}
    finally:
        await client.disconnect()


@app.post("/dialogs")
async def dialogs(payload: DialogsIn, x_api_key: str | None = Header(None)):
    _require_api_key(x_api_key)
    client = _client(payload.session_string or "")
    await client.connect()
    try:
        items = []
        async for d in client.iter_dialogs(limit=payload.limit):
            entity = d.entity
            items.append(
                {
                    "id": int(d.id),
                    "title": d.title or "",
                    "unread_count": d.unread_count or 0,
                    "is_group": bool(getattr(entity, "megagroup", False)) or bool(getattr(entity, "broadcast", False)),
                    "is_channel": bool(getattr(entity, "broadcast", False)),
                }
            )
        return {"items": items}
    finally:
        await client.disconnect()


@app.post("/messages")
async def messages(payload: MessagesIn, x_api_key: str | None = Header(None)):
    _require_api_key(x_api_key)
    client = _client(payload.session_string or "")
    await client.connect()
    try:
        msgs = await client.get_messages(payload.chat_id, limit=payload.limit)
        items = []
        for m in msgs:
            items.append(
                {
                    "id": int(m.id),
                    "text": m.message or "",
                    "date": m.date.isoformat() if m.date else None,
                    "out": bool(getattr(m, "out", False)),
                    "sender_id": int(m.sender_id) if m.sender_id else None,
                }
            )
        return {"items": items}
    finally:
        await client.disconnect()


@app.post("/messages/send")
async def send_message(payload: SendMessageIn, x_api_key: str | None = Header(None)):
    _require_api_key(x_api_key)
    if not payload.text:
        raise HTTPException(400, "Message text required")
    client = _client(payload.session_string or "")
    await client.connect()
    try:
        await client.send_message(payload.chat_id, payload.text)
        return {"ok": True}
    finally:
        await client.disconnect()
