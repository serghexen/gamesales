import os
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import Response
from pydantic import BaseModel
from datetime import datetime
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
    offset_date: str | None = None
    offset_id: int = 0


class MessagesIn(BaseModel):
    session_string: str
    chat_id: int
    limit: int = 50


class SendMessageIn(BaseModel):
    session_string: str
    chat_id: int
    text: str

class MediaIn(BaseModel):
    session_string: str
    chat_id: int
    message_id: int

async def _resolve_entity(client: TelegramClient, chat_id: int):
    dialogs = await client.get_dialogs(limit=200)
    for d in dialogs:
        if int(d.id) == int(chat_id):
            return d.entity
    raise HTTPException(404, "Chat not found")

@app.get("/health")
def health():
    return {"ok": True}


@app.post("/auth/start")
async def auth_start(payload: AuthStartIn, x_api_key: str | None = Header(None)):
    _require_api_key(x_api_key)
    if not payload.phone:
        raise HTTPException(400, "Phone is required")
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
        dialogs_limit = int(payload.limit or 0)
        if dialogs_limit <= 0:
            dialogs_limit = 100
        offset_date = None
        if payload.offset_date:
            try:
                offset_date = datetime.fromisoformat(str(payload.offset_date).replace("Z", "+00:00"))
            except Exception:
                raise HTTPException(400, "Invalid offset_date")
        offset_id = int(payload.offset_id or 0)
        items = []
        last_message_date = None
        last_message_id = 0
        async for d in client.iter_dialogs(limit=dialogs_limit, offset_date=offset_date, offset_id=offset_id):
            entity = d.entity
            msg = getattr(d, "message", None)
            if msg and getattr(msg, "date", None):
                last_message_date = msg.date
                last_message_id = int(getattr(msg, "id", 0) or 0)
            items.append(
                {
                    "id": int(d.id),
                    "title": d.title or "",
                    "unread_count": d.unread_count or 0,
                    "is_group": bool(getattr(entity, "megagroup", False)) or bool(getattr(entity, "broadcast", False)),
                    "is_channel": bool(getattr(entity, "broadcast", False)),
                }
            )
        has_more = len(items) >= dialogs_limit and last_message_date is not None
        return {
            "items": items,
            "has_more": has_more,
            "next_offset_date": last_message_date.isoformat() if has_more else None,
            "next_offset_id": last_message_id if has_more else 0,
        }
    finally:
        await client.disconnect()


@app.post("/messages")
async def messages(payload: MessagesIn, x_api_key: str | None = Header(None)):
    _require_api_key(x_api_key)
    client = _client(payload.session_string or "")
    await client.connect()
    try:
        entity = await _resolve_entity(client, payload.chat_id)
        msgs = await client.get_messages(entity, limit=payload.limit)
        items = []
        for m in msgs:
            sender = m.sender
            if sender is None:
                try:
                    sender = await m.get_sender()
                except Exception:
                    sender = None
            sender_username = getattr(sender, "username", None) if sender else None
            sender_title = getattr(sender, "title", None) if sender else None
            first_name = getattr(sender, "first_name", None) if sender else None
            last_name = getattr(sender, "last_name", None) if sender else None
            sender_name = None
            if sender_title:
                sender_name = sender_title
            elif first_name or last_name:
                sender_name = " ".join([p for p in [first_name, last_name] if p])
            media_type = None
            mime_type = None
            if m.photo:
                media_type = "photo"
                mime_type = "image/jpeg"
            elif m.document:
                mime_type = getattr(m.file, "mime_type", None)
                file_ext = getattr(m.file, "ext", "") if getattr(m, "file", None) else ""
                if mime_type == "image/gif" or file_ext.lower() == ".gif":
                    media_type = "gif"
                elif mime_type and mime_type.startswith("video/"):
                    media_type = "video"
                else:
                    media_type = "document"
            items.append(
                {
                    "id": int(m.id),
                    "text": m.message or "",
                    "date": m.date.isoformat() if m.date else None,
                    "out": bool(getattr(m, "out", False)),
                    "sender_id": int(m.sender_id) if m.sender_id else None,
                    "sender_username": sender_username,
                    "sender_name": sender_name,
                    "has_media": bool(m.media),
                    "media_type": media_type,
                    "mime_type": mime_type,
                }
            )
        return {"items": items}
    finally:
        await client.disconnect()

@app.post("/media")
async def media(payload: MediaIn, x_api_key: str | None = Header(None)):
    _require_api_key(x_api_key)
    client = _client(payload.session_string or "")
    await client.connect()
    try:
        entity = await _resolve_entity(client, payload.chat_id)
        msg = await client.get_messages(entity, ids=payload.message_id)
        if not msg or not msg.media:
            raise HTTPException(404, "Media not found")
        data = await client.download_media(msg, file=bytes)
        if not data:
            raise HTTPException(404, "Media not found")
        mime_type = None
        if msg.photo:
            mime_type = "image/jpeg"
        elif msg.document:
            mime_type = getattr(msg.file, "mime_type", None)
        return Response(content=data, media_type=mime_type or "application/octet-stream")
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
        msg = await client.send_message(payload.chat_id, payload.text)
        return {"ok": True, "message_id": int(msg.id) if msg else None}
    finally:
        await client.disconnect()
