import asyncio
import json
from datetime import datetime, timezone
from typing import Callable, Optional

import jwt
import redis
import redis.asyncio as redis_async
from fastapi import Query, WebSocket, WebSocketDisconnect


DEALS_EVENTS_CHANNEL = "app.deals.events"


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
            parse_ws_user(token)
        except Exception:
            await websocket.close(code=1008, reason="Unauthorized")
            return

        await websocket.accept()
        client = None
        pubsub = None
        disconnect_task = None

        # Поднимает новое подключение к Redis Pub/Sub и подписывается на канал сделок.
        async def open_pubsub():
            local_client = redis_async.Redis.from_url(redis_url, decode_responses=True)
            local_pubsub = local_client.pubsub()
            await local_pubsub.subscribe(DEALS_EVENTS_CHANNEL)
            return local_client, local_pubsub

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
            client, pubsub = await open_pubsub()
            # Отправляем служебное событие, чтобы клиент понимал, что подписка установлена.
            await websocket.send_text(json.dumps({"event": "connected"}, ensure_ascii=True))

            # Отдельно слушаем входящие сообщения, чтобы вовремя поймать disconnect.
            async def watch_disconnect():
                while True:
                    await websocket.receive_text()

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
                    client, pubsub = await open_pubsub()
        except WebSocketDisconnect:
            return
        except RuntimeError:
            # RuntimeError в send/receive обычно значит, что сокет уже закрыт.
            return
        finally:
            if disconnect_task is not None:
                disconnect_task.cancel()
            await close_pubsub(client, pubsub)
