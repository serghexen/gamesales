from dataclasses import dataclass
from typing import Any, Callable
import json
import socket
import urllib.error
import urllib.parse
import urllib.request


@dataclass
class SupplierHubOperatorClient:
    list_transactions: Callable[[dict[str, Any]], dict[str, Any]]
    reveal_result: Callable[[str, str], dict[str, Any]]


def build_supplier_hub_operator_client(
    *,
    HTTPException,
    base_url: str,
    operator_id: str,
    operator_key: str,
    timeout_sec: int,
) -> SupplierHubOperatorClient:
    def ensure_configured() -> None:
        # Проверяем backend-only настройки до запроса, не раскрывая ключ в тексте ошибки.
        if not str(base_url or "").strip():
            raise HTTPException(503, "Supplier Hub URL is not configured")
        if not str(operator_id or "").strip() or not str(operator_key or "").strip():
            raise HTTPException(503, "Supplier Hub operator credentials are not configured")

    def parse_json(raw: bytes) -> dict[str, Any]:
        # Принимаем только JSON-объект, потому что CRM ожидает именованный контракт Hub.
        try:
            value = json.loads((raw or b"{}").decode("utf-8"))
        except Exception as exc:
            raise HTTPException(502, "Supplier Hub returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise HTTPException(502, "Supplier Hub returned an unexpected response")
        return value

    def request(method: str, path: str, *, query: dict[str, Any] | None = None, request_id: str = "") -> dict[str, Any]:
        # Вызываем только operator API по внутреннему адресу; методов покупки в клиенте намеренно нет.
        ensure_configured()
        url = str(base_url).rstrip("/") + path
        clean_query = {key: value for key, value in (query or {}).items() if value not in (None, "")}
        if clean_query:
            url += "?" + urllib.parse.urlencode(clean_query)
        headers = {
            "Accept": "application/json",
            "X-Hub-Operator": str(operator_id).strip(),
            "X-Hub-Operator-Key": str(operator_key).strip(),
        }
        body = None
        if method == "POST":
            body = b"{}"
            headers["Content-Type"] = "application/json"
            headers["X-Request-ID"] = request_id
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=max(2, int(timeout_sec or 10))) as response:
                return parse_json(response.read())
        except urllib.error.HTTPError as exc:
            error_payload: dict[str, Any] = {}
            try:
                error_payload = parse_json(exc.read())
            except Exception:
                error_payload = {}
            detail = str(error_payload.get("detail") or "Supplier Hub request failed")
            if exc.code in (404, 409, 422):
                raise HTTPException(exc.code, detail) from exc
            if exc.code in (401, 403):
                raise HTTPException(502, "Supplier Hub operator authorization failed") from exc
            raise HTTPException(502, detail) from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            raise HTTPException(503, "Supplier Hub is temporarily unavailable") from exc

    def list_transactions(query: dict[str, Any]) -> dict[str, Any]:
        # История не раскрывает результат покупки и безопасна для обычной загрузки таблицы.
        return request("GET", "/v1/operator/transactions", query=query)

    return SupplierHubOperatorClient(
        list_transactions=list_transactions,
        reveal_result=lambda purchase_id, request_id: request(
            "POST",
            f"/v1/operator/purchases/{urllib.parse.quote(purchase_id)}/result",
            request_id=request_id,
        ),
    )
