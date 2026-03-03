from dataclasses import dataclass
from typing import Any, Callable, Optional
import json
import re
import socket
import ssl
import threading
import time
import urllib.error
import urllib.request
import uuid


@dataclass
class NsGiftService:
    get_balance: Callable[[], dict[str, Any]]
    get_categories: Callable[[], list[dict[str, Any]]]
    get_services: Callable[[Optional[int]], list[dict[str, Any]]]
    get_steam_currency_rate: Callable[[], dict[str, Any]]
    get_steam_amount: Callable[[float], dict[str, Any]]
    create_order_and_pay: Callable[[int, float, str, bool], dict[str, Any]]


def build_ns_gift_service(
    *,
    HTTPException,
    ns_gift_api_url: str,
    ns_gift_login: str,
    ns_gift_password: str,
    timeout_sec: int,
    ssl_verify: bool,
    ca_cert_path: str,
    user_agent: str,
) -> NsGiftService:
    token_lock = threading.Lock()
    token_cache: dict[str, Any] = {
        "access_token": "",
        "valid_thru": 0,
    }
    services_lock = threading.Lock()
    services_cache: dict[str, dict[str, Any]] = {}
    services_cache_ttl_sec = 80
    categories_cache: dict[str, Any] = {
        "items": [],
        "cached_at": 0,
        "cooldown_until": 0,
    }
    categories_cache_ttl_sec = 300

    def ensure_configured():
        # Проверяем обязательные env, чтобы не уходить в сетевые вызовы с пустыми кредами.
        if not str(ns_gift_api_url or "").strip():
            raise HTTPException(500, "NS Gift API URL is not configured")
        if not str(ns_gift_login or "").strip() or not str(ns_gift_password or "").strip():
            raise HTTPException(500, "NS Gift credentials are not configured")

    def parse_json_bytes(raw: bytes) -> dict[str, Any] | list[Any]:
        # Безопасно декодируем JSON-ответ внешнего API.
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:  # pragma: no cover - редкий случай невалидного JSON
            raise HTTPException(502, "NS Gift returned invalid JSON") from exc

    def send_request(path: str, payload: Optional[dict[str, Any]], token: Optional[str], allow_retry: bool = True):
        # Выполняем HTTP-запрос к NS Gift и при 401 пробуем один раз обновить токен.
        ensure_configured()
        url = ns_gift_api_url.rstrip("/") + path
        # Для части endpoint'ов NS Gift важно отправлять именно пустое тело, а не "{}".
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": str(user_agent or "Mozilla/5.0 (compatible; GameSalesBot/1.0)").strip(),
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        # Для проблемных сертификатов даем управляемый режим проверки через env.
        if ssl_verify:
            context = ssl.create_default_context(cafile=ca_cert_path or None)
        else:
            context = ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(req, timeout=max(5, int(timeout_sec or 20)), context=context) as resp:
                raw = resp.read() or b"{}"
                return parse_json_bytes(raw)
        except urllib.error.HTTPError as exc:
            details_raw = exc.read() or b""
            details_text = details_raw.decode("utf-8", errors="ignore")
            if exc.code == 401 and token and allow_retry:
                refreshed_token = get_access_token(force_refresh=True)
                return send_request(path, payload, refreshed_token, allow_retry=False)
            message = f"NS Gift {path} failed: {exc.code} {exc.reason}"
            if details_text:
                message = f"{message}. {details_text}"
            raise HTTPException(exc.code, message)
        except urllib.error.URLError as exc:
            raise HTTPException(502, f"NS Gift {path} failed: {exc.reason}")
        except (TimeoutError, socket.timeout):
            raise HTTPException(504, f"NS Gift {path} timed out")

    def extract_retry_after_seconds(error_text: str, default_value: int = 85) -> int:
        # Достаем число секунд из текста ошибки провайдера, чтобы соблюдать его лимиты.
        text = str(error_text or "")
        match = re.search(r"(\d+)\s*сек", text, flags=re.IGNORECASE)
        if not match:
            match = re.search(r"(\d+)", text)
        if not match:
            return int(default_value)
        try:
            seconds = int(match.group(1))
        except Exception:
            return int(default_value)
        return max(1, seconds)

    def get_access_token(force_refresh: bool = False) -> str:
        # Кешируем JWT до valid_thru, чтобы не логиниться на каждом запросе.
        now_ts = int(time.time())
        with token_lock:
            cached_token = str(token_cache.get("access_token") or "")
            cached_valid_thru = int(token_cache.get("valid_thru") or 0)
            if not force_refresh and cached_token and cached_valid_thru > (now_ts + 30):
                return cached_token
            response = send_request(
                "/api/v1/get_token",
                {
                    "email": str(ns_gift_login or "").strip(),
                    "username": str(ns_gift_login or "").strip(),
                    "password": str(ns_gift_password or "").strip(),
                },
                token=None,
                allow_retry=False,
            )
            if not isinstance(response, dict):
                raise HTTPException(502, "NS Gift auth response format is invalid")
            access_token = str(response.get("access_token") or "").strip()
            if not access_token:
                raise HTTPException(502, "NS Gift auth response does not contain access_token")
            valid_thru = int(response.get("valid_thru") or 0)
            if valid_thru <= 0:
                valid_thru = now_ts + 15 * 60
            token_cache["access_token"] = access_token
            token_cache["valid_thru"] = valid_thru
            return access_token

    def read_float(value: Any, fallback: float = 0.0) -> float:
        # Нормализуем числовые поля провайдера в float.
        if isinstance(value, str):
            cleaned = value.replace(",", ".").strip()
            match = re.search(r"[-+]?\d+(?:\.\d+)?", cleaned)
            if match:
                value = match.group(0)
        try:
            parsed = float(value)
            if parsed != parsed:  # NaN
                return float(fallback)
            return parsed
        except Exception:
            return float(fallback)

    def collect_balance_values(payload: Any, bucket: list[float]):
        # Рекурсивно ищем поля с названием balance в любом регистре и формате вложенности.
        if isinstance(payload, dict):
            for key, value in payload.items():
                normalized_key = str(key or "").strip().lower()
                if "balance" in normalized_key:
                    parsed = read_float(value, fallback=float("nan"))
                    if parsed == parsed:
                        bucket.append(parsed)
                collect_balance_values(value, bucket)
            return
        if isinstance(payload, list):
            for item in payload:
                collect_balance_values(item, bucket)
            return

    def extract_balance(payload: Any) -> float:
        # Ищем баланс в нескольких известных полях ответа.
        if isinstance(payload, (int, float, str)):
            direct = read_float(payload, fallback=float("nan"))
            if direct == direct:
                return direct
        if isinstance(payload, dict):
            for key in ("balance", "amount", "user_balance", "wallet_balance", "userBalance", "available_balance"):
                if key in payload:
                    return read_float(payload.get(key), 0.0)
            nested = payload.get("data")
            if nested is not None:
                return extract_balance(nested)
        candidates: list[float] = []
        collect_balance_values(payload, candidates)
        if candidates:
            # Если нашли несколько, берем наибольший неотрицательный как самый вероятный баланс кошелька.
            non_negative = [value for value in candidates if value >= 0]
            if non_negative:
                return max(non_negative)
            return candidates[0]
        return 0.0

    def normalize_services(raw_payload: Any) -> list[dict[str, Any]]:
        # Приводим ответ провайдера к единому формату списка услуг для UI.
        def collect_objects(node: Any, bucket: list[dict[str, Any]]):
            # Рекурсивно собираем все словари, чтобы поймать нестандартные вложенные форматы.
            if isinstance(node, dict):
                bucket.append(node)
                for value in node.values():
                    collect_objects(value, bucket)
                return
            if isinstance(node, list):
                for value in node:
                    collect_objects(value, bucket)

        raw_objects: list[dict[str, Any]] = []
        collect_objects(raw_payload, raw_objects)

        items: list[dict[str, Any]] = []
        seen_ids: set[int] = set()
        for item in raw_objects:
            if not isinstance(item, dict):
                continue
            service_id_raw = (
                item.get("service_id")
                if item.get("service_id") is not None
                else item.get("id")
            )
            if service_id_raw is None:
                service_id_raw = item.get("product_id")
            if service_id_raw is None:
                service_id_raw = item.get("service")
            try:
                service_id = int(service_id_raw)
            except Exception:
                continue
            if service_id <= 0:
                continue
            if service_id in seen_ids:
                continue
            seen_ids.add(service_id)

            title = str(item.get("name") or item.get("title") or item.get("service_name") or f"Service #{service_id}").strip()
            category = str(item.get("category") or item.get("category_name") or item.get("group") or "").strip()
            currency = str(item.get("currency") or item.get("currency_code") or "RUB").strip().upper()
            price = read_float(item.get("price", item.get("amount", item.get("rate", item.get("cost")))), 0.0)
            min_qty = read_float(item.get("min", item.get("min_quantity", 1)), 1.0)
            max_qty = read_float(item.get("max", item.get("max_quantity", 1)), 1.0)
            items.append(
                {
                    "service_id": service_id,
                    "title": title,
                    "category": category,
                    "price": price,
                    "currency": currency,
                    "min_quantity": min_qty if min_qty > 0 else 1.0,
                    "max_quantity": max_qty if max_qty > 0 else 1.0,
                    "raw": item,
                }
            )

        return items

    def normalize_categories(raw_payload: Any) -> list[dict[str, Any]]:
        # Приводим ответ категорий к списку объектов {category_id, name}.
        def collect_dicts(node: Any, bucket: list[dict[str, Any]]):
            # Рекурсивно собираем словари из вложенного ответа провайдера.
            if isinstance(node, dict):
                bucket.append(node)
                for value in node.values():
                    collect_dicts(value, bucket)
                return
            if isinstance(node, list):
                for value in node:
                    collect_dicts(value, bucket)

        raw_dicts: list[dict[str, Any]] = []
        collect_dicts(raw_payload, raw_dicts)

        categories: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw_dicts:
            name = str(item.get("category") or item.get("category_name") or item.get("name") or item.get("title") or "").strip()
            if not name:
                continue
            category_id_raw = item.get("category_id")
            if category_id_raw is None:
                category_id_raw = item.get("id")
            category_id = None
            try:
                if category_id_raw is not None and str(category_id_raw).strip() != "":
                    category_id = int(category_id_raw)
            except Exception:
                category_id = None
            dedupe_key = f"{name.lower()}::{category_id if category_id is not None else ''}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            categories.append({
                "category_id": category_id,
                "name": name,
            })
        return categories

    def get_balance() -> dict[str, Any]:
        # Возвращаем баланс кабинета NS Gift в нормализованном виде.
        token = get_access_token()
        payload = send_request("/api/v1/check_balance", None, token)
        return {
            "balance": extract_balance(payload),
            "currency": "RUB",
            "raw": payload,
        }

    def get_services(category_id: Optional[int] = None) -> list[dict[str, Any]]:
        # Загружаем услуги либо целиком, либо по category_id, и нормализуем список.
        cleaned_category_id = None
        try:
            if category_id is not None:
                parsed = int(category_id)
                if parsed > 0:
                    cleaned_category_id = parsed
        except Exception:
            cleaned_category_id = None
        cache_key = f"category_id:{cleaned_category_id}" if cleaned_category_id is not None else "all"
        now_ts = int(time.time())

        with services_lock:
            cached = services_cache.get(cache_key) or {}
            cached_items = cached.get("items") if isinstance(cached.get("items"), list) else []
            cached_at = int(cached.get("cached_at") or 0)
            cooldown_until = int(cached.get("cooldown_until") or 0)

            # Во время cooldown не дергаем NS Gift повторно и отдаем последний успешный каталог.
            if cached_items and now_ts < cooldown_until:
                return cached_items
            # Если кеш еще свежий, отдаем его без запроса к внешнему API.
            if cached_items and (now_ts - cached_at) < services_cache_ttl_sec:
                return cached_items

        token = get_access_token()
        try:
            if cleaned_category_id is not None:
                payload = send_request("/api/v1/products/get_services", {"category_id": cleaned_category_id}, token)
                items = normalize_services(payload)
            else:
                payload = send_request("/api/v1/products/get_all_services", None, token)
                items = normalize_services(payload)
                if not items:
                    # Если общий endpoint вернул пусто, добираем услуги по категориям.
                    categories_payload = send_request("/api/v1/products/get_categories", None, token)
                    category_values = normalize_categories(categories_payload)
                    merged: list[dict[str, Any]] = []
                    merged_ids: set[int] = set()
                    for cat in category_values:
                        payload_data: dict[str, Any] = {}
                        if cat.get("category_id") is not None:
                            payload_data["category_id"] = int(cat["category_id"])
                        elif str(cat.get("name") or "").strip():
                            payload_data["category"] = str(cat["name"]).strip()
                        else:
                            continue
                        cat_payload = send_request("/api/v1/products/get_services", payload_data, token)
                        cat_items = normalize_services(cat_payload)
                        for cat_item in cat_items:
                            sid = int(cat_item.get("service_id") or 0)
                            if sid <= 0 or sid in merged_ids:
                                continue
                            merged_ids.add(sid)
                            merged.append(cat_item)
                    items = merged
            with services_lock:
                services_cache[cache_key] = {
                    "items": items,
                    "cached_at": now_ts,
                    "cooldown_until": 0,
                }
            return items
        except Exception as exc:
            status_code = int(getattr(exc, "status_code", 0) or 0)
            detail = str(getattr(exc, "detail", "") or str(exc))
            if status_code == 429:
                retry_after = extract_retry_after_seconds(detail, 85)
                with services_lock:
                    current = services_cache.get(cache_key) or {}
                    current_items = current.get("items") if isinstance(current.get("items"), list) else []
                    services_cache[cache_key] = {
                        "items": current_items,
                        "cached_at": int(current.get("cached_at") or 0),
                        "cooldown_until": now_ts + retry_after,
                    }
                    # Если есть последний успешный список, отдаем его вместо ошибки 429.
                    if current_items:
                        return current_items
                raise HTTPException(429, f"NS Gift rate limit: подождите {retry_after} секунд")
            raise

    def get_categories() -> list[dict[str, Any]]:
        # Загружает список категорий NS Gift с кешем и защитой от 429.
        now_ts = int(time.time())
        with services_lock:
            cached_items = categories_cache.get("items") if isinstance(categories_cache.get("items"), list) else []
            cached_at = int(categories_cache.get("cached_at") or 0)
            cooldown_until = int(categories_cache.get("cooldown_until") or 0)
            if cached_items and now_ts < cooldown_until:
                return cached_items
            if cached_items and (now_ts - cached_at) < categories_cache_ttl_sec:
                return cached_items

        token = get_access_token()
        try:
            payload = send_request("/api/v1/products/get_categories", None, token)
            items = normalize_categories(payload)
            with services_lock:
                categories_cache["items"] = items
                categories_cache["cached_at"] = now_ts
                categories_cache["cooldown_until"] = 0
            return items
        except Exception as exc:
            status_code = int(getattr(exc, "status_code", 0) or 0)
            detail = str(getattr(exc, "detail", "") or str(exc))
            if status_code == 429:
                retry_after = extract_retry_after_seconds(detail, 85)
                with services_lock:
                    current_items = categories_cache.get("items") if isinstance(categories_cache.get("items"), list) else []
                    categories_cache["items"] = current_items
                    categories_cache["cooldown_until"] = now_ts + retry_after
                    if current_items:
                        return current_items
                raise HTTPException(429, f"NS Gift rate limit: подождите {retry_after} секунд")
            raise

    def create_order_and_pay(service_id: int, quantity: float, data: str, auto_pay: bool) -> dict[str, Any]:
        # Создаем заказ в NS Gift и при необходимости сразу оплачиваем его.
        token = get_access_token()
        custom_id = str(uuid.uuid4())
        create_payload = {
            "service_id": int(service_id),
            "quantity": read_float(quantity, 1.0),
            "custom_id": custom_id,
            "data": str(data or "").strip(),
        }
        created = send_request("/api/v1/create_order", create_payload, token)
        paid: dict[str, Any] | list[Any] = {}
        if auto_pay:
            paid = send_request("/api/v1/pay_order", {"custom_id": custom_id}, token)
        return {
            "custom_id": custom_id,
            "create_payload": create_payload,
            "created": created,
            "paid": paid,
            "auto_pay": bool(auto_pay),
        }

    def get_steam_currency_rate() -> dict[str, Any]:
        # Возвращаем курсы валют Steam как отдает провайдер.
        token = get_access_token()
        payload = send_request("/api/v1/steam/get_currency_rate", None, token)
        if not isinstance(payload, dict):
            raise HTTPException(502, "NS Gift steam currency rate response format is invalid")
        return payload

    def get_steam_amount(amount: float) -> dict[str, Any]:
        # Возвращаем расчет Steam по введенной сумме amount.
        token = get_access_token()
        normalized_amount = read_float(amount, 0.0)
        payload = send_request("/api/v1/steam/get_amount", {"amount": normalized_amount}, token)
        if not isinstance(payload, dict):
            raise HTTPException(502, "NS Gift steam amount response format is invalid")
        return payload

    return NsGiftService(
        get_balance=get_balance,
        get_categories=get_categories,
        get_services=get_services,
        get_steam_currency_rate=get_steam_currency_rate,
        get_steam_amount=get_steam_amount,
        create_order_and_pay=create_order_and_pay,
    )
