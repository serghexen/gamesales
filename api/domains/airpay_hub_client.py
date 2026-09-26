"""Единственный маршрут Airpay через Hub, без fallback на прямой pay CRM."""

import json
import re
import urllib.error
import urllib.request
from urllib.parse import quote, urlsplit

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from domains.interhub_ssh_transport import NoTunnelRedirects
from domains.airpay_jobs import hide_codes
from domains.airpay_history import read_history_filters, export_history, XLSX_TYPE
from domains.airpay_repository import AirpayRepository
from domains.airpay_purchase import public_transaction
from domains.airpay_contract import CONTRACT_HEADER, CONTRACT_VERSION


SAFE_POST = re.compile(r'^(diagnostics(?:/[a-fA-F0-9-]{36}/(?:next|cancel))?|jobs/[a-fA-F0-9-]{36}/cancel|prepare|check|batches/[1-9][0-9]*/(?:renew|check)|(?:legacy/)?transactions/[1-9][0-9]*/result|transactions/[1-9][0-9]*/resolve)$')
VALID_PATH = re.compile(r'^(diagnostics(?:/[a-fA-F0-9-]{36}(?:/(?:next|cancel))?)?|contract|cutover|queue|balance|services|service|prepare|check|transactions/export|legacy/transactions/[1-9][0-9]*(?:/(?:result|events))?|transactions(?:/[1-9][0-9]*(?:/(?:pay|reconcile|voucher|result|events|resolve))?)?|batches/[1-9][0-9]*(?:/(?:pay|vouchers|renew|check))?|jobs/[a-fA-F0-9-]{36}(?:/cancel)?)$')
NEW_WORK = re.compile(r'^(jobs/[a-fA-F0-9-]{36}/cancel|prepare|check|transactions/[1-9][0-9]*/pay|batches/[1-9][0-9]*/(?:pay|check|renew))$')
MAX_RESPONSE_BYTES = 4 * 1024 * 1024


def disable_payments(value):
    # Даже удалённый разрешённый Hub не даёт локальному UI включить платёжные кнопки.
    if isinstance(value, dict):
        return {key: False if key == 'payments_enabled' else disable_payments(item) for key, item in value.items()}
    if isinstance(value, list):
        return [disable_payments(item) for item in value]
    return value


