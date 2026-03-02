import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import redis
from fastapi import Depends


PRESENCE_KEY_PREFIX = "app.presence.user:"
PRESENCE_TTL_SECONDS = 90
MSK_TZ_NAME = "Europe/Moscow"


def mount_dashboard_routes(
    app,
    *,
    DB_DSN,
    psycopg,
    qall,
    get_current_user,
    redis_url,
):
    redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
    msk_tz = ZoneInfo(MSK_TZ_NAME)

    # Сохраняет "пульс" пользователя, чтобы считать его онлайн ограниченное время.
    def touch_presence(user):
        username = str(getattr(user, "username", "") or "").strip()
        role = str(getattr(user, "role", "") or "").strip()
        if not username:
            return
        payload = {
            "username": username,
            "role": role,
            "seen_at": datetime.now(timezone.utc).isoformat(),
        }
        redis_client.set(
            f"{PRESENCE_KEY_PREFIX}{username.lower()}",
            json.dumps(payload, ensure_ascii=True),
            ex=PRESENCE_TTL_SECONDS,
        )

    # Собирает из Redis активных менеджеров и их timestamp последнего пинга.
    def load_online_managers_from_presence():
        online = {}
        pattern = f"{PRESENCE_KEY_PREFIX}*"
        for key in redis_client.scan_iter(match=pattern):
            raw = redis_client.get(key)
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            username = str(payload.get("username") or "").strip()
            role = str(payload.get("role") or "").strip().lower()
            seen_at = str(payload.get("seen_at") or "").strip()
            if not username or role != "manager":
                continue
            online[username.lower()] = {
                "username": username,
                "seen_at": seen_at,
            }
        return online

    # Возвращает UTC-границы текущего дня в часовом поясе Москвы.
    def resolve_today_bounds_utc():
        now_utc = datetime.now(timezone.utc)
        now_msk = now_utc.astimezone(msk_tz)
        day_start_msk = now_msk.replace(hour=0, minute=0, second=0, microsecond=0)
        next_day_start_msk = day_start_msk + timedelta(days=1)
        return (
            day_start_msk.astimezone(timezone.utc),
            next_day_start_msk.astimezone(timezone.utc),
            day_start_msk.date().isoformat(),
        )

    @app.post("/presence/heartbeat")
    def presence_heartbeat(user=Depends(get_current_user)):
        touch_presence(user)
        return {"ok": True}

    @app.get("/dashboard/managers-load")
    def dashboard_managers_load(user=Depends(get_current_user)):
        # Перед выдачей обновляем пульс текущего пользователя, чтобы список был актуальным.
        touch_presence(user)
        online_managers = load_online_managers_from_presence()
        if not online_managers:
            today_start_utc, today_end_utc, today_msk = resolve_today_bounds_utc()
            _ = today_start_utc
            _ = today_end_utc
            return {
                "timezone": MSK_TZ_NAME,
                "date": today_msk,
                "online_count": 0,
                "items": [],
            }

        today_start_utc, today_end_utc, today_msk = resolve_today_bounds_utc()
        manager_usernames = list(online_managers.keys())
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                SELECT
                  u.username,
                  COALESCE(u.name, '') AS name,
                  COALESCE(work.pending_count, 0) AS pending_count
                FROM app.users u
                LEFT JOIN (
                  SELECT
                    lower(d.responsible_username) AS responsible_username,
                    COUNT(*)::int AS pending_count
                  FROM app.deals d
                  WHERE d.flow_status_code = 'pending'
                    AND d.created_at >= %s
                    AND d.created_at < %s
                  GROUP BY lower(d.responsible_username)
                ) work ON work.responsible_username = lower(u.username)
                WHERE lower(u.role_code) = 'manager'
                  AND lower(u.username) = ANY(%s)
                ORDER BY COALESCE(work.pending_count, 0) DESC, u.username ASC
                """,
                (today_start_utc, today_end_utc, manager_usernames),
            )

        items = []
        for username, name, pending_count in rows:
            key = str(username or "").strip().lower()
            presence = online_managers.get(key) or {}
            items.append(
                {
                    "username": username,
                    "name": name or "",
                    "pending_count": int(pending_count or 0),
                    "seen_at": presence.get("seen_at") or "",
                }
            )

        return {
            "timezone": MSK_TZ_NAME,
            "date": today_msk,
            "online_count": len(items),
            "items": items,
        }
