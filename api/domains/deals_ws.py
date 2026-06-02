import asyncio
import json
from datetime import datetime, timezone
from typing import Callable, Optional

import jwt
import redis
import redis.asyncio as redis_async
from fastapi import Query, WebSocket, WebSocketDisconnect


DEALS_EVENTS_CHANNEL = "app.deals.events"
DEALS_EDITING_KEY_PREFIX = "app.deals.editing:"
DEALS_EDITING_TTL_SECONDS = 45


def build_deals_events(
    *,
    redis_url: str,
    jwt_secret: str,
    jwt_alg: str,
    UserOut,
):
    sync_redis = redis.Redis.from_url(redis_url, decode_responses=True)

    # Проверяет токен из query и возвращает пользователя для WS-подключения.
    def parse_ws_user(token: Optional[str]):
        if not token:
            raise ValueError("Missing token")
        payload = jwt.decode(token, jwt_secret, algorithms=[jwt_alg])
        return UserOut(username=payload.get("username"), role=payload.get("role"))

    # Публикует событие изменения сделки в Redis Pub/Sub для всех WS-клиентов.
    def publish_deal_event(event_type: str, deal_id: int, actor: Optional[str] = None):
        data = {
            "event": event_type,
            "deal_id": int(deal_id),
            "actor": actor or "",
            "changed_at": datetime.now(timezone.utc).isoformat(),
        }
        sync_redis.publish(DEALS_EVENTS_CHANNEL, json.dumps(data, ensure_ascii=True))

    return parse_ws_user, publish_deal_event