def mount_airpay_hub_proxy(app, *, get_current_user, environ, restricted=False, legacy_connect=None, legacy_secret=lambda: ''):
    # Выбор выполняется один раз при запуске; ошибка Hub не переключает операцию на CRM.
    base = environ.get('AIRPAY_HUB_URL', '').rstrip('/')
    client = environ.get('AIRPAY_HUB_CLIENT_ID', '').strip()
    secret = environ.get('AIRPAY_HUB_CLIENT_KEY', '').strip()

    @app.api_route('/integrations/airpay/{path:path}', methods=['GET', 'POST'])
    async def airpay_proxy(path: str, request: Request, user=Depends(get_current_user)):
        # Пользователь и разрешение метода проверяются в CRM до передачи серверных credentials в Hub.
        if not VALID_PATH.fullmatch(path):
            raise HTTPException(404, 'Метод Airpay не найден')
        role = user.get('role') if isinstance(user, dict) else user.role
        owner = user.get('username') if isinstance(user, dict) else user.username
        if not (request.method == 'GET' and path in {'balance', 'services', 'service'}) and role != 'owner':
            raise HTTPException(403, 'Действие Airpay доступно только владельцу')
        if restricted and request.method == 'POST' and not SAFE_POST.fullmatch(path):
            raise HTTPException(403, 'Оплата и получение ваучеров отключены в этом окружении')
        from starlette.concurrency import run_in_threadpool
        if path == 'cutover':
            # Диагностика возвращает только счётчики, не реквизиты и не чужие записи.
            if request.method != 'GET':
                raise HTTPException(405, 'Проверка перехода доступна только для чтения')
            if not legacy_connect:
                raise HTTPException(503, 'Старый журнал CRM не подключён')
            return await run_in_threadpool(AirpayRepository(legacy_connect).cutover_status)
        if path in {'queue', 'transactions/export'} and request.method != 'GET':
            raise HTTPException(405, 'Выгрузка доступна только для чтения')
        filters = read_history_filters(request) if path in {'transactions', 'transactions/export'} else None
        archive = path.startswith('legacy/') or (path in {'transactions', 'transactions/export'} and request.query_params.get('archive') == 'crm')
        if archive:
            # Старый журнал доступен только для чтения; архив никогда не становится вторым исполнителем pay.
            if not legacy_connect:
                raise HTTPException(503, 'Архив CRM не подключён')
            repo = AirpayRepository(legacy_connect, code_secret=legacy_secret)
            if path == 'transactions/export':
                return await run_in_threadpool(export_history, repo, owner, filters)
            if path == 'transactions' and request.method == 'GET':
                try:
                    limit, offset = int(request.query_params.get('limit', '21')), int(request.query_params.get('offset', '0'))
                    if not 1 <= limit <= 100 or offset < 0:
                        raise ValueError
                except ValueError:
                    raise HTTPException(422, 'Некорректная страница архива') from None
                rows = await run_in_threadpool(repo.history, owner, limit, offset, filters)
                return hide_codes({'items': [public_transaction(row, False) for row in rows], 'legacy_available': True})
            if path.startswith('legacy/transactions/'):
                transaction_id = int(path.split('/')[2])
                if request.method == 'POST' and path.endswith('/result'):
                    return await run_in_threadpool(repo.reveal, owner, transaction_id)
                if request.method == 'GET' and path.endswith('/events'):
                    try:
                        before = int(request.query_params['before']) if 'before' in request.query_params else None
                        if before is not None and not 1 <= before <= 9223372036854775807:
                            raise ValueError
                    except ValueError:
                        raise HTTPException(422, 'Некорректная страница событий') from None
                    return await run_in_threadpool(repo.events, owner, transaction_id, before)
                if request.method == 'GET' and not path.endswith('/result'):
                    row = await run_in_threadpool(repo.read, owner, transaction_id)
                    return hide_codes(public_transaction(row, False))
            raise HTTPException(405, 'Архив CRM доступен только для чтения')
        parsed = urlsplit(base)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or not client or not secret:
            raise HTTPException(503, 'Не настроено подключение Airpay к Supplier Hub')
        body = await request.body() if request.method == 'POST' else None
        # Старые оплаченные ваучеры без кода также запрещают новые покупки; чтение и завершение Hub доступны.
        if legacy_connect and request.method == 'POST' and NEW_WORK.fullmatch(path):
            report = await run_in_threadpool(AirpayRepository(legacy_connect).cutover_status)
            if not report['ready']:
                raise HTTPException(409, 'Сначала завершите оплаты, получение кодов и задания Airpay в прежнем режиме CRM')
        url = f'{base}/integrations/airpay/{path}'
        if request.url.query:
            url += '?' + request.url.query
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json',
                   'X-Hub-Client': client, 'X-Hub-Key': secret, 'X-Airpay-Owner': quote(owner, safe=''),
                   CONTRACT_HEADER: CONTRACT_VERSION}
        def request_hub(target, method, data=None):
            # Ограничиваем ответ и проверяем версию; токены CRM не передаются даже при ошибке.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoTunnelRedirects())
            req = urllib.request.Request(target, data=data, headers=headers, method=method)
            try:
                # Диагностический шаг последовательно читает service и check; ему нужен запас сверх одного сетевого таймаута.
                diagnostic_step = path.startswith('diagnostics') and method == 'POST'
                with opener.open(req, timeout=250 if diagnostic_step else 30) as response:
                    if response.headers.get(CONTRACT_HEADER) != CONTRACT_VERSION:
                        raise HTTPException(502, 'Supplier Hub требует обновления контракта Airpay')
                    raw = response.read(MAX_RESPONSE_BYTES + 1)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise HTTPException(502, 'Слишком большой ответ Supplier Hub')
                    if path == 'transactions/export' and method == 'GET':
                        if response.status != 200 or response.headers.get('Content-Type', '').split(';')[0] != XLSX_TYPE or not raw.startswith(b'PK'):
                            raise HTTPException(502, 'Некорректная выгрузка Supplier Hub')
                        return response.status, raw
                    payload = json.loads(raw)
                    if not isinstance(payload, dict):
                        raise HTTPException(502, 'Некорректный ответ Supplier Hub')
                    return response.status, payload
            except urllib.error.HTTPError as exc:
                if exc.code in {400, 404, 409, 410, 422, 429}:
                    try:
                        payload = json.loads(exc.read())
                        return exc.code, {'detail': payload.get('detail', 'Запрос Airpay отклонён')}
                    except (ValueError, AttributeError):
                        pass
                raise HTTPException(502, 'Supplier Hub отклонил запрос Airpay') from None
            except (OSError, ValueError):
                raise HTTPException(503, 'Supplier Hub недоступен. Обновите сохранённый результат; новую покупку не создавайте.') from None
        def send():
            # Сначала безопасный handshake: старый Hub не получит POST, который мог бы выполнить покупку.
            if request.method == 'POST':
                status, contract = request_hub(f'{base}/integrations/airpay/contract', 'GET')
                if status != 200 or contract.get('contract_version') != CONTRACT_VERSION or contract.get('provider_code') != 'airpay' or contract.get('execution_backend') != 'hub':
                    raise HTTPException(502, 'Supplier Hub не подтвердил совместимый контракт Airpay')
            return request_hub(url, request.method, body)
        status, payload = await run_in_threadpool(send)
        if path == 'transactions/export' and status == 200 and isinstance(payload, bytes):
            return Response(payload, media_type=XLSX_TYPE, headers={CONTRACT_HEADER: CONTRACT_VERSION,
                'Content-Disposition': 'attachment; filename="airpay-history.xlsx"', 'Cache-Control': 'no-store'})
        if path == 'transactions' and isinstance(payload, dict) and status == 200:
            payload['legacy_available'] = bool(legacy_connect)
        return JSONResponse(disable_payments(payload) if restricted else payload, status_code=status,
                            headers={CONTRACT_HEADER: CONTRACT_VERSION})
