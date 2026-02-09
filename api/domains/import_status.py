from dataclasses import dataclass
import json
from typing import Callable
import urllib.error
import urllib.request

from fastapi import HTTPException
import redis


@dataclass
class ImportStatusStore:
    is_import_cancelled: Callable[[str], bool]
    set_import_progress: Callable[[str, str, dict], None]
    get_import_progress: Callable[[str], dict]
    clear_import_progress: Callable[[str], None]


def build_import_status_store(
    *,
    import_status_ttl_sec: int,
    queue_api_url: str,
    queue_api_key: str,
    redis_url: str,
) -> ImportStatusStore:
    redis_client = None

    def get_redis():
        nonlocal redis_client
        if redis_client is None:
            redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
        return redis_client

    def job_key(job_id: str) -> str:
        return f"import:status:{job_id}"

    def queue_api_request(method: str, path: str, data: dict | None = None) -> dict | None:
        if not queue_api_url:
            return None
        url = queue_api_url.rstrip("/") + path
        body = None
        headers = {"Content-Type": "application/json"}
        if queue_api_key:
            headers["X-API-Key"] = queue_api_key
        if data is not None:
            body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read()
                return json.loads(content.decode("utf-8")) if content else {}
        except urllib.error.HTTPError as exc:
            content = exc.read() if hasattr(exc, "read") else b""
            detail = content.decode("utf-8", errors="ignore") if content else str(exc)
            raise HTTPException(exc.code or 502, f"Queue API error: {detail}")
        except urllib.error.URLError as exc:
            raise HTTPException(502, f"Queue API unavailable: {exc}")

    def get_import_progress(job_id: str) -> dict:
        if queue_api_url:
            try:
                return queue_api_request("GET", f"/status/{job_id}") or {}
            except Exception as exc:
                print(f"Queue API status read failed: {exc}")
                return {}
        r = get_redis()
        raw = r.get(job_key(job_id))
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def is_import_cancelled(job_id: str) -> bool:
        status = get_import_progress(job_id)
        return bool(status.get("cancelled"))

    def set_import_progress(job_id: str, owner: str, payload: dict):
        data = {"owner": owner}
        data.update(payload)
        if queue_api_url:
            try:
                queue_api_request("POST", f"/status/{job_id}", {"data": data})
            except Exception as exc:
                print(f"Queue API status update failed: {exc}")
            return
        r = get_redis()
        r.setex(job_key(job_id), import_status_ttl_sec, json.dumps(data))

    def clear_import_progress(job_id: str):
        if queue_api_url:
            try:
                queue_api_request("DELETE", f"/status/{job_id}")
            except Exception as exc:
                print(f"Queue API status delete failed: {exc}")
            return
        r = get_redis()
        r.delete(job_key(job_id))

    return ImportStatusStore(
        is_import_cancelled=is_import_cancelled,
        set_import_progress=set_import_progress,
        get_import_progress=get_import_progress,
        clear_import_progress=clear_import_progress,
    )
