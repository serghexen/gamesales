from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from ipaddress import ip_address, ip_network
import json
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


# Официальные подсети Яндекс Маркета: запросы из других адресов не должны попадать в бизнес-логику.
YANDEX_MARKET_NOTIFICATION_NETWORKS = (
    ip_network("5.45.207.0/25"),
    ip_network("141.8.142.0/25"),
    ip_network("5.255.253.0/25"),
)


def _first_text(*values: Any) -> str:
    # Берем первое непустое значение, потому что поля уведомлений могут отличаться по типу события.
    for value in values:
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return ""


def _optional_int(value: Any) -> int | None:
    # Приводим идентификаторы к числу и не ломаем прием уведомления из-за необязательного поля.
    try:
        return int(value) if value is not None and str(value).strip() else None
    except (TypeError, ValueError):
        return None


def _parse_event_time(value: Any) -> datetime | None:
    # Сохраняем время события в UTC, если Маркет передал корректный ISO-формат.
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def yandex_market_source_ip(request: Request) -> str:
    # Берем первый IP из цепочки прокси: Caddy записывает туда реального отправителя уведомления.
    forwarded_for = str(request.headers.get("x-forwarded-for", "") or "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else ""


def is_yandex_market_source(source_ip: str) -> bool:
    # Проверяем отправителя по опубликованным подсетям Маркета и отсекаем поддельные запросы.
    try:
        parsed_ip = ip_address(source_ip)
    except ValueError:
        return False
    return any(parsed_ip in network for network in YANDEX_MARKET_NOTIFICATION_NETWORKS)


def notification_fingerprint(payload: dict[str, Any]) -> str:
    # Строим стабильный отпечаток для последующего поиска повторно доставленных уведомлений.
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()


def integration_response(event_time: Any = None) -> dict[str, str]:
    # Возвращаем контракт Маркета и всегда указываем время ответа в UTC для отладки PING.
    timestamp = _first_text(event_time) or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "version": str(os.getenv("YANDEX_MARKET_WEBHOOK_INTEGRATION_VERSION", "1.0.0") or "1.0.0").strip(),
        "name": str(os.getenv("YANDEX_MARKET_WEBHOOK_INTEGRATION_NAME", "GameSales") or "GameSales").strip(),
        "time": timestamp,
    }


def mount_yandex_market_webhooks_routes(
    app: FastAPI,
    *,
    DB_DSN: str,
    psycopg,
    exec1,
) -> None:
    # Маркет добавляет /notification к URL, сохранённому в настройке API-уведомления.
    @app.post("/marketplaces/yandex/notifications/notification", include_in_schema=False)
    @app.post("/marketplaces/yandex/notifications", include_in_schema=False)
    async def receive_yandex_market_notification(request: Request):
        # Проверяем адрес до чтения тела, чтобы неизвестные запросы не расходовали ресурсы и не попадали в журнал.
        source_ip = yandex_market_source_ip(request)
        if not is_yandex_market_source(source_ip):
            raise HTTPException(403, "Yandex Market notification source is not allowed")

        try:
            payload = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(400, "Yandex Market notification must be JSON") from exc
        if not isinstance(payload, dict):
            raise HTTPException(400, "Yandex Market notification must be JSON object")

        notification_type = _first_text(payload.get("notificationType"))
        if not notification_type:
            raise HTTPException(400, "Yandex Market notificationType is required")

        event_time_raw = _first_text(payload.get("updatedAt"), payload.get("createdAt"), payload.get("time"))
        # На первом этапе только сохраняем событие: выдача ключей и изменение заказа намеренно не запускаются.
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                INSERT INTO app.marketplace_yandex_market_webhook_events (
                  event_fingerprint, notification_type, campaign_id, order_id,
                  status, substatus, event_time, source_ip, payload_json, processing_state
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, 'received')
                """,
                (
                    notification_fingerprint(payload),
                    notification_type,
                    _optional_int(payload.get("campaignId")),
                    _optional_int(payload.get("orderId")),
                    _first_text(payload.get("status")),
                    _first_text(payload.get("substatus")),
                    _parse_event_time(event_time_raw),
                    source_ip,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

        return JSONResponse(status_code=200, content=integration_response(event_time_raw))
