from dataclasses import dataclass
from typing import Any, Callable
import json
import socket
import ssl
import urllib.error
import urllib.request
from domains.interhub_ssh_transport import NoTunnelRedirects, TunnelHTTPSHandler


@dataclass
class InterHubService:
    get_services: Callable[[], list[dict[str, Any]]]
    get_balance: Callable[[], dict[str, Any]]
    calculate: Callable[[dict[str, Any]], dict[str, Any]]
    check: Callable[[dict[str, Any]], dict[str, Any]]
    pay: Callable[[dict[str, Any]], dict[str, Any]]
    check_status: Callable[[dict[str, Any]], dict[str, Any]]
    get_service_detail: Callable[[int], Any]
    get_catalog: Callable[[], list[dict[str, Any]]] | None = None


def build_interhub_service(
    *,
    HTTPException,
    interhub_api_url: str,
    interhub_token: str,
    timeout_sec: int,
    ssl_verify: bool,
    ca_cert_path: str,
    proxy_url: str = "",
    ssh_tunnel_port: int | None = None,
    calculate_path: str,
    check_path: str,
    deposit_path: str,
    pay_path: str = "/api/agent/payment/pay",
    check_status_path: str = "/api/agent/payment/check_status",
    offline: bool = False,
):
    proxy_url = str(proxy_url or "").strip()

    def ensure_configured():
        # Не отправляем запрос провайдеру, пока URL или токен не настроены на сервере.
        if not str(interhub_api_url or "").strip():
            raise HTTPException(500, "InterHub API URL is not configured")
        if not str(interhub_token or "").strip():
            raise HTTPException(500, "InterHub token is not configured")
        # SSH-forward работает только с HTTPS и никогда не подменяется прямым HTTP-запросом.
        if ssh_tunnel_port is not None and (
            not str(interhub_api_url).startswith('https://') or not 1 <= ssh_tunnel_port <= 65535
        ):
            raise HTTPException(500, 'Invalid InterHub SSH tunnel configuration')

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
        # На staging разрешены только чтение списка услуг и баланса; detail и платежные методы закрыты.
        if offline and (payload is not None or path not in {'/api/agent/service/list', deposit_path}):
            raise HTTPException(403, 'На staging опросы цен, остатков и покупки отключены')
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
            if ssh_tunnel_port is not None:
                # TCP идёт через SSH с IP сервера; HTTP CONNECT-proxy на сервере не требуется.
                opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({}),
                    TunnelHTTPSHandler(context=context, tunnel_port=ssh_tunnel_port),
                    NoTunnelRedirects(),
                )
                response_context = opener.open(request, timeout=max(5, int(timeout_sec or 20)))
            elif proxy_url:
                # Направляем только InterHub через CONNECT-proxy, не меняя маршруты остальных интеграций.
                proxy_handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
                https_handler = urllib.request.HTTPSHandler(context=context)
                opener = urllib.request.build_opener(proxy_handler, https_handler)
                response_context = opener.open(request, timeout=max(5, int(timeout_sec or 20)))
            else:
                # Выполняем прямой запрос, когда отдельный маршрут к поставщику не требуется.
                response_context = urllib.request.urlopen(request, timeout=max(5, int(timeout_sec or 20)), context=context)
            with response_context as response:
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

    def get_catalog():
        # Для обнаружения исчезнувших ID принимаем только полный, непротиворечивый каталог.
        payload = send_request('/api/agent/service/list')
        raw_services = []
        collect_service_objects(payload, raw_services)
        items = normalize_services(payload)
        def verify_envelope(node):
            # Явная ошибка, пагинация или несовпадающий total запрещают применять исчезновения.
            if isinstance(node, list):
                if any(not isinstance(item, dict) or not (item.get('id') or item.get('service_id')) for item in node):
                    raise ValueError('Некорректная строка каталога поставщика')
                return
            if not isinstance(node, dict):
                return
            if str(node.get('success', True)).lower() in {'false', '0'} or node.get('has_more') or node.get('next') or node.get('next_page') or int(node.get('total_pages') or 1) > 1 or int(node.get('page') or 1) > 1:
                raise ValueError('Неполный ответ каталога поставщика')
            for key in ('total', 'total_count'):
                if key in node and int(node[key]) != len(items):
                    raise ValueError('Количество услуг не совпадает с полным каталогом')
            for key in ('data', 'items', 'services', 'result', 'pagination', 'meta'):
                verify_envelope(node.get(key))
        verify_envelope(payload)
        if not items or len(items) != len(raw_services):
            raise ValueError('Некорректные или повторные услуги поставщика')
        return items

    def get_service_detail(service_id: int) -> Any:
        # Один GET возвращает остатки всех номиналов услуги; сырой ответ нужен для разбора ошибок в кэше.
        if isinstance(service_id, bool) or not isinstance(service_id, int) or service_id <= 0:
            raise HTTPException(422, "InterHub service ID must be a positive integer")
        return send_request(f"/api/agent/service/detail?id={service_id}")

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
            "fixed_amount": as_float(data.get("fixed_amount")),
            "params": data.get("params") if isinstance(data.get("params"), dict) else {},
            "raw": data,
        }

    def calculate(payload: dict[str, Any]) -> dict[str, Any]:
        # Запрашиваем номинал и предварительную проверку без запуска оплаты.
        return normalize_payment_response(send_request(calculate_path, payload))

    def check(payload: dict[str, Any]) -> dict[str, Any]:
        # Проверяем реквизиты и сумму перед отдельным подтверждением будущей оплаты.
        return normalize_payment_response(send_request(check_path, payload))

    def pay(payload: dict[str, Any]) -> dict[str, Any]:
        # Подтверждаем уже проверенную операцию только по её идемпотентному идентификатору.
        return normalize_payment_response(send_request(pay_path, payload))

    def check_status(payload: dict[str, Any]) -> dict[str, Any]:
        # Получаем финальный результат операции, которую провайдер ещё обрабатывает.
        return normalize_payment_response(send_request(check_status_path, payload))

    return InterHubService(get_services=get_services, get_balance=get_balance, calculate=calculate, check=check,
                           pay=pay, check_status=check_status, get_service_detail=get_service_detail, get_catalog=get_catalog)
