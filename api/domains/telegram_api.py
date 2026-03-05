from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.responses import Response

from .telegram_models import (
    TelegramAuthConfirmIn,
    TelegramAuthPasswordIn,
    TelegramAuthStartIn,
    TelegramContactIn,
    TelegramDialogStatusIn,
    TelegramDialogsOut,
    TelegramMessagesOut,
    TelegramSendMessageIn,
)


def mount_telegram_routes(
    app,
    *,
    DB_DSN,
    psycopg,
    q1,
    qall,
    exec1,
    get_user_id,
    get_current_user,
    require_role,
    telegram_api_request,
    telegram_api_request_raw,
    upsert_telegram_dialog_snapshot,
    delete_dead_dialog,
    trigger_telegram_dialogs_sync,
    get_sync_stats,
):
    @app.get("/tg/status")
    def telegram_status(user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT status, phone, session_string FROM tg.shared_session WHERE id=1")
        if not row:
            return {"status": "not_connected", "phone": ""}
        return {
            "status": row[0],
            "phone": row[1] or "",
            "has_session": bool(row[2]),
        }

    @app.post("/tg/auth/start")
    def telegram_auth_start(payload: TelegramAuthStartIn, user=Depends(require_role("admin", "owner"))):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT session_string FROM tg.shared_session WHERE id=1")
            session_string = row[0] if row and row[0] else None
            resp = telegram_api_request("POST", "/auth/start", {"phone": payload.phone, "session_string": session_string})
            exec1(
                conn,
                """
                INSERT INTO tg.shared_session(id, status, phone, phone_code_hash, session_string, updated_at)
                VALUES (1, %s, %s, %s, %s, now())
                ON CONFLICT (id)
                DO UPDATE SET status=excluded.status,
                              phone=excluded.phone,
                              phone_code_hash=excluded.phone_code_hash,
                              session_string=excluded.session_string,
                              updated_at=now()
                """,
                (
                    resp.get("status") or "pending",
                    payload.phone,
                    resp.get("phone_code_hash"),
                    resp.get("session_string") or session_string,
                ),
            )
            conn.commit()
        return {"ok": True, "status": resp.get("status", "pending")}

    @app.post("/tg/auth/confirm")
    def telegram_auth_confirm(payload: TelegramAuthConfirmIn, user=Depends(require_role("admin", "owner"))):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT phone, phone_code_hash, session_string FROM tg.shared_session WHERE id=1")
            if not row:
                raise HTTPException(400, "Auth start is required")
            phone, phone_code_hash, session_string = row
            resp = telegram_api_request(
                "POST",
                "/auth/confirm",
                {
                    "phone": phone,
                    "code": payload.code,
                    "phone_code_hash": phone_code_hash,
                    "session_string": session_string,
                },
            )
            status = resp.get("status") or "ready"
            exec1(
                conn,
                """
                UPDATE tg.shared_session
                SET status=%s,
                    session_string=COALESCE(%s, session_string),
                    updated_at=now(),
                    last_used_at=CASE WHEN %s='ready' THEN now() ELSE last_used_at END
                WHERE id=1
                """,
                (status, resp.get("session_string"), status),
            )
            conn.commit()
        return {"ok": True, "status": status}

    @app.post("/tg/auth/password")
    def telegram_auth_password(payload: TelegramAuthPasswordIn, user=Depends(require_role("admin", "owner"))):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT session_string FROM tg.shared_session WHERE id=1")
            if not row or not row[0]:
                raise HTTPException(400, "Auth start is required")
            session_string = row[0]
            resp = telegram_api_request(
                "POST",
                "/auth/password",
                {"password": payload.password, "session_string": session_string},
            )
            status = resp.get("status") or "ready"
            exec1(
                conn,
                """
                UPDATE tg.shared_session
                SET status=%s,
                    session_string=COALESCE(%s, session_string),
                    updated_at=now(),
                    last_used_at=CASE WHEN %s='ready' THEN now() ELSE last_used_at END
                WHERE id=1
                """,
                (status, resp.get("session_string"), status),
            )
            conn.commit()
        return {"ok": True, "status": status}

    @app.post("/tg/auth/disconnect")
    def telegram_auth_disconnect(user=Depends(require_role("admin", "owner"))):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT session_string FROM tg.shared_session WHERE id=1")
            if row and row[0]:
                try:
                    telegram_api_request("POST", "/auth/disconnect", {"session_string": row[0]})
                except Exception:
                    pass
            exec1(
                conn,
                """
                INSERT INTO tg.shared_session(id, status, phone, phone_code_hash, session_string, updated_at, last_used_at)
                VALUES (1, 'not_connected', '', NULL, NULL, now(), NULL)
                ON CONFLICT (id)
                DO UPDATE SET status='not_connected',
                              phone='',
                              phone_code_hash=NULL,
                              session_string=NULL,
                              updated_at=now(),
                              last_used_at=NULL
                """,
            )
            conn.commit()
        return {"ok": True}

    @app.get("/tg/dialogs", response_model=TelegramDialogsOut)
    def telegram_dialogs(status: Optional[str] = None, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT session_string, status FROM tg.shared_session WHERE id=1")
            if not row or row[1] != "ready":
                raise HTTPException(400, "Telegram is not connected")
            session_string = row[0]
            user_id = get_user_id(conn, user.username)

            rows = qall(
                conn,
                """
                SELECT
                  s.chat_id,
                  s.title,
                  s.unread_count,
                  s.is_group,
                  s.is_channel,
                  COALESCE(ds.status, 'new') AS status
                FROM tg.dialog_snapshot s
                LEFT JOIN tg.dialog_states ds ON ds.chat_id = s.chat_id
                ORDER BY s.updated_at DESC, s.chat_id DESC
                """,
            )
            items = [
                {
                    "id": int(r[0]),
                    "title": str(r[1] or ""),
                    "unread_count": int(r[2] or 0),
                    "is_group": bool(r[3]),
                    "is_channel": bool(r[4]),
                    "status": str(r[5] or "new"),
                }
                for r in rows
            ]
            last_sync_row = q1(conn, "SELECT MAX(updated_at) FROM tg.dialog_snapshot")
            last_sync_at = last_sync_row[0] if last_sync_row else None

            if not items:
                resp = telegram_api_request(
                    "POST",
                    "/dialogs",
                    {"session_string": session_string, "limit": 50, "only_private": True},
                    timeout_sec=30,
                )
                bootstrap_items = resp.get("items", []) or []
                if bootstrap_items:
                    upsert_telegram_dialog_snapshot(conn, user_id, bootstrap_items)
                    exec1(conn, "UPDATE tg.shared_session SET last_used_at=now() WHERE id=1")
                    conn.commit()
                    rows = qall(
                        conn,
                        """
                        SELECT
                          s.chat_id,
                          s.title,
                          s.unread_count,
                          s.is_group,
                          s.is_channel,
                          COALESCE(ds.status, 'new') AS status
                        FROM tg.dialog_snapshot s
                        LEFT JOIN tg.dialog_states ds ON ds.chat_id = s.chat_id
                        ORDER BY s.updated_at DESC, s.chat_id DESC
                        """,
                    )
                    items = [
                        {
                            "id": int(r[0]),
                            "title": str(r[1] or ""),
                            "unread_count": int(r[2] or 0),
                            "is_group": bool(r[3]),
                            "is_channel": bool(r[4]),
                            "status": str(r[5] or "new"),
                        }
                        for r in rows
                    ]
                    last_sync_row = q1(conn, "SELECT MAX(updated_at) FROM tg.dialog_snapshot")
                    last_sync_at = last_sync_row[0] if last_sync_row else None

            trigger_telegram_dialogs_sync(session_string, user_id)
            sync_running, sync_loaded, sync_batches = get_sync_stats()

        counts = {"new": 0, "accepted": 0, "archived": 0, "all": len(items)}
        for item in items:
            key = str(item.get("status") or "new")
            unread = int(item.get("unread_count") or 0)
            if key in ("new", "accepted", "archived"):
                counts[key] += unread
        if status in ("new", "accepted", "archived"):
            items = [i for i in items if str(i.get("status") or "new") == status]
        return {
            "items": items,
            "counts": counts,
            "sync_running": sync_running,
            "last_sync_at": last_sync_at,
            "sync_loaded": sync_loaded,
            "sync_batches": sync_batches,
        }

    @app.put("/tg/dialogs/{chat_id}/status")
    def telegram_dialog_status_set(chat_id: int, payload: TelegramDialogStatusIn, user=Depends(get_current_user)):
        status = (payload.status or "").strip().lower()
        if status not in ("new", "accepted", "archived"):
            raise HTTPException(400, "Invalid status")
        with psycopg.connect(DB_DSN) as conn:
            user_id = get_user_id(conn, user.username)
            exec1(
                conn,
                """
                INSERT INTO tg.dialog_states(chat_id, status, updated_at, updated_by_user_id)
                VALUES (%s, %s, now(), %s)
                ON CONFLICT (chat_id)
                DO UPDATE SET status=excluded.status, updated_at=now(), updated_by_user_id=excluded.updated_by_user_id
                """,
                (chat_id, status, user_id),
            )
            conn.commit()
        return {"ok": True, "chat_id": chat_id, "status": status}

    @app.get("/tg/contact")
    def telegram_contact(sender_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                "SELECT title, info FROM tg.contact_notes_shared WHERE sender_id=%s",
                (sender_id,),
            )
        if not row:
            return {"title": "", "info": ""}
        return {"title": row[0], "info": row[1]}

    @app.put("/tg/contact")
    def telegram_contact_upsert(payload: TelegramContactIn, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            user_id = get_user_id(conn, user.username)
            exec1(
                conn,
                """
                INSERT INTO tg.contact_notes_shared(sender_id, title, info, updated_at, updated_by_user_id)
                VALUES (%s, %s, %s, now(), %s)
                ON CONFLICT (sender_id)
                DO UPDATE SET title=excluded.title,
                              info=excluded.info,
                              updated_at=now(),
                              updated_by_user_id=excluded.updated_by_user_id
                """,
                (payload.sender_id, payload.title or "", payload.info or "", user_id),
            )
            conn.commit()
        return {"ok": True}

    @app.get("/tg/messages", response_model=TelegramMessagesOut)
    def telegram_messages(
        chat_id: int,
        min_id: Optional[int] = None,
        max_id: Optional[int] = None,
        limit: int = 100,
        user=Depends(get_current_user),
    ):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT session_string, status FROM tg.shared_session WHERE id=1")
            if not row or row[1] != "ready":
                raise HTTPException(400, "Telegram is not connected")
            session_string = row[0]
            try:
                payload = {
                    "session_string": session_string,
                    "chat_id": chat_id,
                    "limit": max(1, min(int(limit or 100), 200)),
                }
                if min_id:
                    payload["min_id"] = int(min_id)
                if max_id:
                    payload["max_id"] = int(max_id)
                resp = telegram_api_request("POST", "/messages", payload)
            except HTTPException as exc:
                if exc.status_code == 404:
                    delete_dead_dialog(conn, chat_id)
                    conn.commit()
                    raise HTTPException(404, "Chat is unavailable and was removed from the list")
                raise
            items = resp.get("items", [])
            message_ids = [int(i["id"]) for i in items if i.get("id")]
            sent_map = {}
            if message_ids:
                rows = qall(
                    conn,
                    """
                    SELECT message_id, sent_by_user_id
                    FROM tg.sent_messages
                    WHERE chat_id=%s AND message_id = ANY(%s)
                    """,
                    (chat_id, message_ids),
                )
                if rows:
                    user_ids = [r[1] for r in rows]
                    user_rows = qall(
                        conn,
                        "SELECT user_id, username FROM app.users WHERE user_id = ANY(%s)",
                        (user_ids,),
                    )
                    user_map = {r[0]: r[1] for r in user_rows}
                    for msg_id, sent_by_user_id in rows:
                        sent_map[int(msg_id)] = user_map.get(sent_by_user_id, "")
            for item in items:
                sent_by = sent_map.get(int(item.get("id", 0)))
                if sent_by:
                    item["sent_by"] = sent_by
            exec1(conn, "UPDATE tg.shared_session SET last_used_at=now() WHERE id=1")
            conn.commit()
        return {"items": items}

    @app.post("/tg/messages")
    def telegram_send_message(payload: TelegramSendMessageIn, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            user_id = get_user_id(conn, user.username)
            row = q1(conn, "SELECT session_string, status FROM tg.shared_session WHERE id=1")
            if not row or row[1] != "ready":
                raise HTTPException(400, "Telegram is not connected")
            session_string = row[0]
            resp = telegram_api_request("POST", "/messages/send", {"session_string": session_string, "chat_id": payload.chat_id, "text": payload.text})
            message_id = resp.get("message_id")
            if message_id:
                exec1(
                    conn,
                    """
                    INSERT INTO tg.sent_messages(message_id, chat_id, sent_by_user_id, sent_at)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (message_id, chat_id) DO NOTHING
                    """,
                    (message_id, payload.chat_id, user_id),
                )
            exec1(
                conn,
                """
                INSERT INTO tg.dialog_states(chat_id, status, updated_at, updated_by_user_id)
                VALUES (%s, 'accepted', now(), %s)
                ON CONFLICT (chat_id)
                DO UPDATE SET status='accepted', updated_at=now(), updated_by_user_id=excluded.updated_by_user_id
                """,
                (payload.chat_id, user_id),
            )
            exec1(conn, "UPDATE tg.shared_session SET last_used_at=now() WHERE id=1")
            conn.commit()
        return {"ok": True}

    @app.get("/tg/media")
    def telegram_media(chat_id: int, message_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT session_string, status FROM tg.shared_session WHERE id=1")
            if not row or row[1] != "ready":
                raise HTTPException(400, "Telegram is not connected")
            session_string = row[0]
            data, content_type = telegram_api_request_raw(
                "POST",
                "/media",
                {"session_string": session_string, "chat_id": chat_id, "message_id": message_id},
            )
            exec1(conn, "UPDATE tg.shared_session SET last_used_at=now() WHERE id=1")
            conn.commit()
        return Response(content=data, media_type=content_type or "application/octet-stream")
