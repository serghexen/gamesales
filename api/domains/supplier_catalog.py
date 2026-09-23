"""Единое текущее состояние поставщика и безопасное обнаружение изменений."""
import json
import time
from datetime import datetime, timezone
from fastapi import HTTPException
from domains.voucher_catalog_service import schedule_slots


def active(value):
    # Поставщик использует как булевы, так и строковые признаки активности.
    return str(value).lower() not in {'false', '0', 'no', 'off'}


def discovery_targets(services):
    # Отбрасываем весь некорректный ответ до записи, чтобы обрыв каталога не выключил связки.
    if not isinstance(services, list) or not services:
        raise ValueError('Поставщик вернул пустой каталог; состояние сохранено')
    targets, seen_services, seen = [], set(), set()
    for service in services:
        if not isinstance(service, dict):
            raise ValueError('Некорректная услуга поставщика')
        sid = int(service['service_id'])
        if sid <= 0 or sid in seen_services:
            raise ValueError('Некорректный или повторный ID услуги')
        seen_services.add(sid)
        if service.get('type') != 'VOUCHER':
            continue
        fields = service.get('fields')
        nominals = [f for f in fields or [] if isinstance(f, dict) and f.get('name') == 'nominal']
        if not nominals or any(not isinstance(f.get('value_list'), list) or
                ('raw' in f and not isinstance(f['raw'].get('value_list'), list)) for f in nominals):
            raise ValueError('Неполный список номиналов; состояние сохранено')
        enabled = active((service.get('raw') or {}).get('active', service.get('active', True)))
        # Интерхаб может вернуть несколько полей nominal, включая пустые: собираем все их значения.
        for entry in (entry for field in nominals for entry in field['value_list']):
            nid = int(entry['id'])
            key = (sid, nid)
            if nid <= 0 or key in seen or not str(entry.get('title') or '').strip():
                raise ValueError('Некорректный или повторный номинал')
            seen.add(key)
            targets.append(dict(service_id=sid, nominal_id=nid, service_title=service['title'],
                nominal_title=entry['title'], category=service.get('category', ''), service_type='VOUCHER',
                enabled=enabled and active(entry.get('active', True))))
    if not targets:
        raise ValueError('В ответе нет ваучеров; состояние сохранено')
    return targets


