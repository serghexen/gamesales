import os
import json
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import redis

app = FastAPI(title="Notifications Queue API")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
API_KEY = os.getenv("QUEUE_API_KEY", "")
STATUS_TTL_SEC = int(os.getenv("IMPORT_STATUS_TTL_SEC", "86400"))

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def require_api_key(x_api_key: Optional[str]):
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


class QueueMessage(BaseModel):
    payload: str


class StatusPayload(BaseModel):
    data: Dict[str, Any]


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/queue/{name}/push")
def push_message(name: str, msg: QueueMessage, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    redis_client.rpush(name, msg.payload)
    return {"ok": True}


@app.post("/queue/{name}/pop")
def pop_message(name: str, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    value = redis_client.lpop(name)
    return {"ok": True, "payload": value}


@app.get("/queue/{name}/len")
def queue_length(name: str, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    length = redis_client.llen(name)
    return {"ok": True, "length": length}


@app.get("/queue/{name}/peek")
def queue_peek(name: str, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    value = redis_client.lindex(name, 0)
    return {"ok": True, "payload": value}


@app.get("/status/{job_id}")
def get_status(job_id: str, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    raw = redis_client.get(f"games_import:{job_id}")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


@app.post("/status/{job_id}")
def set_status(job_id: str, payload: StatusPayload, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    redis_client.setex(f"games_import:{job_id}", STATUS_TTL_SEC, json.dumps(payload.data))
    return {"ok": True}


@app.delete("/status/{job_id}")
def delete_status(job_id: str, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    redis_client.delete(f"games_import:{job_id}")
    return {"ok": True}