def mount_deals_ws_routes(
    app,
    *,
    redis_url: str,
    parse_ws_user: Callable[[Optional[str]], object],
):
    @app.websocket("/ws/deals")
    async def deals_ws(websocket: WebSocket, token: Optional[str] = Query(default=None)):
        try:
            user = parse_ws_user(token)
        except Exception:
            await websocket.close(code=1008, reason="Unauthorized")
            return

        await websocket.accept()
        client = None
        pubsub = None
        disconnect_task = None
        active_editing_ids = set()

        # Публикует событие редактирования сделки в общий канал.
        async def publish_edit_event(event_type: str, deal_id: int):
            payload = {
                "event": event_type,
                "deal_id": int(deal_id),
                "actor": getattr(user, "username", "") or "",
                "changed_at": datetime.now(timezone.utc).isoformat(),
            }
            await client.publish(DEALS_EVENTS_CHANNEL, json.dumps(payload, ensure_ascii=True))

        # Возвращает текущее состояние "кто редактирует какую сделку" для инициализации клиента.
        async def load_editing_snapshot():
            items = []
            pattern = f"{DEALS_EDITING_KEY_PREFIX}*"
            async for key in client.scan_iter(match=pattern):
                raw = await client.get(key)
                if not raw:
                    continue
                try:
                    parsed = json.loads(raw)
                except Exception:
                    continue
                deal_id_raw = str(key).replace(DEALS_EDITING_KEY_PREFIX, "", 1)
                try:
                    deal_id = int(deal_id_raw)
                except Exception:
                    continue
                actor = str(parsed.get("actor") or "").strip()
                if not actor:
                    continue
                items.append(
                    {
                        "deal_id": deal_id,
                        "actor": actor,
                        "changed_at": parsed.get("changed_at") or "",
                    }
                )
            return items

        # Поднимает новое подключение к Redis Pub/Sub и подписывается на канал сделок.
        async def open_pubsub():
            local_client = redis_async.Redis.from_url(redis_url, decode_responses=True)
            local_pubsub = local_client.pubsub()
            try:
                await local_pubsub.subscribe(DEALS_EVENTS_CHANNEL)
                return local_client, local_pubsub
            except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
                # Если Redis закрыл соединение на подписке, закрываем ресурсы и отдаем ошибку выше.
                await close_pubsub(local_client, local_pubsub)
                raise

        # Аккуратно закрывает текущие объекты redis даже при ошибках.
        async def close_pubsub(local_client, local_pubsub):
            if local_pubsub is not None:
                try:
                    await local_pubsub.unsubscribe(DEALS_EVENTS_CHANNEL)
                    await local_pubsub.close()
                except Exception:
                    pass
            if local_client is not None:
                try:
                    await local_client.aclose()
                except Exception:
                    pass
        try:
            try:
                client, pubsub = await open_pubsub()
            except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
                # Realtime без Redis не работает; закрываем WS штатно без ASGI traceback.
                await websocket.close(code=1011, reason="Redis unavailable")
                return
            # Отправляем служебное событие, чтобы клиент понимал, что подписка установлена.
            await websocket.send_text(
                json.dumps(
                    {
                        "event": "connected",
                        "editing": await load_editing_snapshot(),
                    },
                    ensure_ascii=True,
                )
            )

            # Отдельно слушаем входящие сообщения от клиента (редактирование/disconnect).
            async def watch_disconnect():
                while True:
                    raw = await websocket.receive_text()
                    try:
                        message = json.loads(str(raw or "{}"))
                    except Exception:
                        continue
                    event_type = str(message.get("event") or "").strip().lower()
                    deal_id_raw = message.get("deal_id")
                    if event_type not in {"deal_edit_started", "deal_edit_stopped", "deal_edit_heartbeat"}:
                        continue
                    try:
                        deal_id = int(deal_id_raw)
                    except Exception:
                        continue
                    if deal_id <= 0:
                        continue
                    if event_type == "deal_edit_started":
                        # Обновляем TTL "мягкого" lock и рассылаем событие всем подписчикам.
                        payload = {
                            "actor": getattr(user, "username", "") or "",
                            "changed_at": datetime.now(timezone.utc).isoformat(),
                        }
                        await client.set(
                            f"{DEALS_EDITING_KEY_PREFIX}{deal_id}",
                            json.dumps(payload, ensure_ascii=True),
                            ex=DEALS_EDITING_TTL_SECONDS,
                        )
                        active_editing_ids.add(deal_id)
                        await publish_edit_event("deal_edit_started", deal_id)
                        continue
                    if event_type == "deal_edit_heartbeat":
                        # Продлеваем TTL мягкого lock, пока пользователь держит форму редактирования открытой.
                        payload = {
                            "actor": getattr(user, "username", "") or "",
                            "changed_at": datetime.now(timezone.utc).isoformat(),
                        }
                        await client.set(
                            f"{DEALS_EDITING_KEY_PREFIX}{deal_id}",
                            json.dumps(payload, ensure_ascii=True),
                            ex=DEALS_EDITING_TTL_SECONDS,
                        )
                        active_editing_ids.add(deal_id)
                        continue
                    await client.delete(f"{DEALS_EDITING_KEY_PREFIX}{deal_id}")
                    if deal_id in active_editing_ids:
                        active_editing_ids.remove(deal_id)
                    await publish_edit_event("deal_edit_stopped", deal_id)

            disconnect_task = asyncio.create_task(watch_disconnect())
            while True:
                if disconnect_task.done():
                    break
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message.get("type") == "message":
                        await websocket.send_text(str(message.get("data") or ""))
                except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
                    # Если связь с Redis оборвалась, переподписываемся и продолжаем WS-сессию.
                    await close_pubsub(client, pubsub)
                    client = None
                    pubsub = None
                    await asyncio.sleep(0.5)
                    try:
                        client, pubsub = await open_pubsub()
                    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
                        # Если переподписка тоже не удалась, завершаем WS без падения приложения.
                        await websocket.close(code=1011, reason="Redis unavailable")
                        return
        except WebSocketDisconnect:
            return
        except RuntimeError:
            # RuntimeError в send/receive обычно значит, что сокет уже закрыт.
            return
        finally:
            if disconnect_task is not None:
                disconnect_task.cancel()
            # При отключении клиента освобождаем все "мягкие" lock, которые он держал.
            if client is not None and active_editing_ids:
                actor = getattr(user, "username", "") or ""
                for deal_id in list(active_editing_ids):
                    try:
                        key = f"{DEALS_EDITING_KEY_PREFIX}{deal_id}"
                        raw = await client.get(key)
                        if raw:
                            parsed = json.loads(raw)
                            owner = str(parsed.get("actor") or "").strip()
                            if owner and owner != actor:
                                continue
                        await client.delete(key)
                        payload = {
                            "event": "deal_edit_stopped",
                            "deal_id": int(deal_id),
                            "actor": actor,
                            "changed_at": datetime.now(timezone.utc).isoformat(),
                        }
                        await client.publish(DEALS_EVENTS_CHANNEL, json.dumps(payload, ensure_ascii=True))
                    except Exception:
                        # Ошибка очистки локов не должна валить закрытие веб-сокета.
                        pass
            await close_pubsub(client, pubsub)
