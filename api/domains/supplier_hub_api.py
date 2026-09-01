from datetime import date, datetime, time, timedelta
from typing import Any, Literal
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
    interhub_get_services,
):
    def catalog_labels() -> tuple[dict[int, str], dict[tuple[int, str], str]]:
        # Собираем видимые названия из каталога, чтобы поиск совпадал с текстом в таблице CRM.
        service_titles: dict[int, str] = {}
        nominal_titles: dict[tuple[int, str], str] = {}
        try:
            services = interhub_get_services()
        except Exception:
            # История остаётся доступной по ID, даже если каталог InterHub временно не загрузился.
            services = []
        for service in services if isinstance(services, list) else []:
            if not isinstance(service, dict):
                continue
            service_id = int(service.get("service_id") or 0)
            if service_id <= 0:
                continue
            service_titles[service_id] = str(service.get("title") or "").strip()
            for field in service.get("fields") or []:
                if not isinstance(field, dict) or str(field.get("name") or "") != "nominal":
                    continue
                for nominal in field.get("value_list") or []:
                    if not isinstance(nominal, dict):
                        continue
                    nominal_id = str(nominal.get("id") or "").strip()
                    if nominal_id:
                        nominal_titles[(service_id, nominal_id)] = str(nominal.get("title") or nominal_id).strip()
        return service_titles, nominal_titles

    def safe_history_item(item: dict[str, Any], service_titles: dict[int, str], nominal_titles: dict[tuple[int, str], str]) -> dict[str, Any]:
        # Отдаём только безопасные поля списка и сразу добавляем подписи, по которым искал пользователь.
        service_id = int(item.get("service_id") or 0)
        nominal_id = str(item.get("nominal_id") or "")
        return {
            "purchase_id": str(item.get("id") or ""),
            "consumer_id": str(item.get("consumer_id") or ""),
            "provider_code": str(item.get("provider_code") or ""),
            "service_id": service_id,
            "service_title": service_titles.get(service_id, ""),
            "nominal": nominal_id,
            "nominal_title": nominal_titles.get((service_id, nominal_id), ""),
            "price": float(item.get("amount") or item.get("max_amount") or 0),
            "state": str(item.get("state") or ""),
            "result_available": bool(item.get("result_available")),
            "provider_message": str(item.get("provider_message") or ""),
            "provider_transaction_id": str(item.get("provider_transaction_id") or ""),
            "created_at": item.get("created_at"),
            "completed_at": item.get("completed_at"),
        }

    def matches_history_search(item: dict[str, Any], search: str) -> bool:
        # Короткий запрос ищет по содержимому строки, а UUID подключаем только для достаточно точного фрагмента.
        needle = " ".join(search.casefold().replace("_", " ").replace("-", " ").split())
        visible_values = [
            item.get("consumer_id"), item.get("provider_code"), item.get("service_id"),
            item.get("service_title"), item.get("nominal"), item.get("nominal_title"),
        ]
        if len(needle) >= 8:
            visible_values.extend([item.get("purchase_id"), item.get("provider_transaction_id")])
        return any(needle in " ".join(str(value or "").casefold().replace("_", " ").replace("-", " ").split()) for value in visible_values)

    def history_sort_key(item: dict[str, Any], sort_by: str) -> Any:
        # Сортируем найденные строки по тем же значениям, которые пользователь видит в колонках.
        if sort_by == "service":
            return (str(item.get("service_title") or "").casefold(), int(item.get("service_id") or 0))
        if sort_by == "nominal":
            return (str(item.get("nominal_title") or item.get("nominal") or "").casefold(), str(item.get("nominal") or ""))
        if sort_by == "price":
            return float(item.get("price") or 0)
        return str(item.get("created_at") or "")

    def load_searchable_history(base_query: dict[str, object]) -> list[dict[str, Any]]:
        # Загружаем безопасную историю пачками только при явном поиске, чтобы фильтр работал по названиям каталога.
        items: list[dict[str, Any]] = []
        offset = 0
        while True:
            payload = supplier_hub_client.list_transactions({**base_query, "limit": 100, "offset": offset})
            batch = payload.get("items") if isinstance(payload.get("items"), list) else []
            items.extend(item for item in batch if isinstance(item, dict))
            offset += len(batch)
            total = max(0, int(payload.get("total") or 0))
            if not batch or offset >= total:
                return items

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
            "state": state.strip().lower(),
        }
        if date_from:
            query["created_from"] = datetime.combine(date_from, time.min, HISTORY_TIMEZONE).isoformat()
        if date_to:
            query["created_to"] = datetime.combine(date_to + timedelta(days=1), time.min, HISTORY_TIMEZONE).isoformat()
        service_titles, nominal_titles = catalog_labels()
        clean_search = search.strip()
        if clean_search:
            raw_items = load_searchable_history(query)
            items = [safe_history_item(item, service_titles, nominal_titles) for item in raw_items]
            items = [item for item in items if matches_history_search(item, clean_search)]
            items.sort(key=lambda item: history_sort_key(item, sort_by), reverse=sort_direction == "desc")
            total = len(items)
            total_amount = sum(float(item.get("price") or 0) for item in items if item.get("state") == "succeeded")
            offset = (page - 1) * page_size
            page_items = items[offset:offset + page_size]
        else:
            payload = supplier_hub_client.list_transactions({
                **query,
                "limit": page_size,
                "offset": (page - 1) * page_size,
                "sort_by": sort_columns[sort_by],
                "sort_direction": sort_direction,
            })
            raw_items = payload.get("items") if isinstance(payload.get("items"), list) else []
            page_items = [safe_history_item(item, service_titles, nominal_titles) for item in raw_items if isinstance(item, dict)]
            total = max(0, int(payload.get("total") or 0))
            total_amount = float(payload.get("total_amount") or 0)
        return {
            "total": total,
            "total_amount": total_amount,
            "page": page,
            "page_size": page_size,
            "items": page_items,
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
