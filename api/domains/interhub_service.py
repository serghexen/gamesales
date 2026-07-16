from dataclasses import dataclass
from typing import Any, Callable
import json
import socket
import ssl
import urllib.error
import urllib.request


@dataclass
class InterHubService:
    get_services: Callable[[], list[dict[str, Any]]]
    get_balance: Callable[[], dict[str, Any]]
    calculate: Callable[[dict[str, Any]], dict[str, Any]]
    check: Callable[[dict[str, Any]], dict[str, Any]]


def build_interhub_service(
    *,
    HTTPException,
    interhub_api_url: str,
    interhub_token: str,
    timeout_sec: int,
    ssl_verify: bool,
    ca_cert_path: str,
    calculate_path: str,
    check_path: str,
    deposit_path: str,
):
    def ensure_configured():
        # Не отправляем запрос провайдеру, пока URL или токен не настроены на сервере.
        if not str(interhub_api_url or "").strip():
            raise HTTPException(500, "InterHub API URL is not configured")
        if not str(interhub_token or "").strip():
            raise HTTPException(500, "InterHub token is not configured")

    def parse_json_bytes(raw: bytes) -> Any:
        # Декодируем JSON-ответ и явно сообщаем о некорректном ответе провайдера.
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:  # pragma: no cover - редкий случай невалидного JSON
            raise HTTPException(502, "InterHub returned invalid JSON") from exc

    def send_request(path: str, payload: dict[str, Any] | None = None) -> Any:
        # Выполняем авторизованный запрос к InterHub, не передавая токен в клиентский UI.
        ensure_configured()
        url = interhub_api_url.rstrip("/") + path
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "token": str(interhub_token).strip(),
        }
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method="GET" if payload is None else "POST")
        context = ssl.create_default_context(cafile=ca_cert_path or None) if ssl_verify else ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(request, timeout=max(5, int(timeout_sec or 20)), context=context) as response:
                return parse_json_bytes(response.read() or b"{}")
        except urllib.error.HTTPError as exc:
            details = (exc.read() or b"").decode("utf-8", errors="ignore")
            suffix = f". {details}" if details else ""
            raise HTTPException(exc.code, f"InterHub {path} failed: {exc.reason}{suffix}") from exc
        except urllib.error.URLError as exc:
            raise HTTPException(502, f"InterHub {path} failed: {exc.reason}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise HTTPException(504, f"InterHub {path} timed out") from exc

    def as_float(value: Any, fallback: float = 0.0) -> float:
        # Приводим лимиты услуги к числу, даже если провайдер прислал строку.
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(fallback)

    def collect_service_objects(payload: Any, bucket: list[dict[str, Any]]):
        # Находим услуги в типовых вложениях ответа, не считая служебные объекты услугами.
        if isinstance(payload, list):
            for item in payload:
                collect_service_objects(item, bucket)
            return
        if not isinstance(payload, dict):
            return
        if (payload.get("id") is not None or payload.get("service_id") is not None) and any(key in payload for key in ("name", "service_name", "type")):
            bucket.append(payload)
        for key in ("data", "items", "services", "result"):
            nested = payload.get(key)
            if isinstance(nested, (list, dict)):
                collect_service_objects(nested, bucket)

    def normalize_fields(raw_fields: Any) -> list[dict[str, Any]]:
        # Оставляем поля сервиса в едином виде для построения динамической формы на следующем этапе.
        if not isinstance(raw_fields, list):
            return []
        fields: list[dict[str, Any]] = []
        for field in raw_fields:
            if not isinstance(field, dict):
                continue
            name = str(field.get("name") or field.get("field") or "").strip()
            if not name:
                continue
            values = field.get("value_list")
            fields.append(
                {
                    "name": name,
                    "type": str(field.get("type") or "TEXT").upper(),
                    "required": bool(field.get("required")),
                    "value_list": values if isinstance(values, list) else [],
                    "raw": field,
                }
            )
        return fields

    def normalize_services(payload: Any) -> list[dict[str, Any]]:
        # Нормализуем каталог InterHub, сохраняя исходные данные для ещё неописанных полей.
        raw_services: list[dict[str, Any]] = []
        collect_service_objects(payload, raw_services)
        items: list[dict[str, Any]] = []
        seen_ids: set[int] = set()
        for service in raw_services:
            try:
                service_id = int(service.get("id") if service.get("id") is not None else service.get("service_id"))
            except (TypeError, ValueError):
                continue
            if service_id <= 0 or service_id in seen_ids:
                continue
            seen_ids.add(service_id)
            items.append(
                {
                    "service_id": service_id,
                    "title": str(service.get("name") or service.get("service_name") or f"Service #{service_id}").strip(),
                    "category": str(service.get("category_name") or service.get("category") or "").strip(),
                    "type": str(service.get("type") or "").upper(),
                    "min_amount": as_float(service.get("min_amount")),
                    "max_amount": as_float(service.get("max_amount")),
                    "fields": normalize_fields(service.get("fields")),
                    "raw": service,
                }
            )
        return items

    def get_services() -> list[dict[str, Any]]:
        # Загружаем каталог услуг из единственного подтверждённого метода InterHub.
        return normalize_services(send_request("/api/agent/service/list"))

    def get_balance() -> dict[str, Any]:
        # Возвращаем баланс и лимит овердрафта в формате, безопасном для виджета UI.
        payload = send_request(deposit_path)
        data = payload if isinstance(payload, dict) else {}
        currency_codes = {"643": "RUB", "949": "TRY", "840": "USD", "978": "EUR"}
        currency = str(data.get("currency") or "").upper()
        return {"balance": as_float(data.get("balance")), "currency": currency_codes.get(currency, currency), "over_balance": as_float(data.get("over_balance")), "over_limit": as_float(data.get("over_limit"))}

    def normalize_payment_response(payload: Any) -> dict[str, Any]:
        # Собираем ключевые поля ответа, но сохраняем raw до уточнения всех форматов InterHub.
        data = payload if isinstance(payload, dict) else {}
        return {
            "success": bool(data.get("success")), "message": str(data.get("message") or ""),
            "status": int(data.get("status") or 0), "account": str(data.get("account") or ""),
            "amount": as_float(data.get("amount")), "transaction_id": str(data.get("transaction_id") or ""),
            "amount_in_currency": as_float(data.get("amount_in_currency")),
            "commission": as_float(data.get("commission", data.get("comission"))),
            "fixed_amount": as_float(data.get("fixed_amount")), "raw": data,
        }

    def calculate(payload: dict[str, Any]) -> dict[str, Any]:
        # Запрашиваем номинал и предварительную проверку без запуска оплаты.
        return normalize_payment_response(send_request(calculate_path, payload))

    def check(payload: dict[str, Any]) -> dict[str, Any]:
        # Проверяем реквизиты и сумму перед отдельным подтверждением будущей оплаты.
        return normalize_payment_response(send_request(check_path, payload))

    return InterHubService(get_services=get_services, get_balance=get_balance, calculate=calculate, check=check)
