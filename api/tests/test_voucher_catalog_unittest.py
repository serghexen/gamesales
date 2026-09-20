"""Изолированные проверки каталога без сети, staging и платёжных операций."""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from domains.voucher_catalog_api import mount_voucher_catalog_routes, VoucherBindingIn, VoucherNominalIn
from domains.voucher_catalog_service import (
    InterhubVoucherProvider, VoucherCatalogService, schedule_slots, valid_price, voucher_targets,
)


def services():
    # Два номинала одной услуги позволяют проверить группировку запросов остатков.
    return [{'service_id': 10, 'title': 'Voucher', 'type': 'VOUCHER', 'fields': [
        {'name': 'nominal', 'value_list': [{'id': 1, 'title': 'USD 10'}, {'id': 2, 'title': 'USD 20'}]},
    ]}]


def database():
    # Все соединения работают с управляемым курсором без реального подключения к БД.
    db = MagicMock()
    conn = db.connect.return_value.__enter__.return_value
    cur = conn.cursor.return_value.__enter__.return_value
    return db, conn, cur


class VoucherProviderTests(TestCase):
    def test_only_active_vouchers_are_available(self):
        # Пополнения и выключенные ваучеры не должны попадать в каталог и расписание.
        catalog = services()
        catalog += [{**catalog[0], 'service_id': 20, 'type': 'TOP_UP_FIXED'},
                    {**catalog[0], 'service_id': 30, 'raw': {'active': False}}]
        self.assertEqual([row['nominal_id'] for row in voucher_targets(catalog)], [1, 2])

    def test_price_keeps_precision_and_rejects_missing_raw_amount(self):
        # Старый normalizer заменяет отсутствующее поле нулём, поэтому проверяем исходный ответ.
        self.assertEqual(valid_price({'success': True, 'fixed_amount': 0, 'raw': {'fixed_amount': '123.456789'}}), Decimal('123.456789'))
        self.assertIsNone(valid_price({'success': True, 'fixed_amount': 0, 'raw': {}}))
        for value in [None, True, -1, 'NaN', 'Infinity', '100000000000000']:
            self.assertIsNone(valid_price({'success': True, 'fixed_amount': value}))
        self.assertEqual(valid_price({'success': True, 'fixed_amount': 0}), Decimal(0))
        self.assertIsNone(valid_price({'success': False, 'fixed_amount': 100}))

    def test_initial_snapshot_reads_live_price_and_zero_stock(self):
        # Создание связки получает независимые живые значения, включая допустимый нулевой остаток.
        detail = Mock(return_value=[{'name': 'USD 10.00', 'count': 0}])
        calculate = Mock(return_value={'success': True, 'fixed_amount': '900.15'})
        provider = InterhubVoucherProvider(services, detail, calculate, 0)
        targets = provider.targets()
        price, stock = provider.snapshot(targets[0], targets)
        self.assertEqual(price['value'], Decimal('900.15'))
        self.assertEqual(stock['value'], 0)
        self.assertEqual(stock['error'], '')
        detail.assert_called_once_with(10)
        self.assertEqual(calculate.call_args.args[0]['params'], {'nominal': 1})

    def test_stock_failure_does_not_discard_successful_price(self):
        # У поставщика могут независимо работать calculate и detail.
        provider = InterhubVoucherProvider(services, Mock(side_effect=RuntimeError('private transport error')),
                                          Mock(return_value={'success': True, 'fixed_amount': 20}), 0)
        targets = provider.targets()
        price, stock = provider.snapshot(targets[0], targets)
        self.assertEqual(price['value'], 20)
        self.assertIsNone(stock['value'])
        self.assertTrue(stock['error'])
        self.assertNotIn('private', stock['error'])

    def test_duplicates_outside_selected_offer_are_ambiguous(self):
        # Даже несвязанный номинал с таким же именем должен запретить угадывание остатка.
        catalog = services()
        catalog[0]['fields'][0]['value_list'][1]['title'] = 'USD 10.00'
        provider = InterhubVoucherProvider(lambda: catalog, lambda _: [{'name': 'USD 10', 'count': 5}],
                                          lambda _: {'success': True, 'fixed_amount': 20}, 0)
        targets = provider.targets()
        _, stock = provider.snapshot(targets[0], targets)
        self.assertIsNone(stock['value'])
        self.assertTrue(stock['error'])


