from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import os
import ssl
import time
import urllib.error
import urllib.request
import zipfile
from typing import Any
from collections.abc import Callable

from fastapi import HTTPException


YANDEX_MARKET_BASE_URL = "https://api.partner.market.yandex.ru"


def _env_bool(name: str, default: bool = True) -> bool:
    # Читаем булевую настройку из env, чтобы локально можно было диагностировать SSL.
    raw = str(os.getenv(name, "") or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int = 0) -> int:
    # Читаем числовую настройку из env и защищаем код от пустых значений.
    raw = str(os.getenv(name, "") or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise HTTPException(500, f"{name} must be integer")


def _required_env(name: str) -> str:
    # Проверяем обязательный секрет до сетевого запроса, чтобы ошибка была понятной.
    value = str(os.getenv(name, "") or "").strip()
    if not value:
        raise HTTPException(500, f"{name} is not configured")
    return value


def _ssl_context() -> ssl.SSLContext:
    # Создаем SSL-контекст с certifi, чтобы локальный Python доверял сертификатам Yandex.
    if not _env_bool("YANDEX_MARKET_SSL_VERIFY", True):
        return ssl._create_unverified_context()

    ca_cert_path = str(os.getenv("YANDEX_MARKET_CA_CERT_PATH", "") or "").strip()
    if ca_cert_path:
        return ssl.create_default_context(cafile=ca_cert_path)

    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _request_json(method: str, url: str, *, token: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    # Выполняем JSON-запрос к Yandex Market API и возвращаем разобранный ответ.
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Api-Key": token,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_text = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(exc.code, f"Yandex Market API error: {error_text[:1000]}")
    except urllib.error.URLError as exc:
        raise HTTPException(502, f"Yandex Market API unavailable: {exc}")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise HTTPException(502, "Yandex Market API returned invalid JSON")


def _download_bytes(url: str, *, timeout: int = 60) -> bytes:
    # Скачиваем готовый ZIP-отчет по временной ссылке из Yandex.
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        error_text = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(exc.code, f"Yandex Market report download error: {error_text[:1000]}")
    except urllib.error.URLError as exc:
        raise HTTPException(502, f"Yandex Market report download unavailable: {exc}")


def _normalize_report_rows(json_files: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    # Достаем строки отчета из разных JSON-оберток, потому что формат отчета может расширяться.
    rows: list[tuple[str, dict[str, Any]]] = []
    for item in json_files:
        source_file = str(item.get("source_file") or "")
        data = item.get("data")
        if isinstance(data, list):
            for row in data:
                if isinstance(row, dict):
                    rows.append((source_file, row))
            continue
        if not isinstance(data, dict):
            continue
        found_list = False
        for key in ("rows", "items", "data", "result", "reports", "orders"):
            value = data.get(key)
            if not isinstance(value, list):
                continue
            found_list = True
            for row in value:
                if isinstance(row, dict):
                    rows.append((source_file, row))
        if not found_list:
            rows.append((source_file, data))
    return rows


def _read_json_zip(zip_content: bytes) -> list[dict[str, Any]]:
    # Читаем JSON-файлы внутри ZIP и сохраняем имя файла для payload_json.
    result: list[dict[str, Any]] = []
    try:
        archive = zipfile.ZipFile(io.BytesIO(zip_content))
    except zipfile.BadZipFile:
        raise HTTPException(502, "Yandex Market report is not a valid ZIP")
    for name in archive.namelist():
        if not name.lower().endswith(".json"):
            continue
        text = archive.read(name).decode("utf-8-sig")
        result.append({"source_file": name, "data": json.loads(text)})
    return result


def _first(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    # Берем первое непустое поле из списка возможных названий.
    for key in keys:
        if key in row and row.get(key) not in (None, ""):
            return row.get(key)
    return None


def _parse_money(value: Any) -> Decimal | None:
    # Приводим сумму из JSON к Decimal, чтобы не терять копейки.
    if value is None or value == "":
        return None
    text = str(value).replace(" ", "").replace(",", ".")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _parse_report_date(value: Any, fallback: date) -> date:
    # Превращаем дату Яндекса в дату учета; при пустом поле используем день отчета.
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return fallback
    for fmt in ("%Y-%m-%d", "%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return fallback


def _row_hash(row: dict[str, Any]) -> str:
    # Формируем короткий стабильный ключ для строк без orderId/shopSku.
    text = json.dumps(row, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _normalize_order_row(source_file: str, row: dict[str, Any], *, fallback_date: date, campaign_id: int) -> dict[str, Any]:
    # Готовим строку экономики заказа к дальнейшему дневному агрегированию.
    amount = _parse_money(_first(row, ("incomeWithoutServices", "income_without_services")))
    order_status = str(_first(row, ("orderStatus", "status")) or "").strip()
    biz_date = _parse_report_date(
        _first(row, ("orderCreationDate", "creationDate", "createdAt", "orderDate", "deliveryDate", "orderDeliveryDate")),
        fallback_date,
    )
    order_id = _first(row, ("orderId", "order_id", "id"))
    shop_sku = _first(row, ("shopSku", "shop_sku", "offerId", "offer_id"))
    key_tail = f"{order_id or 'no-order'}:{shop_sku or _row_hash(row)}:{biz_date.isoformat()}"
    return {
        "biz_date": biz_date,
        "amount": amount,
        "order_id": str(order_id or ""),
        "shop_sku": str(shop_sku or ""),
        "offer_name": str(_first(row, ("offerName", "offerOrServiceName", "name")) or ""),
        "order_status": order_status,
        "external_key": f"yandex-market:united-orders:{campaign_id}:{key_tail}",
        "payload_json": {
            "provider": "yandex_market",
            "report_type": "united_orders",
            "source_file": source_file,
            "campaign_id": campaign_id,
            "order_id": order_id,
            "shop_sku": shop_sku,
            "raw": row,
        },
    }


def fetch_yandex_market_order_economics(
    date_from: date,
    date_to: date,
    progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    # Загружает отчет "Экономика заказов" и возвращает строки с incomeWithoutServices.
    token = _required_env("YANDEX_MARKET_TOKEN")
    business_id = _env_int("YANDEX_MARKET_BUSINESS_ID")
    campaign_id = _env_int("YANDEX_MARKET_CAMPAIGN_ID")
    if not business_id or not campaign_id:
        raise HTTPException(500, "YANDEX_MARKET_BUSINESS_ID and YANDEX_MARKET_CAMPAIGN_ID are required")

    base_url = str(os.getenv("YANDEX_MARKET_BASE_URL", YANDEX_MARKET_BASE_URL) or YANDEX_MARKET_BASE_URL).rstrip("/")
    timeout = max(5, _env_int("YANDEX_MARKET_TIMEOUT_SEC", 30))
    attempts = max(1, _env_int("YANDEX_MARKET_REPORT_ATTEMPTS", 30))
    sleep_seconds = max(1, _env_int("YANDEX_MARKET_REPORT_SLEEP_SEC", 10))

    payload = {
        "businessId": business_id,
        "campaignIds": [campaign_id],
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat(),
    }
    generate_url = f"{base_url}/v2/reports/united-orders/generate?format=JSON&language=RU"
    if progress:
        progress("Создаем отчет Yandex Market")
    report_data = _request_json("POST", generate_url, token=token, payload=payload, timeout=timeout)
    report_id = (report_data.get("result") or {}).get("reportId")
    if not report_id:
        raise HTTPException(502, "Yandex Market did not return reportId")

    file_url = ""
    for attempt in range(attempts):
        if progress:
            progress(f"Проверяем готовность отчета Yandex Market: {attempt + 1}/{attempts}")
        info = _request_json("GET", f"{base_url}/v2/reports/info/{report_id}", token=token, timeout=timeout)
        result = info.get("result") or {}
        status = str(result.get("status") or "")
        if status == "DONE" and result.get("file"):
            file_url = str(result.get("file"))
            break
        if status in {"FAILED", "ERROR"}:
            raise HTTPException(502, f"Yandex Market report failed: {status}")
        time.sleep(sleep_seconds)
    if not file_url:
        raise HTTPException(504, "Yandex Market report was not ready in time")

    if progress:
        progress("Скачиваем ZIP отчета Yandex Market")
    zip_content = _download_bytes(file_url, timeout=max(timeout, 60))
    if progress:
        progress("Разбираем JSON отчета Yandex Market")
    json_files = _read_json_zip(zip_content)
    rows = _normalize_report_rows(json_files)
    if progress:
        progress(f"Найдено строк отчета Yandex Market: {len(rows)}")
    economics_rows = [
        _normalize_order_row(source_file, row, fallback_date=date_from, campaign_id=campaign_id)
        for source_file, row in rows
        if _parse_money(_first(row, ("incomeWithoutServices", "income_without_services"))) is not None
        and str(_first(row, ("orderStatus", "status")) or "").strip() == "Доставлен"
    ]
    if progress:
        progress(f"Найдено доставленных строк экономики Yandex Market: {len(economics_rows)}")
    return economics_rows
