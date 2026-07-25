import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import redis
from fastapi import Depends


PRESENCE_KEY_PREFIX = "app.presence.user:"
PRESENCE_INDEX_KEY = "app.presence.index"
PRESENCE_META_HASH_KEY = "app.presence.meta"
PRESENCE_TTL_SECONDS = 90
MSK_TZ_NAME = "Europe/Moscow"
WORKLOAD_ROLE_CODES = ("manager", "operator", "admin", "owner")


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
        now_utc = datetime.now(timezone.utc)
        payload = {
            "username": username,
            "role": role,
            "seen_at": now_utc.isoformat(),
        }
        member = username.lower()
        # Если Redis недоступен, не роняем endpoint: presence временно не обновится, но API продолжит работать.
        try:
            # Пишем метаданные в HASH и обновляем индекс пинга в ZSET.
            redis_client.hset(PRESENCE_META_HASH_KEY, member, json.dumps(payload, ensure_ascii=True))
            redis_client.zadd(PRESENCE_INDEX_KEY, {member: now_utc.timestamp()})
        except Exception:
            return

    # Собирает из Redis активных пользователей рабочих ролей и их timestamp последнего пинга.
    def load_online_managers_from_presence():
        online = {}
        now_ts = datetime.now(timezone.utc).timestamp()
        min_alive_ts = now_ts - PRESENCE_TTL_SECONDS
        try:
            # Чистим индекс и hash-метаданные от старых записей, чтобы presence не рос бесконечно.
            stale_members = redis_client.zrangebyscore(PRESENCE_INDEX_KEY, "-inf", min_alive_ts)
            redis_client.zremrangebyscore(PRESENCE_INDEX_KEY, "-inf", min_alive_ts)
            if stale_members:
                redis_client.hdel(PRESENCE_META_HASH_KEY, *stale_members)
            members = redis_client.zrangebyscore(PRESENCE_INDEX_KEY, min_alive_ts, "+inf")
            if not members:
                return online
            payloads = redis_client.hmget(PRESENCE_META_HASH_KEY, members)
        except Exception:
            return online
        for member, raw in zip(members, payloads):
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            username = str(payload.get("username") or "").strip()
            role = str(payload.get("role") or "").strip().lower()
            seen_at = str(payload.get("seen_at") or "").strip()
            if not username or role not in WORKLOAD_ROLE_CODES:
                continue
            online[username.lower()] = {
                "username": username,
                "seen_at": seen_at,
            }
        return online

    # Возвращает сегодняшнюю дату по Москве для информирования в UI.
    def resolve_today_msk_date():
        now_utc = datetime.now(timezone.utc)
        now_msk = now_utc.astimezone(msk_tz)
        return now_msk.date().isoformat()

    @app.post("/presence/heartbeat")
    def presence_heartbeat(user=Depends(get_current_user)):
        touch_presence(user)
        return {"ok": True}

    @app.get("/dashboard/managers-load")
    def dashboard_managers_load(user=Depends(get_current_user)):
        # Перед выдачей обновляем пульс текущего пользователя, чтобы список был актуальным.
        touch_presence(user)
        online_managers = load_online_managers_from_presence()
        today_msk = resolve_today_msk_date()
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
                    lower(match_u.username) AS manager_username,
                    COUNT(DISTINCT d.deal_id)::int AS pending_count
                  FROM app.deals d
                  LEFT JOIN app.deal_items di ON di.deal_id = d.deal_id
                  JOIN app.users match_u
                    ON lower(match_u.role_code) IN ('manager', 'operator', 'admin', 'owner')
                   AND (
                     lower(match_u.username) = lower(COALESCE(d.responsible_username, ''))
                     OR lower(COALESCE(match_u.name, '')) = lower(COALESCE(d.responsible_username, ''))
                   )
                  WHERE d.flow_status_code = 'pending'
                  GROUP BY lower(match_u.username)
                ) work ON work.manager_username = lower(u.username)
                WHERE lower(u.role_code) IN ('manager', 'operator', 'admin', 'owner')
                ORDER BY COALESCE(work.pending_count, 0) DESC, u.username ASC
                """,
                (),
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
                    # Отдаем явный флаг онлайн, чтобы фронт показывал индикатор только активным пользователям.
                    "is_online": bool(presence),
                    "seen_at": presence.get("seen_at") or "",
                }
            )

        return {
            "timezone": MSK_TZ_NAME,
            "date": today_msk,
            "online_count": len(online_managers),
            "items": items,
        }