class VoucherScheduleTests(TestCase):
    def test_batch_reads_catalog_and_stock_once_and_prices_each_nominal(self):
        # Пакет сохраняет собственные имена и не умножает одинаковые запросы service/detail.
        db, _, _ = database()
        provider = InterhubVoucherProvider(Mock(side_effect=services),
            Mock(return_value=[{'name': 'USD 10', 'count': 2}, {'name': 'USD 20', 'count': 4}]),
            Mock(return_value={'success': True, 'fixed_amount': 42}), 0)
        service = VoucherCatalogService(db, 'unused', {'interhub': provider})
        rows = service.prepare_nominals([
            VoucherNominalIn(name='Наши 10 USD', binding=VoucherBindingIn(service_id='10', nominal_id='1')),
            VoucherNominalIn(name='Наши 20 USD', binding=VoucherBindingIn(service_id='10', nominal_id='2')),
        ])
        self.assertEqual([row['name'] for row in rows], ['Наши 10 USD', 'Наши 20 USD'])
        self.assertEqual([row['stock']['value'] for row in rows], [2, 4])
        provider.get_services.assert_called_once()
        provider.get_detail.assert_called_once_with(10)
        self.assertEqual(provider.calculate.call_count, 2)

    def test_invalid_last_nominal_makes_no_price_or_stock_requests(self):
        # Сначала валидируется весь выбор, чтобы ошибочная последняя строка не создала частичный набор.
        db, _, _ = database()
        provider = InterhubVoucherProvider(services, Mock(), Mock(), 0)
        service = VoucherCatalogService(db, 'unused', {'interhub': provider})
        with self.assertRaises(Exception) as raised:
            service.prepare_nominals([
                VoucherNominalIn(name='10 USD', binding=VoucherBindingIn(service_id='10', nominal_id='1')),
                VoucherNominalIn(name='Missing', binding=VoucherBindingIn(service_id='10', nominal_id='999')),
            ])
        self.assertEqual(raised.exception.status_code, 422)
        provider.get_detail.assert_not_called()
        provider.calculate.assert_not_called()

    def test_duplicate_names_or_own_ids_are_rejected(self):
        # Повторное имя и две правки одного ID в пакете должны иметь однозначную ошибку.
        db, _, _ = database()
        service = VoucherCatalogService(db, 'unused', {})
        for rows in ([VoucherNominalIn(name='Same'), VoucherNominalIn(name=' Same ')],
                     [VoucherNominalIn(name='A', catalog_nominal_id=1), VoucherNominalIn(name='B', catalog_nominal_id=1)]):
            with self.assertRaises(Exception) as raised:
                service.prepare_nominals(rows)
            self.assertEqual(raised.exception.status_code, 422)

    def test_foreign_nominal_id_rolls_back_instead_of_creating_binding(self):
        # Номинал другой услуги нельзя переименовать или связать через ID в запросе.
        db, conn, cur = database()
        cur.fetchone.side_effect = [(7,), None]
        service = VoucherCatalogService(db, 'unused', {})
        with self.assertRaises(Exception) as raised:
            service.save_item(None, 'admin', item_id=7, nominals=[VoucherNominalIn(name='Wrong', catalog_nominal_id=99)])
        self.assertEqual(raised.exception.status_code, 404)
        conn.commit.assert_not_called()
        self.assertTrue(any('WHERE item_id=%s AND catalog_nominal_id=%s' in call.args[0] for call in cur.execute.call_args_list))

    def test_moscow_nine_boundary_and_hourly_slots(self):
        # 09:00 МСК соответствует 06:00 UTC; до границы берём вчерашний ежедневный слот.
        before = schedule_slots(datetime(2026, 9, 20, 5, 59, tzinfo=timezone.utc))
        after = schedule_slots(datetime(2026, 9, 20, 6, 0, tzinfo=timezone.utc))
        self.assertEqual(before['prices'].astimezone(timezone.utc), datetime(2026, 9, 19, 6, tzinfo=timezone.utc))
        self.assertEqual(after['prices'].astimezone(timezone.utc), datetime(2026, 9, 20, 6, tzinfo=timezone.utc))
        self.assertEqual(before['stocks'].astimezone(timezone.utc), datetime(2026, 9, 20, 5, tzinfo=timezone.utc))

    def test_second_worker_does_not_refresh_when_lock_is_busy(self):
        # При занятой PostgreSQL-блокировке второй worker не делает внешних запросов.
        db, _, cur = database()
        cur.fetchone.return_value = (False,)
        service = VoucherCatalogService(db, 'unused', {})
        service.refresh = Mock()
        service.run_due()
        service.refresh.assert_not_called()

    def test_persisted_slots_survive_process_restart(self):
        # Уже выполненные часы и дни не запускаются заново после создания нового сервиса.
        now = datetime(2026, 9, 20, 10, 42, tzinfo=timezone.utc)
        db, _, cur = database()
        cur.fetchone.return_value = (True,)
        cur.fetchall.return_value = list(schedule_slots(now).items())
        service = VoucherCatalogService(db, 'unused', {})
        service.refresh = Mock()
        service.run_due(now)
        service.refresh.assert_not_called()

    def test_missed_runs_are_caught_up_once(self):
        # За длительный простой достаточно одного свежего снимка каждого вида.
        db, conn, cur = database()
        cur.fetchone.return_value = (True,)
        cur.fetchall.return_value = []
        service = VoucherCatalogService(db, 'unused', {})
        service.refresh = Mock(return_value=2)
        service.run_due(datetime(2026, 9, 20, 10, tzinfo=timezone.utc))
        self.assertEqual([call.args[0] for call in service.refresh.call_args_list], ['stocks', 'prices'])
        self.assertEqual(sum('INSERT INTO app.voucher_catalog_sync_runs' in call.args[0] for call in cur.execute.call_args_list), 2)
        conn.commit.assert_called_once()

    def test_hourly_refresh_only_reads_linked_services_and_deduplicates(self):
        # Остатки одной услуги читаем один раз, цену в часовом обходе вообще не запрашиваем.
        db, _, cur = database()
        cur.fetchall.return_value = [(1, 'interhub', '10', '1'), (2, 'interhub', '10', '2'), (3, 'interhub', '10', '1')]
        provider = InterhubVoucherProvider(services, Mock(return_value=[{'name': 'USD 10', 'count': 0}, {'name': 'USD 20', 'count': 4}]), Mock(), 0)
        service = VoucherCatalogService(db, 'unused', {'interhub': provider})
        service.write_snapshot = Mock()
        self.assertEqual(service.refresh('stocks'), 0)
        provider.get_detail.assert_called_once_with(10)
        provider.calculate.assert_not_called()
        self.assertEqual(service.write_snapshot.call_count, 2)
        self.assertEqual(service.write_snapshot.call_args_list[0].args[1], [1, 3])

    def test_daily_refresh_only_calculates_linked_nominals(self):
        # Дневной обход не трогает несвязанный второй номинал и не запрашивает остатки.
        db, _, cur = database()
        cur.fetchall.return_value = [(1, 'interhub', '10', '1'), (3, 'interhub', '10', '1')]
        provider = InterhubVoucherProvider(services, Mock(), Mock(return_value={'success': True, 'fixed_amount': 42}), 0)
        service = VoucherCatalogService(db, 'unused', {'interhub': provider})
        service.write_snapshot = Mock()
        self.assertEqual(service.refresh('prices'), 0)
        provider.calculate.assert_called_once()
        provider.get_detail.assert_not_called()

    def test_unknown_nominal_is_marked_as_error_without_guessing(self):
        # Исчезнувшая услуга оставляет ошибку, а не нулевую цену или случайный номинал.
        db, _, cur = database()
        cur.fetchall.return_value = [(1, 'interhub', '999', '1')]
        provider = InterhubVoucherProvider(services, Mock(), Mock(), 0)
        service = VoucherCatalogService(db, 'unused', {'interhub': provider})
        service.write_snapshot = Mock()
        self.assertEqual(service.refresh('prices'), 1)
        snapshot = service.write_snapshot.call_args.args[3]
        self.assertIsNone(snapshot['value'])
        self.assertTrue(snapshot['error'])
        provider.calculate.assert_not_called()

    def test_snapshot_sql_preserves_success_and_rejects_older_reply(self):
        # Неудачная и запоздавшая проверки не затирают ранее полученные данные.
        cur = Mock()
        checked_at = datetime.now(timezone.utc)
        VoucherCatalogService.write_snapshot(cur, [1], 'stocks', {'value': None, 'error': 'Ошибка', 'checked_at': checked_at})
        sql, params = cur.execute.call_args.args
        self.assertIn('ELSE stock_count END', sql)
        self.assertIn('stock_checked_at <= %s', sql)
        self.assertIn('AND active', sql)
        self.assertEqual(params[0], 'Ошибка')
        self.assertEqual(params[-1], checked_at)

    def test_invalid_binding_creates_no_item(self):
        # Подмена ID через прямой запрос отклоняется до INSERT.
        db, _, cur = database()
        provider = InterhubVoucherProvider(services, Mock(), Mock(), 0)
        service = VoucherCatalogService(db, 'unused', {'interhub': provider})
        with self.assertRaises(Exception) as raised:
            service.save_item('Test', 'admin', binding=VoucherBindingIn(service_id='10', nominal_id='999'))
        self.assertEqual(raised.exception.status_code, 422)
        cur.execute.assert_not_called()


