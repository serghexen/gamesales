"""Единый жизненный цикл резервов аккаунта без DDL и внешних подключений."""

import base64
import hashlib
import re
import uuid

from fastapi import HTTPException


def reserve_key(value):
    # Отсекаем произвольные ключи секретов и оставляем постоянный номер резерва.
    raw = str(value or '').strip().lower()
    if not re.fullmatch(r'reserve\d{1,18}', raw):
        return None
    return f'reserve{int(raw[7:])}'


class AccountReserves:
    def __init__(self, q1, qall, exec1):
        # Используем соединение вызывающей операции, чтобы статус сделки и резерв менялись атомарно.
        self.q1, self.qall, self.exec1 = q1, qall, exec1

    def lock(self, conn, account_id):
        # Одна блокировка аккаунта сериализует редактор, импорт, копирование и назначение.
        if not self.q1(conn, 'SELECT account_id FROM app.accounts WHERE account_id=%s FOR UPDATE', (account_id,)):
            raise HTTPException(404, 'Account not found')

    def rows(self, conn, account_id):
        # Значения скрытых резервов нужны только прежним сделкам; в редактор попадают listed.
        return self.qall(conn, '''
            SELECT c.reserve_id, c.reserve_key, c.value_hash, c.is_listed,
                   c.issued_at, c.consumed_at, s.secret_value
            FROM app.account_reserve_codes c
            LEFT JOIN app.account_secrets s ON s.account_id=c.account_id AND s.secret_key=c.reserve_key
            WHERE c.account_id=%s ORDER BY substring(c.reserve_key from '[0-9]+$')::bigint
        ''', (account_id,))

    def event(self, conn, identity, kind, actor, deal_id=None):
        # В журнал никогда не записываем значение кода.
        self.exec1(conn, '''INSERT INTO app.account_reserve_events(reserve_id, deal_id, event_type, actor)
                           VALUES (%s,%s,%s,%s)''', (identity, deal_id, kind, actor))

    def replace(self, conn, account_id, values, actor, expected=None):
        # Сопоставляем по содержимому, а новый код получает новый номер независимо от позиции.
        self.lock(conn, account_id)
        rows = self.rows(conn, account_id)
        current = {r[1]: r[6] for r in rows if r[3] and r[5] is None and r[6]}
        if expected is not None:
            encoded = {k: base64.b64encode(v.encode()).decode() for k, v in expected.items()}
            if encoded != current:
                raise HTTPException(409, 'Резервы изменились. Откройте аккаунт заново.')
        values = [str(v).strip() for v in values if str(v).strip()]
        if len(values) != len(set(values)):
            raise HTTPException(400, 'Одинаковый резерв нельзя добавить дважды')
        keep = []
        next_number = max([int(r[1][7:]) for r in rows] + [0])
        for value in values:
            encoded = base64.b64encode(value.encode()).decode()
            digest = hashlib.sha256(encoded.encode()).hexdigest()
            matches = [r for r in rows if r[2] == digest]
            if len(matches) > 1:
                raise HTTPException(409, 'В старых резервах есть дубли; требуется проверка аккаунта')
            if matches:
                row = matches[0]
                if row[5] is not None:
                    raise HTTPException(409, 'Этот резерв уже выдан и удалён')
                identity, key = row[:2]
                self.exec1(conn, 'UPDATE app.account_reserve_codes SET is_listed=true WHERE reserve_id=%s', (identity,))
            else:
                next_number += 1
                key = f'reserve{next_number}'
                identity = self.q1(conn, '''INSERT INTO app.account_reserve_codes(account_id,reserve_key,value_hash)
                    VALUES (%s,%s,%s) RETURNING reserve_id''', (account_id, key, digest))[0]
                self.event(conn, identity, 'added', actor)
            self.exec1(conn, '''INSERT INTO app.account_secrets(account_id,secret_key,secret_value)
                VALUES (%s,%s,%s) ON CONFLICT(account_id,secret_key) DO NOTHING''', (account_id, key, encoded))
            keep.append(key)
        self.exec1(conn, '''UPDATE app.account_reserve_codes SET is_listed=false
            WHERE account_id=%s AND NOT (reserve_key=ANY(%s))''', (account_id, keep))
        return keep

    def patch_legacy(self, conn, account_id, upserts, deletes, actor):
        # Старые клиенты тоже не могут перезаписать выданный код: собираем новый список значений.
        self.lock(conn, account_id)
        rows = self.rows(conn, account_id)
        values = {r[1]: base64.b64decode(r[6]).decode() for r in rows if r[3] and r[6] and r[5] is None}
        for key in deletes:
            values.pop(key, None)
        values.update(upserts)
        return self.replace(conn, account_id, list(values.values()), actor)

    def used(self, conn, account_id, exclude_deal_id=None, owner=None):
        # Завершённые/выданные и скрытые коды не возвращаем в свободные после смены сделки.
        rows = self.qall(conn, '''
            SELECT c.reserve_key FROM app.account_reserve_codes c
            WHERE c.account_id=%s AND (
                c.consumed_at IS NOT NULL OR NOT c.is_listed
                OR EXISTS (SELECT 1 FROM app.deal_items i JOIN app.deals d USING(deal_id)
                    WHERE i.account_id=c.account_id AND i.reserve_key=c.reserve_key
                      AND d.deal_type_code='rental' AND d.status_code<>'cancelled'
                      AND (%s::bigint IS NULL OR d.deal_id<>%s))
                OR (c.issued_at IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM app.account_reserve_claims a
                    WHERE a.account_id=c.account_id AND a.reserve_key=c.reserve_key AND a.claimed_by=%s)
                    AND NOT EXISTS (SELECT 1 FROM app.deal_items own
                        WHERE own.deal_id=%s AND own.account_id=c.account_id AND own.reserve_key=c.reserve_key))
                OR EXISTS (SELECT 1 FROM app.account_reserve_codes other
                    WHERE other.account_id=c.account_id AND other.value_hash=c.value_hash AND other.reserve_id<>c.reserve_id)
            )
        ''', (account_id, exclude_deal_id, exclude_deal_id, owner, exclude_deal_id))
        return {reserve_key(r[0]) for r in rows if reserve_key(r[0])}

    def claim(self, conn, account_id, key, actor, deal_id=None):
        # Сначала проверяем настоящую связь сделки; несохранённая форма не получает обход защиты.
        if deal_id:
            self.q1(conn, 'SELECT deal_id FROM app.deals WHERE deal_id=%s FOR UPDATE', (deal_id,))
        self.lock(conn, account_id)
        key = reserve_key(key)
        row = next((r for r in self.rows(conn, account_id) if r[1] == key), None)
        if not row or not row[6] or row[5]:
            raise HTTPException(404, 'Reserve not found')
        linked = self.q1(conn, '''SELECT 1 FROM app.deal_items i JOIN app.deals d USING(deal_id)
            WHERE d.deal_id=%s AND i.account_id=%s AND i.reserve_key=%s
              AND d.deal_type_code='rental' AND d.status_code<>'cancelled' AND d.flow_status_code<>'completed'
        ''', (deal_id, account_id, key)) if deal_id else None
        if linked:
            self.exec1(conn, '''UPDATE app.account_reserve_codes SET issued_at=COALESCE(issued_at,now()),
                issued_by=COALESCE(issued_by,%s) WHERE reserve_id=%s''', (actor, row[0]))
            self.event(conn, row[0], 'copied', actor, deal_id)
            return {'reserve_key': key, 'claim_token': '', 'assigned': True}
        if key in self.used(conn, account_id, owner=actor):
            raise HTTPException(409, 'Reserve already used')
        old = self.q1(conn, '''SELECT claim_token::text, claimed_by FROM app.account_reserve_claims
            WHERE account_id=%s AND reserve_key=%s''', (account_id, key))
        if old:
            if old[1] != actor:
                raise HTTPException(409, 'Reserve already used')
            self.exec1(conn, 'UPDATE app.account_reserve_claims SET reused_at=now() WHERE claim_token=%s', (old[0],))
            return {'reserve_key': key, 'claim_token': old[0], 'assigned': False, 'reused': True}
        token = str(uuid.uuid4())
        self.exec1(conn, '''INSERT INTO app.account_reserve_claims(claim_token,account_id,reserve_key,claimed_by)
            VALUES (%s,%s,%s,%s)''', (token, account_id, key, actor))
        self.exec1(conn, 'UPDATE app.account_reserve_codes SET issued_at=now(),issued_by=%s WHERE reserve_id=%s', (actor, row[0]))
        self.event(conn, row[0], 'claimed', actor)
        return {'reserve_key': key, 'claim_token': token, 'assigned': False, 'reused': False}

    def release(self, conn, account_id, key, token, actor):
        # Откатываем только свежую неудачную выдачу владельца токена, не чужие отметки.
        self.lock(conn, account_id)
        deleted = self.q1(conn, '''DELETE FROM app.account_reserve_claims
            WHERE account_id=%s AND reserve_key=%s AND claim_token=%s AND claimed_by=%s
              AND reused_at IS NULL RETURNING reserve_key
        ''', (account_id, key, token, actor))
        if deleted:
            self.exec1(conn, '''UPDATE app.account_reserve_codes SET issued_at=NULL,issued_by=NULL
                WHERE account_id=%s AND reserve_key=%s AND consumed_at IS NULL''', (account_id, key))
        return bool(deleted)

    def select(self, conn, account_id, key, actor, deal_id=None, token=None, auto=True):
        # Назначаем только реально существующий код; конфликт не подменяет уже показанное значение.
        self.lock(conn, account_id)
        rows = self.rows(conn, account_id)
        raw_key = key
        key = reserve_key(key)
        if raw_key and not key:
            raise HTTPException(400, 'Invalid reserve_key')
        if token and not key:
            raise HTTPException(409, 'Reserve claim does not match reserve_key')
        if token:
            claim = self.q1(conn, '''SELECT 1 FROM app.account_reserve_claims
                WHERE account_id=%s AND reserve_key=%s AND claim_token=%s AND claimed_by=%s''', (account_id, key, token, actor))
            if not claim:
                raise HTTPException(409, 'Reserve claim is invalid or already used')
        if deal_id and key:
            linked = self.q1(conn, '''SELECT 1 FROM app.deal_items i JOIN app.deals d USING(deal_id)
                WHERE i.deal_id=%s AND i.account_id=%s AND i.reserve_key=%s
                  AND d.deal_type_code='rental' AND d.status_code<>'cancelled' ''', (deal_id, account_id, key))
            if linked and any(r[1] == key for r in rows):
                return key
        used = self.used(conn, account_id, exclude_deal_id=deal_id, owner=actor)
        available = [r[1] for r in rows if r[3] and r[6] and r[5] is None and r[1] not in used]
        if key:
            if key not in available:
                raise HTTPException(409, 'Резерв уже занят или удалён. Обновите данные сделки.')
            return key
        return available[0] if auto and available else None

    def assigned(self, conn, account_id, key, actor, deal_id):
        # После сохранения сделки отметка копирования заменяется её постоянной связью.
        if not key:
            return
        row = self.q1(conn, 'SELECT reserve_id FROM app.account_reserve_codes WHERE account_id=%s AND reserve_key=%s', (account_id, key))
        self.exec1(conn, 'DELETE FROM app.account_reserve_claims WHERE account_id=%s AND reserve_key=%s AND claimed_by=%s', (account_id, key, actor))
        self.event(conn, row[0], 'assigned', actor, deal_id)

    def detached(self, conn, account_id, key, actor, deal_id):
        # Сохраняем историю прежней связи и очищаем код только после завершённой выдачи.
        if not account_id or not key:
            return
        self.lock(conn, account_id)
        row = self.q1(conn, 'SELECT reserve_id FROM app.account_reserve_codes WHERE account_id=%s AND reserve_key=%s', (account_id, key))
        if row:
            self.event(conn, row[0], 'detached', actor, deal_id)
        completed = self.q1(conn, '''SELECT 1 FROM app.deal_items i JOIN app.deals d USING(deal_id)
            WHERE i.account_id=%s AND i.reserve_key=%s AND d.deal_type_code='rental'
              AND d.status_code<>'cancelled' AND d.flow_status_code='completed' LIMIT 1''', (account_id, key))
        if completed:
            self.finish(conn, account_id, key, actor, deal_id)

    def finish(self, conn, account_id, key, actor, deal_id):
        # Удаляем только конкретный код и только когда он не нужен другой незавершённой сделке.
        if not account_id or not key:
            return
        self.lock(conn, account_id)
        other = self.q1(conn, '''SELECT 1 FROM app.deal_items i JOIN app.deals d USING(deal_id)
            WHERE i.account_id=%s AND i.reserve_key=%s AND d.deal_type_code='rental'
              AND d.status_code<>'cancelled' AND d.flow_status_code<>'completed' LIMIT 1''', (account_id, key))
        if other:
            return
        row = self.q1(conn, '''UPDATE app.account_reserve_codes SET consumed_at=now(), is_listed=false,
            issued_at=COALESCE(issued_at,now()), issued_by=COALESCE(issued_by,%s)
            WHERE account_id=%s AND reserve_key=%s AND consumed_at IS NULL RETURNING reserve_id''', (actor, account_id, key))
        if row:
            self.exec1(conn, 'DELETE FROM app.account_secrets WHERE account_id=%s AND secret_key=%s', (account_id, key))
            self.exec1(conn, 'DELETE FROM app.account_reserve_claims WHERE account_id=%s AND reserve_key=%s', (account_id, key))
            self.event(conn, row[0], 'consumed', actor, deal_id)

    def related(self, conn, deal_id):
        # Учитываем и прежние выдачи сделки, если сотрудник менял выбранный резерв.
        return self.qall(conn, '''
            SELECT account_id, reserve_key FROM app.deal_items
            WHERE deal_id=%s AND account_id IS NOT NULL AND reserve_key IS NOT NULL
            UNION
            SELECT c.account_id,c.reserve_key FROM app.account_reserve_codes c
            JOIN app.account_reserve_events e ON e.reserve_id=c.reserve_id WHERE e.deal_id=%s
            ORDER BY account_id,reserve_key
        ''', (deal_id, deal_id))

    def finish_deal(self, conn, deal_id, actor):
        # Завершение очищает все коды истории этой сделки, сохраняя нужные другим активным сделкам.
        bindings = self.related(conn, deal_id)
        for account_id in sorted({r[0] for r in bindings}):
            self.lock(conn, account_id)
        for account_id, key in bindings:
            self.finish(conn, account_id, key, actor, deal_id)
