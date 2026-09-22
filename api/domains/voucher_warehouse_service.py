"""Собственный склад ключей по SKU каталога, независимый от пулов селлера."""
from datetime import datetime
from hashlib import sha256
from zoneinfo import ZoneInfo
import os
from fastapi import HTTPException


def warehouse_secret():
    # Используем уже настроенное шифрование пулов, не копируя ключи между хранилищами.
    secret = os.getenv('MARKETPLACE_KEY_POOL_SECRET', '').strip()
    if len(secret) < 32:
        raise HTTPException(503, 'Не настроен секрет хранения ключей MARKETPLACE_KEY_POOL_SECRET')
    return secret


class VoucherWarehouseService:
    def __init__(self, db, dsn):
        # Соединения передаются снаружи, поэтому модуль сам не запускает задачи и миграции.
        self.db, self.dsn = db, dsn

    def can_view(self, role):
        # Раздел имеет собственное право просмотра; работа с ключами разрешается отдельно.
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute('SELECT can_view FROM app.role_ui_sections WHERE role_code=%s AND section_code=%s', (role, 'voucher-warehouse'))
            row = cur.fetchone()
        return bool(row[0]) if row else role in {'admin', 'owner'}

    @staticmethod
    def rows(cur):
        # Имена колонок берём из запроса, чтобы ключи не попадали в ответ случайными позициями.
        names = [column.name for column in cur.description]
        return [dict(zip(names, row)) for row in cur.fetchall()]

    @staticmethod
    def lock_nominal(cur, nominal_id):
        # Порядок блокировок совпадает с каталогом и исключает удаление во время загрузки ключей.
        cur.execute('''SELECT i.item_id FROM app.voucher_catalog_items i
            JOIN app.voucher_catalog_nominals n ON n.item_id=i.item_id
            WHERE n.catalog_nominal_id=%s FOR UPDATE OF i''', (nominal_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, 'Номинал не найден в каталоге')
        cur.execute('SELECT catalog_nominal_id FROM app.voucher_catalog_nominals WHERE catalog_nominal_id=%s FOR UPDATE', (nominal_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, 'Номинал не найден в каталоге')

    def list_positions(self):
        # Представление включает все существующие и новые номиналы даже без загруженных ключей.
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute('SELECT * FROM app.voucher_warehouse_stock ORDER BY lower(service_name), catalog_nominal_id')
            return self.rows(cur)

    def set_price(self, nominal_id, price, username, *, expected_updated_at):
        # Одна цена действует для всего пула; NULL означает, что цена ещё не задана.
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            self.lock_nominal(cur, nominal_id)
            # Старое окно не может молча перезаписать цену, сохранённую другим владельцем.
            cur.execute('SELECT updated_at FROM app.voucher_warehouse_positions WHERE catalog_nominal_id=%s', (nominal_id,))
            current = cur.fetchone()
            if (current[0] if current else None) != expected_updated_at:
                raise HTTPException(409, 'Цена пула изменилась в другом окне. Проверьте актуальную цену перед повторным сохранением.')
            cur.execute('''INSERT INTO app.voucher_warehouse_positions(catalog_nominal_id,price,updated_by)
                VALUES(%s,%s,%s) ON CONFLICT(catalog_nominal_id) DO UPDATE
                SET price=EXCLUDED.price,updated_by=EXCLUDED.updated_by,updated_at=clock_timestamp()
                RETURNING updated_at''', (nominal_id, price, username))
            updated_at = cur.fetchone()[0]
            conn.commit()
        return {'ok': True, 'price_updated_at': updated_at}

    def list_keys(self, nominal_id, page, page_size):
        # Обычное чтение возвращает только маски; расшифровка доступна отдельным запросом.
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            # Пул проверяет соединение через SELECT 1; завершаем его пустую транзакцию перед выбором изоляции.
            conn.rollback()
            # Счётчики, граница очистки и страница ключей должны относиться к одному снимку.
            cur.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            # Граница снимка защищает новые поступления от удаления из давно открытого списка.
            cur.execute('''SELECT w.*, (SELECT COALESCE(MAX(key_id),0) FROM app.voucher_warehouse_keys k
                WHERE k.catalog_nominal_id=w.catalog_nominal_id) AS through_key_id
                FROM app.voucher_warehouse_stock w WHERE w.catalog_nominal_id=%s''', (nominal_id,))
            positions = self.rows(cur)
            if not positions:
                raise HTTPException(404, 'Номинал не найден в каталоге')
            stats = positions[0]
            pages = max(1, (stats['total'] + page_size - 1) // page_size)
            page = min(page, pages)
            cur.execute('''SELECT key_id AS id, '••••' || code_suffix AS masked_code,
                CASE WHEN status='free' AND expires_at < (now() AT TIME ZONE 'Europe/Moscow')::date THEN 'expired' ELSE status END AS status,
                expires_at,created_at FROM app.voucher_warehouse_keys WHERE catalog_nominal_id=%s
                ORDER BY key_id DESC LIMIT %s OFFSET %s''', (nominal_id, page_size, (page - 1) * page_size))
            return {**stats, 'page': page, 'page_size': page_size, 'items': self.rows(cur)}

    def add_keys(self, nominal_id, codes, expires_at, username):
        # Проверяем весь пакет до записи; повторы игнорируем, а неверные строки не теряем молча.
        prepared = [code.strip() for code in codes]
        if any(not code or len(code) > 1024 for code in prepared):
            raise HTTPException(422, 'Каждый ключ должен содержать от 1 до 1024 символов')
        # NUL не поддерживается PostgreSQL, а переносы внутри строки склеивают разные ключи.
        if any(any(ord(char) < 32 or ord(char) == 127 for char in code) for code in prepared):
            raise HTTPException(422, 'Ключ не должен содержать переносы строк или управляющие символы')
        if expires_at and expires_at < datetime.now(ZoneInfo('Europe/Moscow')).date():
            raise HTTPException(422, 'Срок действия ключей уже истёк')
        secret = warehouse_secret()
        added = 0
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            self.lock_nominal(cur, nominal_id)
            # Общий порядок вставки предотвращает взаимную блокировку пересекающихся пакетов.
            for code in sorted(set(prepared)):
                digest = sha256(f'voucher-warehouse:v1:{code}'.encode()).hexdigest()
                cur.execute('''INSERT INTO app.voucher_warehouse_keys
                    (catalog_nominal_id,code_ciphertext,code_hash,code_suffix,expires_at,created_by)
                    VALUES(%s,pgp_sym_encrypt(%s,%s,'cipher-algo=aes256, compress-algo=0'),%s,%s,%s,%s)
                    ON CONFLICT(code_hash) DO NOTHING RETURNING key_id''',
                    (nominal_id, code, secret, digest, code[-4:] if len(code) > 4 else '', expires_at, username))
                added += int(cur.fetchone() is not None)
            conn.commit()
        return {'ok': True, 'added': added, 'duplicates': len(prepared) - added}

    def reveal(self, nominal_id, key_id):
        # Раскрываем ровно один ключ выбранного SKU, не меняя его доступность.
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute('''SELECT pgp_sym_decrypt(code_ciphertext,%s) FROM app.voucher_warehouse_keys
                WHERE catalog_nominal_id=%s AND key_id=%s''', (warehouse_secret(), nominal_id, key_id))
            row = cur.fetchone()
        if row is None:
            raise HTTPException(404, 'Ключ не найден в этой позиции')
        return {'id': key_id, 'code': row[0]}

    def delete_keys(self, nominal_id, key_id=None, *, through_key_id=None):
        # Зарезервированные и выданные ключи не удаляем; свободные удаляются после подтверждения в UI.
        if key_id is None and (through_key_id is None or through_key_id <= 0):
            raise HTTPException(422, 'Обновите список ключей перед удалением')
        with self.db.connect(self.dsn) as conn, conn.cursor() as cur:
            self.lock_nominal(cur, nominal_id)
            query = "DELETE FROM app.voucher_warehouse_keys WHERE catalog_nominal_id=%s AND status='free'"
            params = (nominal_id,)
            if key_id is not None:
                query += ' AND key_id=%s'
                params += (key_id,)
            else:
                # Ключи, добавленные после снимка, сохраняются даже при подтверждённой очистке.
                query += ' AND key_id<=%s'
                params += (through_key_id,)
            cur.execute(query + ' RETURNING key_id', params)
            removed = len(cur.fetchall())
            if key_id is not None and not removed:
                raise HTTPException(409, 'Можно удалить только свободный ключ из этой позиции')
            conn.commit()
        return {'ok': True, 'removed': removed}
