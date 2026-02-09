from dataclasses import dataclass
from typing import Callable, Optional
import json
import socket
import threading
import time
import urllib.error
import urllib.request

from fastapi import HTTPException


@dataclass
class TelegramSyncService:
    telegram_api_request: Callable[..., dict]
    telegram_api_request_raw: Callable[..., tuple[bytes, Optional[str]]]
    upsert_telegram_dialog_snapshot: Callable[[object, int, list[dict]], None]
    delete_dead_dialog: Callable[[object, int], None]
    trigger_telegram_dialogs_sync: Callable[[str, int], bool]
    get_sync_stats: Callable[[], tuple[bool, int, int]]


def build_telegram_sync_service(
    *,
    DB_DSN,
    psycopg,
    q1,
    exec1,
    telegram_api_url: str,
    telegram_api_key: str,
    sync_limit: int,
    sync_batch: int,
    sync_cooldown_sec: int,
    sync_batch_delay_ms: int,
) -> TelegramSyncService:
    sync_lock = threading.Lock()
    sync_running = False
    sync_last_started_mono = 0.0
    sync_loaded = 0
    sync_batches = 0

    def telegram_api_request(method: str, path: str, data: Optional[dict] = None, timeout_sec: int = 15) -> dict:
        if not telegram_api_url:
            raise HTTPException(500, "Telegram service is not configured")
        url = telegram_api_url.rstrip("/") + path
        body = None
        headers = {"Content-Type": "application/json"}
        if telegram_api_key:
            headers["X-API-Key"] = telegram_api_key
        if data is not None:
            body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                content = resp.read()
                return json.loads(content.decode("utf-8")) if content else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            details = raw.decode("utf-8", errors="ignore") if raw else ""
            message = f"Telegram service {method} {path} failed: {exc.code} {exc.reason}"
            if details:
                message = f"{message}. {details}"
            raise HTTPException(exc.code, message)
        except urllib.error.URLError as exc:
            raise HTTPException(502, f"Telegram service {method} {path} failed: {exc.reason}")
        except (TimeoutError, socket.timeout):
            raise HTTPException(504, f"Telegram service {method} {path} timed out")

    def telegram_api_request_raw(method: str, path: str, data: Optional[dict] = None) -> tuple[bytes, Optional[str]]:
        if not telegram_api_url:
            raise HTTPException(500, "Telegram service is not configured")
        url = telegram_api_url.rstrip("/") + path
        body = None
        headers = {"Content-Type": "application/json"}
        if telegram_api_key:
            headers["X-API-Key"] = telegram_api_key
        if data is not None:
            body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
                content_type = resp.headers.get("Content-Type")
                return content or b"", content_type
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            details = raw.decode("utf-8", errors="ignore") if raw else ""
            message = f"Telegram service {method} {path} failed: {exc.code} {exc.reason}"
            if details:
                message = f"{message}. {details}"
            raise HTTPException(exc.code, message)
        except urllib.error.URLError as exc:
            raise HTTPException(502, f"Telegram service {method} {path} failed: {exc.reason}")
        except (TimeoutError, socket.timeout):
            raise HTTPException(504, f"Telegram service {method} {path} timed out")

    def upsert_telegram_dialog_snapshot(conn, user_id: int, items: list[dict]):
        if not items:
            return
        payload = []
        chat_ids = []
        archived_with_unread = []
        for item in items:
            raw_id = item.get("id")
            if raw_id is None:
                continue
            chat_id = int(raw_id)
            title = str(item.get("title") or "")
            unread_count = int(item.get("unread_count") or 0)
            is_group = bool(item.get("is_group"))
            is_channel = bool(item.get("is_channel"))
            payload.append((chat_id, title, unread_count, is_group, is_channel))
            chat_ids.append(chat_id)
            if unread_count > 0:
                archived_with_unread.append(chat_id)

        if not payload:
            return

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO tg.dialog_snapshot(chat_id, title, unread_count, is_group, is_channel, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (chat_id)
                DO UPDATE SET
                  title=excluded.title,
                  unread_count=excluded.unread_count,
                  is_group=excluded.is_group,
                  is_channel=excluded.is_channel,
                  updated_at=now()
                """,
                payload,
            )
            cur.executemany(
                """
                INSERT INTO tg.dialog_states(chat_id, status, updated_at, updated_by_user_id)
                VALUES (%s, 'new', now(), %s)
                ON CONFLICT (chat_id) DO NOTHING
                """,
                [(cid, user_id) for cid in chat_ids],
            )

        if archived_with_unread:
            exec1(
                conn,
                """
                UPDATE tg.dialog_states
                SET status='accepted', updated_at=now(), updated_by_user_id=%s
                WHERE chat_id = ANY(%s) AND status='archived'
                """,
                (user_id, archived_with_unread),
            )

    def delete_unseen_dialogs_from_snapshot(conn, seen_chat_ids: list[int]):
        if not seen_chat_ids:
            return
        exec1(
            conn,
            "DELETE FROM tg.dialog_snapshot WHERE NOT (chat_id = ANY(%s))",
            (seen_chat_ids,),
        )

    def delete_dead_dialog(conn, chat_id: int):
        exec1(conn, "DELETE FROM tg.dialog_snapshot WHERE chat_id=%s", (chat_id,))

    def telegram_fetch_dialog_batch_with_retry(
        session_string: str,
        limit: int,
        offset_date: Optional[str],
        offset_id: int,
    ) -> dict:
        delays = (0, 2, 5)
        last_exc: Optional[HTTPException] = None
        for idx, delay_sec in enumerate(delays):
            if delay_sec > 0:
                time.sleep(delay_sec)
            try:
                return telegram_api_request(
                    "POST",
                    "/dialogs",
                    {
                        "session_string": session_string,
                        "limit": limit,
                        "offset_date": offset_date,
                        "offset_id": offset_id,
                        "only_private": True,
                    },
                    timeout_sec=45,
                )
            except HTTPException as exc:
                last_exc = exc
                if exc.status_code not in (429, 502, 504) or idx == len(delays) - 1:
                    raise
        if last_exc:
            raise last_exc
        return {"items": [], "has_more": False, "next_offset_date": None, "next_offset_id": 0}

    def telegram_dialogs_sync_worker(session_string: str, user_id: int):
        nonlocal sync_running, sync_loaded, sync_batches
        try:
            configured_sync_limit = sync_limit if sync_limit > 0 else None
            batch_size = sync_batch if sync_batch > 0 else 100
            batch_delay_sec = max(sync_batch_delay_ms, 0) / 1000.0
            offset_date: Optional[str] = None
            offset_id = 0
            total_loaded = 0
            rounds = 0
            seen_chat_ids: list[int] = []
            completed_full_scan = False
            with psycopg.connect(DB_DSN) as conn:
                while True:
                    if configured_sync_limit is not None:
                        remaining = max(configured_sync_limit - total_loaded, 0)
                        if remaining <= 0:
                            break
                        current_batch = min(batch_size, remaining)
                    else:
                        current_batch = batch_size
                    resp = telegram_fetch_dialog_batch_with_retry(session_string, current_batch, offset_date, offset_id)
                    items = resp.get("items", []) or []
                    if not items:
                        completed_full_scan = True
                        break
                    upsert_telegram_dialog_snapshot(conn, user_id, items)
                    for item in items:
                        if item.get("id") is not None:
                            seen_chat_ids.append(int(item["id"]))
                    conn.commit()
                    total_loaded += len(items)
                    rounds += 1
                    with sync_lock:
                        sync_loaded = total_loaded
                        sync_batches = rounds
                    has_more = bool(resp.get("has_more"))
                    if not has_more:
                        completed_full_scan = True
                        break
                    offset_date = resp.get("next_offset_date")
                    offset_id = int(resp.get("next_offset_id") or 0)
                    if not offset_date or rounds > 500:
                        break
                    if batch_delay_sec > 0:
                        time.sleep(batch_delay_sec)
                if completed_full_scan and seen_chat_ids:
                    delete_unseen_dialogs_from_snapshot(conn, seen_chat_ids)
                exec1(conn, "UPDATE tg.shared_session SET last_used_at=now() WHERE id=1")
                conn.commit()
        except Exception as exc:
            print(f"Telegram dialogs sync failed: {exc}")
        finally:
            with sync_lock:
                sync_running = False

    def trigger_telegram_dialogs_sync(session_string: str, user_id: int) -> bool:
        nonlocal sync_running, sync_last_started_mono, sync_loaded, sync_batches
        now_mono = time.monotonic()
        with sync_lock:
            if sync_running:
                return False
            if (now_mono - sync_last_started_mono) < sync_cooldown_sec:
                return False
            sync_running = True
            sync_last_started_mono = now_mono
            sync_loaded = 0
            sync_batches = 0
        thread = threading.Thread(
            target=telegram_dialogs_sync_worker,
            args=(session_string, user_id),
            daemon=True,
        )
        thread.start()
        return True

    def get_sync_stats() -> tuple[bool, int, int]:
        with sync_lock:
            return bool(sync_running), int(sync_loaded), int(sync_batches)

    return TelegramSyncService(
        telegram_api_request=telegram_api_request,
        telegram_api_request_raw=telegram_api_request_raw,
        upsert_telegram_dialog_snapshot=upsert_telegram_dialog_snapshot,
        delete_dead_dialog=delete_dead_dialog,
        trigger_telegram_dialogs_sync=trigger_telegram_dialogs_sync,
        get_sync_stats=get_sync_stats,
    )
