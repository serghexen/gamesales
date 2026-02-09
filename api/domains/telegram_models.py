from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel


class TelegramAuthStartIn(BaseModel):
    phone: str


class TelegramAuthConfirmIn(BaseModel):
    code: str


class TelegramAuthPasswordIn(BaseModel):
    password: str


class TelegramDialogsOut(BaseModel):
    items: list
    counts: Dict[str, int] = {}
    sync_running: bool = False
    last_sync_at: Optional[datetime] = None
    sync_loaded: int = 0
    sync_batches: int = 0


class TelegramMessagesOut(BaseModel):
    items: list


class TelegramSendMessageIn(BaseModel):
    chat_id: int
    text: str


class TelegramDialogStatusIn(BaseModel):
    status: str


class TelegramContactIn(BaseModel):
    sender_id: int
    title: str = ""
    info: str = ""
