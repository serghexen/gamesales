"""Проверки единого каталога без сети и реальной БД."""
from datetime import datetime, timezone, timedelta
from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch
from fastapi import HTTPException
from domains.supplier_catalog import SupplierCatalog, discovery_targets
from domains.voucher_catalog_service import InterhubVoucherProvider, VoucherCatalogService
from test_voucher_catalog_unittest import services, database
from domains.interhub_service import build_interhub_service


class SupplierCatalogTests(TestCase):
    def build(self, offline=False):
        # Изолированный адаптер не может выполнить check/pay: таких методов у него нет.
        db, conn, cur = database()
        cur.fetchone.return_value = (True,)
        cur.fetchall.return_value = []
        provider = InterhubVoucherProvider(Mock(side_effect=services),
            Mock(return_value=[{'name': 'USD 10', 'count': 0}, {'name': 'USD 20', 'count': 5}]),
            Mock(return_value={'success': True, 'fixed_amount': 10}), 0)
        shared = SupplierCatalog(db, 'unused', provider, offline=offline)
        shared.rows = Mock(return_value=[])
        return shared, provider, cur

    def test_offline_blocks_all_refresh_before_db_and_provider(self):
        # Даже прямой вызов обновления на staging не открывает соединение и не вызывает поставщика.
        shared, provider, _ = self.build(True)
        with self.assertRaises(HTTPException) as caught:
            shared.refresh()
        self.assertEqual(caught.exception.status_code, 403)
        shared.db.connect.assert_not_called()
        provider.get_services.assert_not_called()

    def test_hourly_initializes_new_prices_and_only_reads_existing_stocks(self):
        # Цена существующего номинала ждёт 09:00, новый получает её в первом часовом обходе.
        shared, provider, _ = self.build()
        shared.rows.return_value = [{'service_id': '10', 'nominal_id': '1', 'price_updated_at': datetime.now(timezone.utc)},
                                   {'service_id': '10', 'nominal_id': '2', 'price_updated_at': None}]
        shared.refresh(prices=False)
        provider.calculate.assert_called_once()
        self.assertEqual(provider.calculate.call_args.args[0]['params']['nominal'], 2)
        provider.get_detail.assert_called_once_with(10)

    def test_daily_and_hourly_coalesce_into_single_discovery_and_detail(self):
        # Одновременные слоты не удваивают чтение каталога и остатков.
        shared, provider, cur = self.build()
        now = datetime(2026, 9, 22, 6, tzinfo=timezone.utc)
        cur.fetchall.side_effect = [[('prices', now-timedelta(days=1)), ('stocks', now-timedelta(hours=1))], []]
        shared.refresh(scheduled=True, now=now)
        provider.get_services.assert_called_once()
        provider.get_detail.assert_called_once()
        self.assertEqual(provider.calculate.call_count, 2)

    def test_concurrent_refresh_does_not_contact_provider(self):
        # Блокировка работает до discovery, включая запуск из другого процесса API.
        shared, provider, cur = self.build()
        cur.fetchone.return_value = (False,)
        with self.assertRaises(HTTPException) as caught:
            shared.refresh()
        self.assertEqual(caught.exception.status_code, 409)
        provider.get_services.assert_not_called()
        self.assertIsNone(shared.refresh(scheduled=True))

    def test_empty_malformed_and_duplicate_catalogs_are_rejected(self):
        # Частичный некорректный список не применяется даже для корректной первой услуги.
        for value in [[], None, {}, [services()[0], None], [services()[0], services()[0]],
                      [{**services()[0], 'fields': []}]]:
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                discovery_targets(value)

    def test_disabled_positions_are_discovered_without_being_polled(self):
        # Выключенная услуга остаётся видимой, но calculate/detail для неё не выполняются.
        shared, provider, _ = self.build()
        provider.get_services.side_effect = None
        provider.get_services.return_value = [{**services()[0], 'raw': {'active': False}}]
        shared.refresh()
        provider.get_detail.assert_not_called()
        provider.calculate.assert_not_called()

    def test_availability_explains_disabled_service_and_nominal_separately(self):
        # Причина берётся из явных признаков поставщика, а не из нулевого остатка или ошибки цены.
        payload = services()
        payload[0]['fields'][0]['value_list'][0]['active'] = False
        targets = discovery_targets(payload)
        self.assertEqual(targets[0]['availability_reason'], 'nominal_disabled')
        self.assertEqual(targets[1]['availability_reason'], '')
        payload[0]['raw'] = {'active': 'false'}
        self.assertTrue(all(t['availability_reason'] == 'service_disabled' for t in discovery_targets(payload)))

    def test_multiple_nominal_fields_include_values_after_empty_field(self):
        # В живом каталоге первое поле nominal бывает пустым, а следующие содержат реальные номиналы.
        service = services()[0]
        service['fields'].insert(0, {'name': 'nominal', 'value_list': [], 'raw': {'value_list': []}})
        targets = discovery_targets([service])
        self.assertEqual([t['nominal_id'] for t in targets], [1, 2])

    def test_explicit_empty_service_does_not_block_other_vouchers(self):
        # Пустая услуга проходит обычные два обхода исчезновения, остальные услуги продолжают обновляться.
        empty = {**services()[0], 'service_id': 20, 'fields': [{'name': 'nominal', 'value_list': []}]}
        self.assertEqual(len(discovery_targets([empty, services()[0]])), 2)
        with self.assertRaises(ValueError):
            discovery_targets([empty])
        empty['fields'][0]['raw'] = {'value_list': None}
        with self.assertRaises(ValueError):
            discovery_targets([empty, services()[0]])

    def test_imported_history_is_not_the_live_disappearance_baseline(self):
        # Первое сравнение не принимает накопленные старые записи за предыдущий полный ответ поставщика.
        shared, _, cur = self.build()
        shared.discover()
        query = next(call.args[0] for call in cur.execute.call_args_list
                     if call.args[0].startswith('SELECT service_id, nominal_id'))
        self.assertIn('last_seen_at IS NOT NULL', query)

    def test_large_disappearance_records_error_without_changing_positions(self):
        # Подозрительное сокращение не создаёт массового ложного статуса «недоступен».
        shared, provider, cur = self.build()
        cur.fetchall.return_value = [('10', str(n)) for n in range(1, 30)]
        with self.assertRaises(ValueError):
            shared.discover()
        queries = [c.args[0] for c in cur.execute.call_args_list]
        self.assertFalse(any('UPDATE app.supplier_catalog_current' in q for q in queries))
        self.assertTrue(any('error=EXCLUDED.error' in q for q in queries))

    def test_binding_uses_current_store_without_polling(self):
        # Выбор соответствия не создаёт ещё один кэш и безопасен на staging.
        shared, provider, _ = self.build(True)
        shared.options = Mock(return_value=[{'service_id': 10, 'nominal_id': 1}])
        catalog = VoucherCatalogService(shared.db, shared.dsn, {'interhub': provider}, shared)
        self.assertEqual(catalog.options('interhub')[0]['nominal_id'], 1)
        provider.get_services.assert_not_called()

    def test_staging_transport_blocks_stock_price_and_payment_calls(self):
        # Последний защитный слой останавливает сеть независимо от HTTP-обработчика.
        transport = build_interhub_service(HTTPException=HTTPException, interhub_api_url='https://example.invalid',
            interhub_token='test', timeout_sec=1, ssl_verify=True, ca_cert_path='', calculate_path='/calculate',
            check_path='/check', deposit_path='/balance', offline=True)
        with patch('domains.interhub_service.urllib.request.urlopen') as network:
            for call in [lambda: transport.get_service_detail(1),
                         lambda: transport.calculate({}), lambda: transport.check({}), lambda: transport.pay({}),
                         lambda: transport.check_status({})]:
                with self.assertRaises(HTTPException) as caught:
                    call()
                self.assertEqual(caught.exception.status_code, 403)
            network.assert_not_called()

    def test_discovery_rejects_provider_error_partial_and_invalid_rows(self):
        # Строгий путь синхронизации не наследует мягкий нормализатор формы покупки.
        from test_interhub_service_unittest import _Response
        transport = build_interhub_service(HTTPException=HTTPException, interhub_api_url='https://example.invalid',
            interhub_token='test', timeout_sec=1, ssl_verify=False, ca_cert_path='', calculate_path='/calculate',
            check_path='/check', deposit_path='/balance')
        service = {'id': 1, 'name': 'Voucher', 'type': 'VOUCHER', 'fields': []}
        for payload in [{'success': False, 'data': [service]}, {'data': [service], 'total': 2},
                        {'data': [service], 'pagination': {'has_more': True}}, {'data': [service, None]},
                        {'data': [service, service]}]:
            with self.subTest(payload=payload), patch('domains.interhub_service.urllib.request.urlopen', return_value=_Response(payload)):
                with self.assertRaises(ValueError):
                    transport.get_catalog()

    def test_staging_transport_allows_live_services_and_balance_through_proxy(self):
        # Проверяем разрешённые GET через тот же proxy; реальные запросы не отправляются.
        from test_interhub_service_unittest import _Response
        transport = build_interhub_service(HTTPException=HTTPException, interhub_api_url='https://example.invalid',
            interhub_token='test', timeout_sec=1, ssl_verify=True, ca_cert_path='', calculate_path='/calculate',
            check_path='/check', deposit_path='/balance', offline=True, proxy_url='http://127.0.0.1:3128')
        opener = Mock()
        opener.open.side_effect = [_Response({'data': [{'id': 7, 'name': 'Current service', 'type': 'VOUCHER'}]}),
                                    _Response({'balance': 123, 'currency': '643', 'over_limit': 5})]
        with patch('domains.interhub_service.urllib.request.build_opener', return_value=opener), \
             patch('domains.interhub_service.urllib.request.urlopen') as direct:
            self.assertEqual(transport.get_services()[0]['service_id'], 7)
            self.assertEqual(transport.get_balance()['balance'], 123)
            self.assertEqual([call.args[0].full_url for call in opener.open.call_args_list],
                             ['https://example.invalid/api/agent/service/list', 'https://example.invalid/balance'])
            self.assertTrue(all(call.args[0].method == 'GET' for call in opener.open.call_args_list))
            direct.assert_not_called()
