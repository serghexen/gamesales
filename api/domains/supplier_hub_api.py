from datetime import date, datetime, time, timedelta
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Query


HISTORY_TIMEZONE = ZoneInfo("Europe/Moscow")


def mount_supplier_hub_routes(
    app,
    *,
    require_role,
    UserOut,
    supplier_hub_client,
):
    @app.get("/integrations/supplier-hub/transactions")
    def list_supplier_hub_transactions(
        date_from: date | None = Query(default=None),
        date_to: date | None = Query(default=None),
        search: str = Query(default="", max_length=200),
        state: str = Query(default="", max_length=40),
        sort_by: Literal["service", "nominal", "price", "createdAt"] = Query(default="createdAt"),
        sort_direction: Literal["asc", "desc"] = Query(default="desc"),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=25, ge=1, le=100),
        user: UserOut = Depends(require_role("owner")),
    ):
        # Владелец видит общую историю Hub, но секретный результат не входит в список.
        _ = user
        if date_from and date_to and date_from > date_to:
            raise HTTPException(422, "Дата «с» не может быть позже даты «по»")
        sort_columns = {
            "service": "service_id",
            "nominal": "nominal",
            "price": "amount",
            "createdAt": "created_at",
        }
        query: dict[str, object] = {
            "limit": page_size,
            "offset": (page - 1) * page_size,
            "query": search.strip(),
            "state": state.strip().lower(),
            "sort_by": sort_columns[sort_by],
            "sort_direction": sort_direction,
        }
        if date_from:
            query["created_from"] = datetime.combine(date_from, time.min, HISTORY_TIMEZONE).isoformat()
        if date_to:
            query["created_to"] = datetime.combine(date_to + timedelta(days=1), time.min, HISTORY_TIMEZONE).isoformat()
        payload = supplier_hub_client.list_transactions(query)
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        return {
            "total": max(0, int(payload.get("total") or 0)),
            "total_amount": float(payload.get("total_amount") or 0),
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "purchase_id": str(item.get("id") or ""),
                    "consumer_id": str(item.get("consumer_id") or ""),
                    "provider_code": str(item.get("provider_code") or ""),
                    "service_id": int(item.get("service_id") or 0),
                    "nominal": str(item.get("nominal_id") or ""),
                    "price": float(item.get("amount") or item.get("max_amount") or 0),
                    "state": str(item.get("state") or ""),
                    "result_available": bool(item.get("result_available")),
                    "provider_message": str(item.get("provider_message") or ""),
                    "provider_transaction_id": str(item.get("provider_transaction_id") or ""),
                    "created_at": item.get("created_at"),
                    "completed_at": item.get("completed_at"),
                }
                for item in items
                if isinstance(item, dict)
            ],
        }

    @app.post("/integrations/supplier-hub/transactions/{purchase_id}/result")
    def reveal_supplier_hub_result(
        purchase_id: UUID,
        user: UserOut = Depends(require_role("owner")),
    ):
        # Создаём новый correlation id на каждое явное раскрытие и передаём его в аудит Hub.
        username = str(getattr(user, "username", "") or "owner").strip()[:80] or "owner"
        request_id = f"crm:result:{username}:{uuid4().hex}"
        payload = supplier_hub_client.reveal_result(str(purchase_id), request_id)
        return {
            "purchase_id": str(payload.get("purchase_id") or purchase_id),
            "value": str(payload.get("value") or ""),
            "access_created": bool(payload.get("access_created")),
        }
