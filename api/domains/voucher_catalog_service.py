"""Каталог ваучеров: предложения поставщиков, сохранённые снимки и расписание."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
import time
import uuid
from types import SimpleNamespace
from psycopg.errors import ForeignKeyViolation, UniqueViolation

from fastapi import HTTPException

from domains.interhub_price_cache import collect_price_targets
from domains.interhub_stock_cache import match_stock_targets


def schedule_slots(now):
    # После простоя выполняем последний пропущенный запуск, не повторяя все прошлые часы.
    local = now.astimezone(ZoneInfo('Europe/Moscow'))
    daily = local.replace(hour=9, minute=0, second=0, microsecond=0)
    if local < daily:
        daily -= timedelta(days=1)
    return {'prices': daily, 'stocks': local.replace(minute=0, second=0, microsecond=0)}


def voucher_targets(services):
    # Для нового каталога доступны только активные ваучеры, без пополнений TOP_UP_FIXED.
    return collect_price_targets([item for item in services if item.get('type', '').upper() == 'VOUCHER'])


def valid_price(result):
    # Отсутствующая или некорректная цена не должна превратиться в бесплатный ваучер.
    raw = result.get('raw')
    value = raw.get('fixed_amount') if isinstance(raw, dict) else result.get('fixed_amount')
    if not result.get('success') or isinstance(value, bool):
        return None
    try:
        price = Decimal(str(value))
        if price.is_finite() and 0 <= price < Decimal('100000000000000'):
            return price
    except (InvalidOperation, ValueError):
        pass
    return None


class InterhubVoucherProvider:
    code = 'interhub'

    def __init__(self, get_services, get_detail, calculate, delay_ms=700):
        # Адаптер отделяет контракт Интерхаба от собственного каталога и будущих поставщиков.
        self.get_services = get_services
        self.get_detail = get_detail
        self.calculate = calculate
        self.delay = max(0, delay_ms) / 1000

    def targets(self):
        # Каждый обход перечитывает номиналы, чтобы не опрашивать удалённые услуги.
        return voucher_targets(self.get_services())

    def price(self, target):
        # Calculate только узнаёт закупочную цену: платёжных вызовов в каталоге нет.
        checked_at = datetime.now(timezone.utc)
        try:
            result = self.calculate({
                'service_id': target['service_id'], 'account': '',
                'agent_transaction_id': f'catalog-{uuid.uuid4().hex}',
                'params': {'nominal': target['nominal_id']},
            })
            price = valid_price(result)
            error = '' if price is not None else str(result.get('message') or 'Поставщик не вернул корректную цену')
        except Exception:
            price, error = None, 'Не удалось получить цену у поставщика'
        return {'value': price, 'checked_at': checked_at, 'error': error}

    def stocks(self, targets):
        # Сравниваем все номиналы услуги, чтобы обнаруживать неоднозначные имена даже вне наших связок.
        checked_at = datetime.now(timezone.utc)
        try:
            payload = self.get_detail(targets[0]['service_id'])
            rows = match_stock_targets(targets, payload, checked_at=checked_at)
        except Exception:
            rows = match_stock_targets(targets, None, checked_at=checked_at,
                                       error='Не удалось получить остатки у поставщика')
        return {str(row['nominal_id']): {
            'value': row['stock_count'], 'checked_at': checked_at,
            'error': '' if row['stock_count'] is not None else row['message'],
        } for row in rows}

    def snapshot(self, target, targets):
        # При создании связки сразу читаем обе величины, независимо от расписания.
        price = self.price(target)
        time.sleep(self.delay)
        stocks = self.stocks([item for item in targets if item['service_id'] == target['service_id']])
        return price, stocks[str(target['nominal_id'])]


class VoucherCatalogService:
    def __init__(self, psycopg, dsn, providers):
        # Новые поставщики подключаются адаптерами, структура предложений остаётся общей.
        self.db, self.dsn, self.providers = psycopg, dsn, providers

    def can_view(self, role):
        # Учитываем сохранённые права раздела и тот же fallback, что используется во фронтенде.
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute('SELECT can_view FROM app.role_ui_sections WHERE role_code=%s AND section_code=%s',
                        (role, 'voucher-catalog'))
            row = cur.fetchone()
        return bool(row[0]) if row else role in {'admin', 'owner'}

    def list_items(self):
        # Открытие страницы читает только БД: поставщик не замедляет таблицу каталога.
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute('SELECT item_id, name FROM app.voucher_catalog_items ORDER BY lower(name), item_id')
            items = {row[0]: {'item_id': row[0], 'name': row[1], 'offers': [], 'nominals': []} for row in cur.fetchall()}
            cur.execute('SELECT catalog_nominal_id, item_id, name, fulfillment_revision FROM app.voucher_catalog_nominals ORDER BY catalog_nominal_id')
            nominals = {}
            for nominal_id, item_id, name, revision in cur.fetchall():
                nominal = {'catalog_nominal_id': nominal_id, 'name': name, 'offers': [], 'fulfillment_revision': revision}
                nominals[nominal_id] = nominal
                if item_id in items:
                    items[item_id]['nominals'].append(nominal)
            cur.execute('''SELECT o.offer_id, o.item_id, o.catalog_nominal_id, o.supplier_code, s.name AS supplier_name,
                o.service_id, o.nominal_id, o.service_title, o.nominal_title, o.price, o.currency,
                o.price_updated_at, o.price_checked_at, o.price_error, o.stock_count,
                o.stock_updated_at, o.stock_checked_at, o.stock_error, o.fulfillment_priority, o.fulfillment_enabled
                FROM app.voucher_catalog_offers o JOIN app.voucher_catalog_suppliers s ON s.code=o.supplier_code
                WHERE o.active ORDER BY o.catalog_nominal_id, o.fulfillment_priority, o.offer_id''')
            keys = [column.name for column in cur.description]
            for row in cur.fetchall():
                offer = dict(zip(keys, row))
                # При параллельном удалении и пересоздании новый номинал попадёт в следующий снимок списка.
                if offer['item_id'] in items and offer['catalog_nominal_id'] in nominals:
                    items[offer['item_id']]['offers'].append(offer)
                    nominals[offer['catalog_nominal_id']]['offers'].append(offer)
            cur.execute('SELECT job, slot, finished_at, errors FROM app.voucher_catalog_sync_runs ORDER BY job')
            runs = [dict(zip(['job', 'slot', 'finished_at', 'errors'], row)) for row in cur.fetchall()]
            cur.execute('SELECT code, name FROM app.voucher_catalog_suppliers ORDER BY name')
            suppliers = [{'code': row[0], 'name': row[1]} for row in cur.fetchall() if row[0] in self.providers]
        return {'items': list(items.values()), 'runs': runs, 'suppliers': suppliers}

    def options(self, supplier_code):
        # Не допускаем произвольный код поставщика из браузера.
        provider = self.providers.get(supplier_code)
        if provider is None:
            raise HTTPException(422, 'Поставщик пока не подключён')
        return provider.targets()

    def prepare_nominals(self, nominals, binding=None):
        # Сначала проверяем весь пакет: ошибочный последний ID не должен сохранить часть выбора.
        requests = list(nominals or [])
        if binding:
            if requests:
                raise HTTPException(422, 'Передайте один способ добавления номиналов')
            requests = [SimpleNamespace(name='', catalog_nominal_id=None, binding=binding)]
        catalogs, prepared, seen_names, seen_bindings, seen_ids = {}, [], set(), set(), set()
        for nominal in requests:
            if nominal.catalog_nominal_id is not None:
                if nominal.catalog_nominal_id in seen_ids:
                    raise HTTPException(422, 'Один собственный номинал передан несколько раз')
                seen_ids.add(nominal.catalog_nominal_id)
            link = nominal.binding
            target = None
            if link:
                if link.supplier_code not in catalogs:
                    catalogs[link.supplier_code] = self.options(link.supplier_code)
                target = next((item for item in catalogs[link.supplier_code]
                               if str(item['service_id']) == link.service_id
                               and str(item['nominal_id']) == link.nominal_id), None)
                if target is None:
                    raise HTTPException(422, 'Выберите активный номинал ваучера из каталога поставщика')
                key = (link.supplier_code, link.service_id, link.nominal_id)
                if key in seen_bindings:
                    raise HTTPException(422, 'Один номинал поставщика выбран несколько раз')
                seen_bindings.add(key)
            name = (nominal.name or (target['nominal_title'] if binding else '')).strip()
            if not name or len(name) > 250:
                raise HTTPException(422, 'Укажите название каждого номинала длиной до 250 символов')
            if name in seen_names:
                raise HTTPException(422, 'Названия номиналов внутри услуги должны различаться')
            seen_names.add(name)
            routing = getattr(nominal, 'routing', None)
            if routing is not None:
                if nominal.catalog_nominal_id is None:
                    raise HTTPException(422, 'Приоритеты доступны после создания собственного номинала')
                ids = [offer.offer_id for offer in routing.offers]
                if len(ids) != len(set(ids)):
                    raise HTTPException(422, 'Связка передана в порядке поставщиков несколько раз')
            prepared.append({'name': name, 'id': nominal.catalog_nominal_id, 'binding': link, 'target': target,
                             'routing': routing})
        # При пакетном добавлении остатки читаем один раз на услугу, а цены — по каждому номиналу.
        stocks = {}
        for row in prepared:
            link, target = row['binding'], row['target']
            if not link:
                continue
            provider = self.providers[link.supplier_code]
            key = (link.supplier_code, link.service_id)
            if key not in stocks:
                targets = [item for item in catalogs[link.supplier_code] if str(item['service_id']) == link.service_id]
                stocks[key] = provider.stocks(targets)
                time.sleep(provider.delay)
            row['stock'] = stocks[key][link.nominal_id]
            row['price'] = provider.price(target)
            time.sleep(provider.delay)
        return prepared

    def save_item(self, name, username, item_id=None, binding=None, nominals=None):
        # Услуга и её номиналы сохраняются одной транзакцией; ошибка не оставляет половину списка.
        if name is not None:
            name = name.strip()
            if not name or len(name) > 250:
                raise HTTPException(422, 'Укажите название услуги длиной до 250 символов')
        elif item_id is None:
            raise HTTPException(422, 'Укажите услугу')
        prepared = self.prepare_nominals(nominals, binding)
        try:
            with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
                if item_id is None:
                    if any(row['id'] for row in prepared):
                        raise HTTPException(422, 'В новой услуге нельзя использовать ID чужих номиналов')
                    cur.execute('INSERT INTO app.voucher_catalog_items(name, created_by) VALUES (%s, %s) RETURNING item_id',
                                (name, username))
                    item_id = cur.fetchone()[0]
                else:
                    # Блокируем родителя, чтобы два редактора не создали дубли номиналов одновременно.
                    cur.execute('SELECT item_id FROM app.voucher_catalog_items WHERE item_id=%s FOR UPDATE', (item_id,))
                    if cur.fetchone() is None:
                        raise HTTPException(404, 'Услуга каталога не найдена')
                    if name is not None:
                        cur.execute('UPDATE app.voucher_catalog_items SET name=%s WHERE item_id=%s', (name, item_id))
                for row in prepared:
                    if row['id'] is None:
                        cur.execute('''INSERT INTO app.voucher_catalog_nominals(item_id, name, created_by)
                            VALUES (%s, %s, %s) RETURNING catalog_nominal_id''', (item_id, row['name'], username))
                    else:
                        cur.execute('''UPDATE app.voucher_catalog_nominals SET name=%s
                            WHERE item_id=%s AND catalog_nominal_id=%s RETURNING catalog_nominal_id''',
                            (row['name'], item_id, row['id']))
                    found = cur.fetchone()
                    if not found:
                        raise HTTPException(404, 'Номинал не найден в этой услуге')
                    catalog_nominal_id = found[0]
                    if row['routing'] is not None:
                        self.save_routing(cur, item_id, catalog_nominal_id, row['routing'])
                    link, target = row['binding'], row['target']
                    if not link:
                        continue
                    cur.execute('''INSERT INTO app.voucher_catalog_offers
                        (item_id, catalog_nominal_id, supplier_code, service_id, nominal_id, service_title, nominal_title, created_by,
                         fulfillment_priority)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                          (SELECT COALESCE(MAX(fulfillment_priority), 0) + 1 FROM app.voucher_catalog_offers
                           WHERE catalog_nominal_id=%s))
                        ON CONFLICT (item_id, supplier_code, service_id, nominal_id) DO UPDATE SET
                          active=true, service_title=EXCLUDED.service_title, nominal_title=EXCLUDED.nominal_title,
                          fulfillment_priority=CASE WHEN app.voucher_catalog_offers.active
                            THEN app.voucher_catalog_offers.fulfillment_priority ELSE EXCLUDED.fulfillment_priority END,
                          fulfillment_enabled=CASE WHEN app.voucher_catalog_offers.active
                            THEN app.voucher_catalog_offers.fulfillment_enabled ELSE true END
                        WHERE app.voucher_catalog_offers.catalog_nominal_id=EXCLUDED.catalog_nominal_id
                        RETURNING offer_id''',
                        (item_id, catalog_nominal_id, link.supplier_code, link.service_id, link.nominal_id,
                         target['service_title'], target['nominal_title'], username, catalog_nominal_id))
                    offer = cur.fetchone()
                    if offer is None:
                        raise HTTPException(409, 'Этот номинал поставщика уже связан с другим номиналом услуги')
                    self.write_snapshot(cur, [offer[0]], 'prices', row['price'])
                    self.write_snapshot(cur, [offer[0]], 'stocks', row['stock'])
                    cur.execute('''UPDATE app.voucher_catalog_nominals
                        SET fulfillment_revision=fulfillment_revision+1 WHERE catalog_nominal_id=%s''', (catalog_nominal_id,))
                conn.commit()
        except UniqueViolation:
            raise HTTPException(409, 'Номинал с таким названием уже есть в услуге. Откройте его карточку для привязки поставщика.') from None
        return {'item_id': item_id}

    @staticmethod
    def save_routing(cur, item_id, catalog_nominal_id, routing):
        # Родитель уже заблокирован save_item; весь порядок проверяем до первой записи.
        cur.execute('''SELECT fulfillment_revision FROM app.voucher_catalog_nominals
            WHERE item_id=%s AND catalog_nominal_id=%s''', (item_id, catalog_nominal_id))
        current = cur.fetchone()
        if current is None:
            raise HTTPException(404, 'Номинал не найден в этой услуге')
        if current[0] != routing.revision:
            raise HTTPException(409, 'Настройки поставщиков изменились. Закройте карточку, обновите список и откройте её снова.')
        cur.execute('''SELECT offer_id FROM app.voucher_catalog_offers
            WHERE item_id=%s AND catalog_nominal_id=%s AND active''', (item_id, catalog_nominal_id))
        actual = {row[0] for row in cur.fetchall()}
        ids = [offer.offer_id for offer in routing.offers]
        if len(ids) != len(set(ids)) or set(ids) != actual:
            raise HTTPException(409, 'Состав связок изменился. Обновите каталог перед сохранением приоритетов.')
        for priority, offer in enumerate(routing.offers, 1):
            cur.execute('''UPDATE app.voucher_catalog_offers SET fulfillment_priority=%s, fulfillment_enabled=%s
                WHERE item_id=%s AND catalog_nominal_id=%s AND offer_id=%s AND active''',
                (priority, offer.enabled, item_id, catalog_nominal_id, offer.offer_id))
        cur.execute('''UPDATE app.voucher_catalog_nominals SET fulfillment_revision=fulfillment_revision+1
            WHERE item_id=%s AND catalog_nominal_id=%s''', (item_id, catalog_nominal_id))

    def unlink(self, item_id, offer_id):
        # Отвязка использует ту же блокировку, чтобы не потерять изменения порядка в другой карточке.
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute('SELECT item_id FROM app.voucher_catalog_items WHERE item_id=%s FOR UPDATE', (item_id,))
            if cur.fetchone() is None:
                raise HTTPException(404, 'Услуга каталога не найдена')
            cur.execute('''UPDATE app.voucher_catalog_offers SET active=false
                WHERE item_id=%s AND offer_id=%s AND active RETURNING catalog_nominal_id''', (item_id, offer_id))
            nominal = cur.fetchone()
            if nominal is None:
                raise HTTPException(404, 'Связка не найдена')
            cur.execute('''UPDATE app.voucher_catalog_nominals SET fulfillment_revision=fulfillment_revision+1
                WHERE catalog_nominal_id=%s''', (nominal[0],))
            conn.commit()

    def delete_item(self, item_id):
        # Общая блокировка не даёт добавить номинал во время удаления услуги и её содержимого.
        try:
            with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
                cur.execute('SELECT item_id FROM app.voucher_catalog_items WHERE item_id=%s FOR UPDATE', (item_id,))
                if cur.fetchone() is None:
                    raise HTTPException(404, 'Услуга каталога не найдена')
                cur.execute('DELETE FROM app.voucher_catalog_offers WHERE item_id=%s', (item_id,))
                cur.execute('DELETE FROM app.voucher_catalog_nominals WHERE item_id=%s', (item_id,))
                cur.execute('DELETE FROM app.voucher_catalog_items WHERE item_id=%s', (item_id,))
                conn.commit()
        except ForeignKeyViolation:
            # Если услуга или её содержимое используются, вся транзакция откатывается.
            raise HTTPException(409, 'Услуга или её номиналы уже используются. Сначала уберите их из связанных товаров или выдач.') from None

    def delete_nominal(self, item_id, catalog_nominal_id):
        # Удаляем номинал и все его связки атомарно; общая блокировка исключает одновременную привязку.
        try:
            with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
                cur.execute('SELECT item_id FROM app.voucher_catalog_items WHERE item_id=%s FOR UPDATE', (item_id,))
                if cur.fetchone() is None:
                    raise HTTPException(404, 'Услуга каталога не найдена')
                cur.execute('''SELECT catalog_nominal_id FROM app.voucher_catalog_nominals
                    WHERE item_id=%s AND catalog_nominal_id=%s FOR UPDATE''', (item_id, catalog_nominal_id))
                if cur.fetchone() is None:
                    raise HTTPException(404, 'Номинал не найден в этой услуге')
                cur.execute('''DELETE FROM app.voucher_catalog_offers
                    WHERE item_id=%s AND catalog_nominal_id=%s''', (item_id, catalog_nominal_id))
                cur.execute('''DELETE FROM app.voucher_catalog_nominals
                    WHERE item_id=%s AND catalog_nominal_id=%s''', (item_id, catalog_nominal_id))
                conn.commit()
        except ForeignKeyViolation:
            # Будущие ссылки из товаров или выдач должны запрещать удаление, а не обрывать историю.
            raise HTTPException(409, 'Номинал уже используется. Сначала уберите его из связанных товаров или выдач.') from None

    @staticmethod
    def write_snapshot(cur, offer_ids, job, snapshot):
        # Ошибка оставляет последнюю успешную величину; поздний ответ не затирает более свежий снимок.
        field, prefix = ('price', 'price') if job == 'prices' else ('stock_count', 'stock')
        cur.execute(f'''UPDATE app.voucher_catalog_offers SET
            {field}=CASE WHEN %s='' THEN %s ELSE {field} END,
            {prefix}_updated_at=CASE WHEN %s='' THEN %s ELSE {prefix}_updated_at END,
            {prefix}_checked_at=%s, {prefix}_error=%s
            WHERE offer_id=ANY(%s) AND active
              AND ({prefix}_checked_at IS NULL OR {prefix}_checked_at <= %s)''',
            (snapshot['error'], snapshot['value'], snapshot['error'], snapshot['checked_at'],
             snapshot['checked_at'], snapshot['error'], offer_ids, snapshot['checked_at']))

    def refresh(self, job):
        # Обходим только связанные предложения; повторяющиеся номиналы рассчитываем один раз.
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute('''SELECT offer_id, supplier_code, service_id, nominal_id
                FROM app.voucher_catalog_offers WHERE active ORDER BY supplier_code, service_id, nominal_id''')
            offers = cur.fetchall()
        errors = 0
        for code, provider in self.providers.items():
            selected = [row for row in offers if row[1] == code]
            if not selected:
                continue
            try:
                targets = provider.targets()
            except Exception:
                targets = []
            lookup = {(str(item['service_id']), str(item['nominal_id'])): item for item in targets}
            groups = {}
            for offer_id, _, service_id, nominal_id in selected:
                groups.setdefault((service_id, nominal_id), []).append(offer_id)
            stocks = {}
            for key, ids in groups.items():
                target = lookup.get(key)
                if target is None:
                    snapshot = {'value': None, 'checked_at': datetime.now(timezone.utc),
                                'error': 'Номинал отсутствует или каталог поставщика недоступен'}
                elif job == 'prices':
                    snapshot = provider.price(target)
                    time.sleep(provider.delay)
                else:
                    if key[0] not in stocks:
                        stocks[key[0]] = provider.stocks([item for item in targets if str(item['service_id']) == key[0]])
                        time.sleep(provider.delay)
                    snapshot = stocks[key[0]][key[1]]
                errors += len(ids) if snapshot['error'] else 0
                with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
                    self.write_snapshot(cur, ids, job, snapshot)
                    conn.commit()
        return errors

    def run_due(self, now=None):
        # Транзакционная блокировка исключает параллельные обходы и снимается даже при аварии worker.
        slots = schedule_slots(now or datetime.now(timezone.utc))
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute('SELECT pg_try_advisory_xact_lock(20260920, 1)')
            if not cur.fetchone()[0]:
                return
            cur.execute('SELECT job, slot FROM app.voucher_catalog_sync_runs')
            completed = dict(cur.fetchall())
            for job in ('stocks', 'prices'):
                slot = slots[job]
                if job in completed and completed[job] >= slot:
                    continue
                errors = self.refresh(job)
                cur.execute('''INSERT INTO app.voucher_catalog_sync_runs(job, slot, finished_at, errors)
                    VALUES (%s, %s, now(), %s) ON CONFLICT (job) DO UPDATE SET
                    slot=EXCLUDED.slot, finished_at=EXCLUDED.finished_at, errors=EXCLUDED.errors''',
                    (job, slot, errors))
            conn.commit()