class VoucherCatalogApiTests(TestCase):
    def setUp(self):
        # Минимальное приложение изолирует тесты прав от глобального lifespan и настоящего DSN.
        self.service = Mock()
        self.service.can_view.return_value = True
        self.service.list_items.return_value = {'items': [], 'suppliers': [], 'runs': []}
        self.service.save_item.return_value = {'item_id': 1}
        self.user = SimpleNamespace(role='admin', username='admin')
        self.app = FastAPI()
        mount_voucher_catalog_routes(self.app, service=self.service, get_current_user=lambda: self.user)
        self.client = TestClient(self.app)

    def test_admin_can_create_and_edit_catalog_item(self):
        # Связка передаётся в доменный сервис вместе с собственным наименованием.
        response = self.client.post('/voucher-catalog/items', json={'name': 'Наш ваучер', 'binding': {'service_id': '10', 'nominal_id': '1'}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.save_item.call_args.kwargs['binding'].supplier_code, 'interhub')
        response = self.client.put('/voucher-catalog/items/1', json={'name': 'Другое имя'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.save_item.call_args.kwargs['item_id'], 1)

    def test_view_permission_does_not_allow_editing(self):
        # Оператор с разрешённым просмотром получает таблицу, но не может менять связки.
        self.user.role = 'operator'
        self.assertFalse(self.client.get('/voucher-catalog').json()['can_edit'])
        self.assertEqual(self.client.post('/voucher-catalog/items', json={'name': 'Test'}).status_code, 403)
        self.assertEqual(self.client.delete('/voucher-catalog/items/1/offers/2').status_code, 403)
        self.service.save_item.assert_not_called()

    def test_batch_endpoint_does_not_overwrite_service_name(self):
        # Добавление номиналов сохраняет имя родительской услуги, даже если другой редактор его изменил.
        response = self.client.post('/voucher-catalog/items/7/nominals', json={'nominals': [
            {'name': '500 TRY', 'binding': {'service_id': '10', 'nominal_id': '1'}}, {'name': '1000 TRY'},
        ]})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.service.save_item.call_args.args[0])
        self.assertEqual(self.service.save_item.call_args.kwargs['item_id'], 7)
        self.assertEqual(len(self.service.save_item.call_args.kwargs['nominals']), 2)
        self.user.role = 'operator'
        self.assertEqual(self.client.post('/voucher-catalog/items/7/nominals', json={'nominals': [{'name': 'A'}]}).status_code, 403)

    def test_empty_and_oversized_batch_are_rejected(self):
        # Ограничение размера защищает API от случайного полного импорта всего каталога поставщика.
        for rows in [[], [{'name': str(index)} for index in range(101)]]:
            response = self.client.post('/voucher-catalog/items/7/nominals', json={'nominals': rows})
            self.assertEqual(response.status_code, 422)
        self.service.save_item.assert_not_called()

    def test_denied_section_blocks_even_direct_get(self):
        # Скрытая вкладка защищается правами API, а не только интерфейсом.
        self.service.can_view.return_value = False
        self.assertEqual(self.client.get('/voucher-catalog').status_code, 403)
        self.assertEqual(self.client.get('/voucher-catalog/suppliers/interhub/nominals').status_code, 403)
        self.service.list_items.assert_not_called()

    def test_list_reads_database_without_provider_calls(self):
        # Чтение таблицы не запускает calculate или refresh.
        self.assertEqual(self.client.get('/voucher-catalog').status_code, 200)
        self.service.options.assert_not_called()
        self.service.refresh.assert_not_called()
