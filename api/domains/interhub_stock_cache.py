"""Сопоставление остатков по имени и хранение последней проверки независимо от цены."""

import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


STOCK_STATUS_LABELS = {
    'matched': 'Совпало по имени',
    'normalized': 'Совпало после нормализации',
    'missing': 'Номинал не найден в ответе',
    'ambiguous': 'Неоднозначное имя номинала',
    'invalid_count': 'Некорректный остаток',
    'error': 'Ошибка получения остатков',
}


def normalize_stock_name(value):
    # Убираем разницу регистра и пробелов, сохраняя валюту, тип подписки и бонусы.
    return ' '.join(unicodedata.normalize('NFKC', str(value or '')).casefold().split())


def canonical_stock_name(value):
    # Сравниваем оформление чисел и пробелы вокруг плюса, не угадывая номинал только по цифрам.
    value = normalize_stock_name(value)
    value = re.sub(r'(?<!\d)\d{1,3}(?:[.,]\d{3})+(?!\d)',
                   lambda match: re.sub(r'[.,]', '', match.group()), value)
    value = re.sub(r'(?<=\d)[.,]00\b', '', value)
    return re.sub(r'\s*\+\s*', '+', value)


def parse_stock_count(value):
    # Ноль допустим; дробь, отрицательное число и нечисловой ответ не превращаются в остаток.
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
        if number.is_finite() and 0 <= number <= 9223372036854775807 and number == number.to_integral_value():
            return int(number)
    except (InvalidOperation, ValueError):
        pass
    return None


def detail_items(payload):
    # HTTP 200 с success=false остаётся ошибкой поставщика, а пустой список — корректным ответом.
    if isinstance(payload, dict):
        if payload.get('success') is False or payload.get('error'):
            return None, str(payload.get('message') or payload.get('error') or 'Ошибка поставщика')
        for key in ('data', 'items', 'result'):
            if key in payload:
                return detail_items(payload[key])
    if not isinstance(payload, list) or any(not isinstance(item, dict) or not item.get('name') for item in payload):
        return None, 'Некорректный формат ответа service/detail'
    return payload, ''


def match_stock_targets(targets, payload, *, checked_at=None, error=''):
    # Возвращаем строку для каждого ID номинала: сбой проверки явно заменяет старый остаток на неизвестный.
    checked_at = checked_at or datetime.now(timezone.utc)
    items, message = detail_items(payload) if not error else (None, error)
    local_names = Counter(canonical_stock_name(target['nominal_title']) for target in targets)
    provider_names = Counter(canonical_stock_name(item['name']) for item in items or [])
    rows = []
    for target in targets:
        row = {**target, 'stock_count': None, 'provider_name': '', 'checked_at': checked_at,
               'provider_response': payload, 'match_status': 'error', 'message': message}
        if items is not None:
            key = canonical_stock_name(target['nominal_title'])
            candidates = [item for item in items if canonical_stock_name(item['name']) == key]
            if not candidates:
                row.update(match_status='missing', message=STOCK_STATUS_LABELS['missing'])
            elif local_names[key] != 1 or provider_names[key] != 1:
                row.update(match_status='ambiguous', message=STOCK_STATUS_LABELS['ambiguous'])
            else:
                item = candidates[0]
                count = parse_stock_count(item.get('count'))
                status = ('matched' if normalize_stock_name(item['name']) == normalize_stock_name(target['nominal_title'])
                          else 'normalized') if count is not None else 'invalid_count'
                row.update(stock_count=count, match_status=status, provider_name=str(item['name']),
                           message=STOCK_STATUS_LABELS[status])
        rows.append(row)
    return rows


def fetch_nominal_stock(service_id, nominal_id, *, get_services, get_detail):
    # Для подтверждения читаем живой остаток; сбой не подменяем кэшем и не отменяем успешный check.
    if nominal_id is None or nominal_id == '':
        return None
    response = None
    stock = {'service_id': service_id, 'nominal_id': nominal_id, 'stock_count': None,
             'match_status': 'error', 'message': '', 'provider_response': None}
    try:
        if isinstance(nominal_id, bool) or int(nominal_id) <= 0 or str(int(nominal_id)) != str(nominal_id):
            raise ValueError('Некорректный ID номинала')
        nominal_id = int(nominal_id)
        stock['nominal_id'] = nominal_id
        if get_detail is None:
            raise RuntimeError('Метод получения остатков не настроен')
        response = get_detail(service_id)
        service = next((item for item in get_services() if item.get('service_id') == service_id), None)
        if service is None:
            raise ValueError('Услуга не найдена в актуальном каталоге')
        field = next((item for item in service.get('fields') or [] if item.get('name') == 'nominal'), {})
        targets = {}
        for item in field.get('value_list') or []:
            if not isinstance(item, dict):
                continue
            try:
                item_id = int(item.get('id'))
            except (TypeError, ValueError):
                continue
            if item_id > 0:
                targets[item_id] = {'service_id': service_id, 'service_title': service.get('title', ''),
                                    'nominal_id': item_id, 'nominal_title': str(item.get('title') or '')}
        if nominal_id not in targets or not targets[nominal_id]['nominal_title']:
            raise ValueError('Имя номинала не найдено в актуальном каталоге')
        # Сопоставляем все названия услуги, чтобы дубли не превратились в уверенный остаток.
        rows = match_stock_targets(list(targets.values()), response)
        return next(row for row in rows if row['nominal_id'] == nominal_id)
    except Exception as exc:
        stock.update(message=str(getattr(exc, 'detail', exc)), provider_response=response,
                     checked_at=datetime.now(timezone.utc))
        return stock


def save_stock_rows(psycopg, dsn, rows, batch_id, username):
    # Сохраняем всю услугу одной транзакцией; конфликт обновляет и успех, и последнюю ошибку.
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute('''
                    INSERT INTO app.interhub_stock_cache (
                      service_id, nominal_id, service_title, nominal_title, stock_count, match_status,
                      provider_name, message, provider_response, checked_at, batch_id, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                    ON CONFLICT (service_id, nominal_id) DO UPDATE SET
                      service_title=EXCLUDED.service_title, nominal_title=EXCLUDED.nominal_title,
                      stock_count=EXCLUDED.stock_count, match_status=EXCLUDED.match_status,
                      provider_name=EXCLUDED.provider_name, message=EXCLUDED.message,
                      provider_response=EXCLUDED.provider_response, checked_at=EXCLUDED.checked_at,
                      batch_id=EXCLUDED.batch_id, created_by=EXCLUDED.created_by
                    WHERE app.interhub_stock_cache.checked_at <= EXCLUDED.checked_at
                ''', (row['service_id'], row['nominal_id'], row['service_title'], row['nominal_title'],
                      row['stock_count'], row['match_status'], row['provider_name'], row['message'],
                      json.dumps(row['provider_response'], ensure_ascii=False), row['checked_at'], batch_id, username))
        conn.commit()


def read_stock_rows(psycopg, dsn):
    # UI и Excel читают одинаковый снимок из базы без запросов к поставщику.
    keys = ['service_id', 'nominal_id', 'service_title', 'nominal_title', 'stock_count', 'match_status',
            'provider_name', 'message', 'provider_response', 'checked_at', 'batch_id']
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT service_id, nominal_id, service_title, nominal_title, stock_count, match_status,
                       provider_name, message, provider_response, checked_at, batch_id
                FROM app.interhub_stock_cache ORDER BY service_id, nominal_id
            ''')
            return [dict(zip(keys, row)) for row in cur.fetchall()]
