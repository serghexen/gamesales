"""Локальный режим не должен создавать фоновые задачи или подключаться к production."""

import asyncio
from unittest import TestCase
from unittest.mock import patch

import app as app_module
from local_ui_runtime import local_interhub_tunnel_port, require_staging_tunnel


class LocalUiRuntimeTests(TestCase):
    def test_health_only_checks_connection_without_schema_or_user_changes(self):
        # Проверка после миграции не должна запускать исторический DDL или добавлять пользователей.
        with patch.object(app_module, '_pool') as pool, \
             patch.object(app_module, 'q1') as query, \
             patch.object(app_module, 'init_auth_schema') as schema, \
             patch.object(app_module, 'ensure_admin_user') as admin:
            self.assertEqual(app_module.health(), {'ok': True})
            query.assert_called_once_with(pool.connection.return_value.__enter__.return_value, 'SELECT 1')
            schema.assert_not_called()
            admin.assert_not_called()

    def test_only_staging_tunnel_is_accepted(self):
        # Даже корректная строка подключения к другой БД должна быть отклонена без вывода реквизитов.
        require_staging_tunnel('postgresql://user:secret@127.0.0.1:5433/gamesales_staging')
        for target in ['postgresql://user:secret@127.0.0.1:5433/gamesales',
                       'postgresql://user:secret@production:5432/gamesales_staging',
                       'postgresql://user:secret@127.0.0.1:5432/gamesales_staging', 'broken']:
            with self.assertRaises(RuntimeError) as raised:
                require_staging_tunnel(target)
            self.assertNotIn('secret', str(raised.exception))

    def test_proxy_uses_tunnel_port_and_rejects_invalid_values(self):
        # Настройка удалённого proxy не может обойти локальный SSH-туннель в режиме просмотра.
        self.assertEqual(local_interhub_tunnel_port({}), 3128)
        self.assertEqual(local_interhub_tunnel_port({'INTERHUB_TUNNEL_LOCAL_PORT': '4128'}), 4128)
        for port in ['', 'bad', '0', '65536', '-1']:
            with self.assertRaises(RuntimeError):
                local_interhub_tunnel_port({'INTERHUB_TUNNEL_LOCAL_PORT': port})

    def test_local_lifespan_keeps_pool_but_creates_no_background_tasks(self):
        # Режим сохраняет рабочие HTTP-ручки, но не запускает ни старые циклы, ни новый каталог.
        async def run():
            # Контекст должен открыть и закрыть пул обычным жизненным циклом API.
            async with app_module.lifespan(app_module.app):
                self.assertIs(app_module._pool, pool_factory.return_value)
        with patch.object(app_module, '_LOCAL_UI_MODE', True), \
             patch.object(app_module, 'DB_DSN', 'postgresql://127.0.0.1:5433/gamesales_staging'), \
             patch.object(app_module, 'ConnectionPool') as pool_factory, \
             patch.object(app_module.asyncio, 'create_task') as create_task:
            asyncio.run(run())
            create_task.assert_not_called()
            pool_factory.return_value.close.assert_called_once()
            self.assertIsNone(app_module._pool)

    def test_wrong_database_is_rejected_before_opening_pool(self):
        # Проверка адреса должна срабатывать до первого сетевого подключения.
        async def run():
            # Ошибка входа в контекст не должна оставить работающих ресурсов.
            async with app_module.lifespan(app_module.app):
                self.fail('Unexpected startup')
        with patch.object(app_module, '_LOCAL_UI_MODE', True), \
             patch.object(app_module, 'DB_DSN', 'postgresql://production/gamesales'), \
             patch.object(app_module, 'ConnectionPool') as pool_factory:
            with self.assertRaises(RuntimeError):
                asyncio.run(run())
            pool_factory.assert_not_called()
