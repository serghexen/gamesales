"""Изолированные проверки QR: настоящий HTTP-маршрут и SQL в памяти, без рабочего приложения."""

import base64
import sqlite3
import struct
import unittest
import zlib
from inspect import signature
from types import SimpleNamespace

from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from domains.accounts_api import mount_accounts_routes
from domains.account_authenticator_image import MAX_IMAGE_BYTES


def png_data_url(color=0):
    # Синтетический PNG 1×1 не содержит реального секрета аутентификатора.
    def chunk(kind, data):
        # Собираем корректные PNG-чанки с контрольными суммами без библиотек изображений.
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    data += chunk(b'IDAT', zlib.compress(bytes([0, color, color, color]))) + chunk(b'IEND', b'')
    return 'data:image/png;base64,' + base64.b64encode(data).decode()


class MemoryConnection:
    def __init__(self, conn):
        # Подменяем только драйвер: все запросы выполняются SQL-движком.
        self.conn = conn

    def __enter__(self):
        # Каждый запрос получает транзакцию, как при psycopg.connect.
        return self

    def __exit__(self, kind, value, traceback):
        # Ошибка в последующих секретах откатывает и предварительную запись изображения.
        if kind:
            self.conn.rollback()
        else:
            self.conn.commit()

    def commit(self):
        # Обработчик сам подтверждает успешное сохранение.
        self.conn.commit()

    def execute(self, sql, params=()):
        # Переводим только синтаксис параметров PostgreSQL и блокировку строки.
        sql = sql.replace(' FOR UPDATE', '')
        if 'ANY(%s)' in sql:
            values = params[-1]
            sql = sql.replace('= ANY(%s)', 'IN (' + ','.join('?' for _ in values) + ')')
            params = (*params[:-1], *values)
        return self.conn.execute(sql.replace('%s', '?'), params)


