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
        client = redis_async.Redis.from_url(redis_url, decode_responses=True)
        pubsub = client.pubsub()
        disconnect_task = None
        try:
            await pubsub.subscribe(DEALS_EVENTS_CHANNEL)
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
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    await websocket.send_text(str(message.get("data") or ""))
        except WebSocketDisconnect:
            return
        except RuntimeError:
            # RuntimeError в send/receive обычно значит, что сокет уже закрыт.
            return
        finally:
            if disconnect_task is not None:
                disconnect_task.cancel()
            try:
                await pubsub.unsubscribe(DEALS_EVENTS_CHANNEL)
                await pubsub.close()
            finally:
                await client.aclose()