class SupplierCatalog:
    def __init__(self, db, dsn, provider, *, offline=False):
        # Один экземпляр обслуживает ручной запуск, расписание, каталог и экспорт.
        self.db, self.dsn, self.provider, self.offline = db, dsn, provider, offline

    def rows(self):
        # Чтение не вызывает поставщика и не изменяет признак непросмотренных позиций.
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute('''SELECT c.*, EXISTS(SELECT 1 FROM app.voucher_catalog_offers o
                WHERE o.active AND (o.supplier_code,o.service_id,o.nominal_id)=
                (c.supplier_code,c.service_id,c.nominal_id)) AS linked
                FROM app.supplier_catalog_current c WHERE c.supplier_code='interhub'
                ORDER BY c.service_title, c.nominal_title, c.nominal_id''')
            keys = [column.name for column in cur.description]
            return [dict(zip(keys, row)) for row in cur.fetchall()]

    def overview(self):
        # Состояние последнего обхода показываем отдельно от последней успешной цены.
        rows = self.rows()
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT discovery_at, checked_at, error FROM app.supplier_catalog_sync_state WHERE supplier_code='interhub'")
            state = cur.fetchone()
        return {'items': rows, 'offline': self.offline,
                'sync': dict(zip(['discovery_at', 'checked_at', 'error'], state)) if state else None}

    def review(self, entries):
        # Версия защищает от отметки новых изменений по устаревшему открытому списку.
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            for entry in entries:
                cur.execute('''UPDATE app.supplier_catalog_current SET reviewed_at=now()
                    WHERE supplier_code='interhub' AND service_id=%s AND nominal_id=%s AND review_revision=%s''',
                    (entry['service_id'], entry['nominal_id'], entry['review_revision']))
            conn.commit()

    def services(self):
        # На staging восстанавливаем список из БД, без запроса в Интерхаб.
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT services FROM app.supplier_catalog_sync_state WHERE supplier_code='interhub'")
            row = cur.fetchone()
        if row and row[0]:
            return row[0]
        grouped = {}
        for row in self.rows():
            if row['status'] != 'active':
                continue
            service = grouped.setdefault(row['service_id'], dict(service_id=int(row['service_id']),
                title=row['service_title'], category=row['category'], type=row['service_type'],
                min_amount=0, max_amount=0, fields=[{'name': 'nominal', 'type': 'LIST', 'required': True, 'value_list': []}]))
            service['fields'][0]['value_list'].append({'id': int(row['nominal_id']), 'title': row['nominal_title']})
        return list(grouped.values())

    def options(self):
        # Собственные связки выбирают сохранённые активные ID, не меняя имена наших SKU.
        return [{**row, 'service_id': int(row['service_id']), 'nominal_id': int(row['nominal_id'])}
                for row in self.rows() if row['service_type'] == 'VOUCHER' and row['status'] == 'active']

    def discover(self):
        # Сначала проверяем полный ответ; только после этого одной транзакцией меняем доступность.
        stamp = datetime.now(timezone.utc)
        try:
            services = self.provider.get_services()
            targets = discovery_targets(services)
            with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
                # Исторический импорт не является живым каталогом: порог считаем только по уже увиденным ID.
                cur.execute("SELECT service_id, nominal_id FROM app.supplier_catalog_current WHERE supplier_code='interhub' AND service_type='VOUCHER' AND status='active' AND last_seen_at IS NOT NULL")
                previous = set(cur.fetchall())
                current = {(str(t['service_id']), str(t['nominal_id'])) for t in targets}
                # Резкое сокращение требует разбирательства, даже если JSON синтаксически корректен.
                if len(previous) >= 10 and len(previous - current) > len(previous) * .2:
                    raise ValueError('Каталог сократился более чем на 20%; изменения не применены')
                for target in targets:
                    cur.execute('''INSERT INTO app.supplier_catalog_current AS c
                        (supplier_code,service_id,nominal_id,service_title,nominal_title,category,service_type,status,last_seen_at)
                        VALUES ('interhub',%s,%s,%s,%s,%s,'VOUCHER',%s,%s)
                        ON CONFLICT(supplier_code,service_id,nominal_id) DO UPDATE SET
                        service_title=EXCLUDED.service_title,nominal_title=EXCLUDED.nominal_title,category=EXCLUDED.category,
                        service_type=EXCLUDED.service_type,status=EXCLUDED.status,missing_count=0,last_seen_at=EXCLUDED.last_seen_at,
                        reviewed_at=CASE WHEN (c.service_title,c.nominal_title,c.status) IS DISTINCT FROM
                            (EXCLUDED.service_title,EXCLUDED.nominal_title,EXCLUDED.status) THEN NULL ELSE c.reviewed_at END,
                        review_revision=c.review_revision+CASE WHEN (c.service_title,c.nominal_title,c.status) IS DISTINCT FROM
                            (EXCLUDED.service_title,EXCLUDED.nominal_title,EXCLUDED.status) THEN 1 ELSE 0 END,
                        review_reason=CASE WHEN (c.service_title,c.nominal_title,c.status) IS DISTINCT FROM
                            (EXCLUDED.service_title,EXCLUDED.nominal_title,EXCLUDED.status) THEN 'changed' ELSE c.review_reason END''',
                        (str(target['service_id']),str(target['nominal_id']),target['service_title'],target['nominal_title'],
                         target['category'],'active' if target['enabled'] else 'unavailable',stamp))
                cur.execute('''UPDATE app.supplier_catalog_current SET missing_count=missing_count+1,
                    status=CASE WHEN missing_count>=1 THEN 'unavailable' ELSE 'suspect' END,
                    reviewed_at=CASE WHEN missing_count<2 THEN NULL ELSE reviewed_at END,
                    review_revision=review_revision+CASE WHEN missing_count<2 THEN 1 ELSE 0 END,
                    review_reason='missing'
                    WHERE supplier_code='interhub' AND service_type='VOUCHER' AND last_seen_at IS DISTINCT FROM %s''', (stamp,))
                cur.execute('''INSERT INTO app.supplier_catalog_sync_state(supplier_code,services,discovery_at,checked_at)
                    VALUES ('interhub',%s::jsonb,%s,%s) ON CONFLICT(supplier_code) DO UPDATE SET
                    services=EXCLUDED.services,discovery_at=EXCLUDED.discovery_at,checked_at=EXCLUDED.checked_at,error='' ''',
                    (json.dumps(services),stamp,stamp))
                conn.commit()
            return [t for t in targets if t['enabled']]
        except Exception as exc:
            # Ошибка обхода не превращается в массовое исчезновение и не стирает последнюю успешную загрузку.
            message = str(exc) if isinstance(exc, ValueError) else 'Не удалось получить полный каталог поставщика'
            with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
                cur.execute('''INSERT INTO app.supplier_catalog_sync_state(supplier_code,checked_at,error)
                    VALUES ('interhub',%s,%s) ON CONFLICT(supplier_code) DO UPDATE SET
                    checked_at=EXCLUDED.checked_at,error=EXCLUDED.error''', (stamp,message))
                conn.commit()
            raise ValueError(message) from None

    @staticmethod
    def write_snapshot(cur, target, job, snapshot):
        # Ошибка сохраняет успешное значение; поздний ответ не перезаписывает более новый.
        prefix, field = ('price','price') if job == 'prices' else ('stock','stock_count')
        cur.execute(f'''UPDATE app.supplier_catalog_current SET
            {field}=CASE WHEN %s='' THEN %s ELSE {field} END,
            {prefix}_updated_at=CASE WHEN %s='' THEN %s ELSE {prefix}_updated_at END,
            {prefix}_checked_at=%s,{prefix}_error=%s,
            {prefix}_response=CASE WHEN %s='' THEN %s::jsonb ELSE {prefix}_response END,
            {prefix}_attempt_response=%s::jsonb
            WHERE supplier_code='interhub' AND service_id=%s AND nominal_id=%s
            AND ({prefix}_checked_at IS NULL OR {prefix}_checked_at<=%s)''',
            (snapshot['error'],snapshot['value'],snapshot['error'],snapshot['checked_at'],snapshot['checked_at'],
             snapshot['error'],snapshot['error'],json.dumps(snapshot.get('raw') or {}),
             json.dumps(snapshot.get('raw') or {}),str(target['service_id']),str(target['nominal_id']),snapshot['checked_at']))

    def refresh(self, *, prices=True, stocks=True, progress=None, scheduled=False, now=None):
        # Одна блокировка БД объединяет ручные и фоновые обходы во всех процессах API.
        if self.offline:
            raise HTTPException(403, 'На staging опросы и покупки отключены')
        counts = dict(total=0,processed=0,successes=0,errors=0,stock_total=0,stock_processed=0,stock_successes=0,stock_errors=0)
        with self.db.connect(self.dsn) as lock_conn, lock_conn.cursor() as lock:
            lock.execute('SELECT pg_try_advisory_xact_lock(20260922, 5)')
            if not lock.fetchone()[0]:
                if scheduled:
                    return
                raise HTTPException(409, 'Опрос поставщика уже выполняется')
            slots = schedule_slots(now or datetime.now(timezone.utc))
            if scheduled:
                lock.execute("SELECT checked_at FROM app.supplier_catalog_sync_state WHERE supplier_code='interhub' AND error<>''")
                failed = lock.fetchone()
                if failed and isinstance(failed[0], datetime) and (datetime.now(timezone.utc)-failed[0]).total_seconds() < 600:
                    return
                lock.execute('SELECT job,slot FROM app.voucher_catalog_sync_runs')
                completed = dict(lock.fetchall())
                prices = completed.get('prices', slots['prices']) < slots['prices'] or 'prices' not in completed
                stocks = completed.get('stocks', slots['stocks']) < slots['stocks'] or 'stocks' not in completed
                if not prices and not stocks:
                    return
            targets = self.discover()
            # Неудачная первая попытка новой позиции повторяется на следующем часовом обходе.
            needs_price = {(r['service_id'],r['nominal_id']) for r in self.rows() if r['price_updated_at'] is None}
            price_targets = [t for t in targets if prices or (str(t['service_id']),str(t['nominal_id'])) in needs_price]
            groups = {}
            for target in targets:
                groups.setdefault(target['service_id'], []).append(target)
            counts.update(total=len(price_targets),stock_total=len(groups) if stocks or prices else 0)
            if progress:
                progress(counts.copy())
            if stocks or prices:
                for group in groups.values():
                    snapshots = self.provider.stocks(group)
                    with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
                        for target in group:
                            snapshot = snapshots[str(target['nominal_id'])]
                            self.write_snapshot(cur,target,'stocks',snapshot)
                            counts['stock_errors' if snapshot['error'] else 'stock_successes'] += 1
                        conn.commit()
                    counts['stock_processed'] += 1
                    if progress:
                        progress(counts.copy())
                    time.sleep(self.provider.delay)
            for target in price_targets:
                snapshot = self.provider.price(target)
                with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
                    self.write_snapshot(cur,target,'prices',snapshot)
                    conn.commit()
                counts['processed'] += 1
                counts['errors' if snapshot['error'] else 'successes'] += 1
                if progress:
                    progress(counts.copy())
                time.sleep(self.provider.delay)
            if scheduled:
                for job, done in [('prices', prices),('stocks',stocks or prices)]:
                    if done:
                        lock.execute('''INSERT INTO app.voucher_catalog_sync_runs(job,slot,finished_at,errors)
                            VALUES (%s,%s,now(),%s) ON CONFLICT(job) DO UPDATE SET
                            slot=EXCLUDED.slot,finished_at=EXCLUDED.finished_at,errors=EXCLUDED.errors''',
                            (job,slots[job],counts['errors' if job=='prices' else 'stock_errors']))
            lock_conn.commit()
        return counts

    def legacy(self):
        # Совместимый формат цен оставляет покупку на её прежнем live calculate/check/pay.
        rows = self.rows()
        prices = [{**r,'service_id':int(r['service_id']),'nominal_id':int(r['nominal_id']),
                   'fixed_amount':r['price'],'calculated_at':r['price_updated_at'],'provider_response':r['price_response']} for r in rows]
        stocks = [{**r,'service_id':int(r['service_id']),'nominal_id':int(r['nominal_id']),
                   'checked_at':r['stock_updated_at'],'match_status':'error' if r['stock_error'] or r['status'] != 'active' else 'matched',
                   'message':r['stock_error'] or ('Позиция недоступна или требует проверки' if r['status'] != 'active' else ''),'provider_response':r['stock_response']} for r in rows]
        return prices, stocks