class AuthenticatorImageTests(unittest.TestCase):
    def setUp(self):
        # Стартуем только маршруты аккаунтов, без lifespan и сетевых соединений.
        conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.addCleanup(conn.close)
        conn.executescript('''
            ATTACH DATABASE ':memory:' AS app;
            CREATE TABLE app.accounts(account_id INTEGER PRIMARY KEY);
            INSERT INTO app.accounts VALUES(5);
            CREATE TABLE app.account_secrets(account_id INTEGER, secret_key TEXT, secret_value TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(account_id,secret_key));
            CREATE TABLE app.account_reserve_codes(account_id INTEGER, reserve_key TEXT, reserve_id INTEGER, is_listed BOOLEAN);
        ''')
        self.db = MemoryConnection(conn)
        app = FastAPI()

        def authenticated(x_role: str = Header(default='')):
            # Заголовок используется только тестовым приложением вместо настоящей авторизации.
            if not x_role:
                raise HTTPException(401)
            return SimpleNamespace(role=x_role, username='test-user')

        def require_role(*roles):
            # Проверяем, что маршрут объявляет те же роли, что чтение остальных секретов.
            def dependency(x_role: str = Header(default='')):
                user = authenticated(x_role)
                if user.role not in roles:
                    raise HTTPException(403)
                return user
            return dependency

        def ensure_exists(db, account_id):
            # Несуществующий аккаунт не может получить или сохранить изображение.
            if not db.execute('SELECT 1 FROM app.accounts WHERE account_id=%s', (account_id,)).fetchone():
                raise HTTPException(404)

        deps = {name: (lambda *args: None) for name in signature(mount_accounts_routes).parameters if name != 'app'}
        deps.update(DB_DSN='in-memory', psycopg=SimpleNamespace(connect=lambda _: self.db),
                    q1=lambda db, sql, params=(): db.execute(sql, params).fetchone(),
                    qall=lambda db, sql, params=(): db.execute(sql, params).fetchall(),
                    exec1=lambda db, sql, params=(): db.execute(sql, params).rowcount,
                    ensure_account_exists=ensure_exists, require_role=require_role, get_current_user=authenticated,
                    b64_encode=lambda value: base64.b64encode(value.encode()).decode())
        mount_accounts_routes(app, **deps)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.headers = {'X-Role': 'operator'}
        self.path = '/accounts/5'

    def read(self):
        # Читаем сохранённую картинку через тот же маршрут, что карточка.
        return self.client.get(self.path + '/authenticator-image', headers=self.headers)

    def save(self, image, version='', **extra):
        # Сохранение изображения входит в общую операцию секретов.
        return self.client.put(self.path + '/secrets', headers=self.headers, json={
            'authenticator_image': image, 'expected_authenticator_image_version': version, **extra,
        })

    def test_attach_replace_remove_and_exclude_from_lists(self):
        # Изображение доступно в карточке, но не раздувает одиночный и массовый справочники.
        self.assertEqual(self.read().json(), {'image': '', 'version': ''})
        self.assertEqual(self.save(png_data_url()).status_code, 200)
        response = self.read()
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(response.json()['image'], png_data_url())
        version = response.json()['version']
        self.assertEqual(len(version), 64)
        self.assertEqual(self.client.get(self.path + '/secrets', headers=self.headers).json(), [])
        self.assertEqual(self.client.post('/accounts/secrets/batch', headers=self.headers, json={'account_ids': [5]}).json(), [{'account_id': 5, 'secrets': []}])
        self.assertEqual(self.save(png_data_url(255), version).status_code, 200)
        self.assertEqual(self.read().json()['image'], png_data_url(255))
        self.assertEqual(self.save('', self.read().json()['version']).status_code, 200)
        self.assertEqual(self.read().json(), {'image': '', 'version': ''})

    def test_rejects_stale_replacement_and_deletion(self):
        # Вторая открытая карточка не может заменить или удалить чужое новое изображение.
        self.save(png_data_url())
        version = self.read().json()['version']
        self.save(png_data_url(255), version)
        for image in ('', png_data_url()):
            with self.subTest(deleting=not image):
                self.assertEqual(self.save(image, version).status_code, 409)
        self.assertEqual(self.read().json()['image'], png_data_url(255))

    def test_rejects_unsupported_mismatched_and_oversized_images(self):
        # Расширению и MIME клиента не доверяем; SVG и внешние URL не допускаются.
        oversized_dimensions = bytearray(base64.b64decode(png_data_url().split(',')[1]))
        oversized_dimensions[16:20] = (5000).to_bytes(4, 'big')
        invalid = [
            'data:image/png;base64,' + base64.b64encode(oversized_dimensions).decode(),
            'https://example.test/image.png', 'data:image/svg+xml;base64,PHN2Zz4=',
            'data:image/png;base64,YmFk', png_data_url().replace('image/png', 'image/jpeg'),
            'data:image/png;base64,' + base64.b64encode(b'x' * (MAX_IMAGE_BYTES + 1)).decode(),
        ]
        for image in invalid:
            with self.subTest(kind=image[:25]):
                self.assertIn(self.save(image).status_code, (400, 422))
        self.assertEqual(self.read().json()['image'], '')

    def test_error_in_other_secrets_rolls_back_image(self):
        # Ошибка общего запроса не оставляет отдельно сохранённый QR.
        response = self.save(png_data_url(), upserts=[{'secret_key': '', 'secret_value': 'bad'}])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.read().json()['image'], '')

    def test_old_secret_endpoints_cannot_bypass_version_check(self):
        # Все старые способы записи этого ключа блокируются.
        key = 'authenticator_image'
        self.assertEqual(self.client.post(self.path + '/secrets', headers=self.headers, json={'secret_key': key, 'secret_value': png_data_url()}).status_code, 400)
        self.assertEqual(self.client.put(self.path + '/secrets', headers=self.headers, json={'upserts': [{'secret_key': key, 'secret_value': png_data_url()}]}).status_code, 400)
        self.assertEqual(self.client.put(self.path + '/secrets', headers=self.headers, json={'delete_keys': [key]}).status_code, 400)
        self.assertEqual(self.client.delete(self.path + '/secrets/' + key, headers=self.headers).status_code, 400)
        self.assertEqual(self.client.put(self.path + '/secrets', headers=self.headers, json={'authenticator_image': png_data_url()}).status_code, 400)

    def test_access_matches_account_secrets(self):
        # QR не читается анонимно или ролью без доступа к секретам.
        for role, status in [('', 401), ('viewer', 403), ('operator', 200), ('manager', 200), ('admin', 200), ('owner', 200)]:
            with self.subTest(role=role):
                headers = {'X-Role': role} if role else {}
                self.assertEqual(self.client.get(self.path + '/authenticator-image', headers=headers).status_code, status)
                self.assertEqual(self.client.put(self.path + '/secrets', headers=headers, json={'authenticator_image': '', 'expected_authenticator_image_version': ''}).status_code, status)
        self.assertEqual(self.client.get('/accounts/999/authenticator-image', headers=self.headers).status_code, 404)


if __name__ == '__main__':
    unittest.main()
