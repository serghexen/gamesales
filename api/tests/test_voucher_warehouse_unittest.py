"""Склад изолирован от селлера: права, шифрование, одна цена и безопасные связки."""
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from psycopg.errors import RestrictViolation
from domains.voucher_warehouse_api import mount_voucher_warehouse_routes, WarehousePriceIn
from domains.voucher_warehouse_service import VoucherWarehouseService
from domains.voucher_catalog_api import VoucherBindingIn, VoucherNominalIn
from domains.voucher_catalog_service import VoucherCatalogService
from tests.test_voucher_catalog_unittest import database


def columns(names):
    # Эмулируем имена колонок psycopg без настоящей БД.
    return [SimpleNamespace(name=name) for name in names]


class WarehouseApiTests(TestCase):
    def setUp(self):
        # HTTP-проверки не требуют приложения, воркеров или доступа к реальным ключам.
        self.service = Mock()
        self.service.can_view.return_value = True
        self.user = SimpleNamespace(role='owner', username='test')
        app = FastAPI()
        mount_voucher_warehouse_routes(app, service=self.service, get_current_user=lambda: self.user)
        self.client = TestClient(app)

    def test_summary_visible_to_admin_but_keys_and_changes_owner_only(self):
        self.user.role = 'admin'
        self.service.list_positions.return_value = []
        self.assertEqual(self.client.get('/voucher-warehouse').json(), {'items': [], 'can_manage': False})
        for method, path, body in [
            ('get', '/keys', None), ('post', '/keys', {'codes': ['test']}),
            ('post', '/keys/1/reveal', {}), ('delete', '/keys/1', None),
            ('delete', '/keys', None), ('put', '/price', {'price': 10}),
        ]:
            response = self.client.request(method, '/voucher-warehouse/nominals/1' + path, json=body)
            self.assertEqual(response.status_code, 403)
        self.service.add_keys.assert_not_called()
        self.service.set_price.assert_not_called()

    def test_disabled_section_denies_even_owner(self):
        self.service.can_view.return_value = False
        self.assertEqual(self.client.get('/voucher-warehouse').status_code, 403)
        self.assertEqual(self.client.get('/voucher-warehouse/nominals/1/keys').status_code, 403)
        self.service.list_keys.assert_not_called()

    def test_one_price_for_position_and_upload_has_no_batch_price(self):
        self.service.set_price.return_value = {'ok': True, 'price_updated_at': '2026-09-22T09:00:00Z'}
        response = self.client.put('/voucher-warehouse/nominals/11/price', json={'price': '1500.123456', 'expected_updated_at': None})
        self.assertEqual(response.status_code, 200)
        self.service.set_price.assert_called_once_with(11, Decimal('1500.123456'), 'test', expected_updated_at=None)
        self.service.add_keys.return_value = {'ok': True, 'added': 2, 'duplicates': 0}
        response = self.client.post('/voucher-warehouse/nominals/11/keys', json={'codes': ['A', 'B']})
        self.assertEqual(response.status_code, 200)
        self.service.add_keys.assert_called_once_with(11, ['A', 'B'], None, 'test')
        self.assertEqual(self.service.set_price.call_count, 1)

    def test_zero_unset_and_invalid_prices(self):
        self.assertEqual(WarehousePriceIn(price=0, expected_updated_at=None).price, 0)
        self.assertIsNone(WarehousePriceIn(price=None, expected_updated_at=None).price)
        for value in [-1, 'NaN', 'Infinity', '100000000000000', '0.1234567']:
            with self.assertRaises(ValidationError):
                WarehousePriceIn(price=value, expected_updated_at=None)
        self.assertEqual(self.client.put('/voucher-warehouse/nominals/1/price', json={'price': 10}).status_code, 422)
        self.assertEqual(self.client.post('/voucher-warehouse/nominals/1/keys', json={'codes': []}).status_code, 422)
        self.assertEqual(self.client.post('/voucher-warehouse/nominals/1/keys', json={'codes': ['a'] * 1001}).status_code, 422)
        self.assertEqual(self.client.get('/voucher-warehouse/nominals/1/keys?page_size=10000').status_code, 422)

    def test_bulk_delete_requires_the_displayed_snapshot_boundary(self):
        # Старый клиент без границы не должен удалить новые поступления вслепую.
        self.service.delete_keys.return_value = {'ok': True, 'removed': 2}
        for suffix in ['', '?through_key_id=0', '?through_key_id=-1']:
            self.assertEqual(self.client.delete('/voucher-warehouse/nominals/11/keys' + suffix).status_code, 422)
        self.service.delete_keys.assert_not_called()
        self.assertEqual(self.client.delete('/voucher-warehouse/nominals/11/keys?through_key_id=5').status_code, 200)
        self.service.delete_keys.assert_called_once_with(11, through_key_id=5)


class WarehouseServiceTests(TestCase):
    @patch.dict('os.environ', {'MARKETPLACE_KEY_POOL_SECRET': 'test-only-secret-longer-than-32-characters'})
    def test_encrypts_deduplicates_and_does_not_touch_seller_or_price(self):
        db, conn, cur = database()
        cur.fetchone.side_effect = [(1,), (11,), (1,), None]
        result = VoucherWarehouseService(db, 'unused').add_keys(11, [' TEST-A ', 'TEST-A', 'TEST-B'], None, 'owner')
        self.assertEqual(result, {'ok': True, 'added': 1, 'duplicates': 2})
        inserts = [call for call in cur.execute.call_args_list if 'INSERT' in call.args[0]]
        self.assertEqual(len(inserts), 2)
        for call in inserts:
            query, params = call.args
            self.assertIn('pgp_sym_encrypt', query)
            self.assertIn('ON CONFLICT(code_hash) DO NOTHING', query)
            self.assertNotIn('marketplace_manual', query)
            self.assertNotIn('price', query)
            self.assertEqual(params[0], 11)
            self.assertEqual(len(params[3]), 64)
            self.assertEqual(params[4], params[1][-4:])
        conn.commit.assert_called_once()

    def test_invalid_or_expired_input_writes_nothing(self):
        # Один испорченный ключ отклоняет весь пакет до подключения к БД.
        db, _, _ = database()
        service = VoucherWarehouseService(db, 'unused')
        for codes, expires in [([''], None), (['A' * 1025], None), (['A'], date(2000, 1, 1)),
                               (['VALID', 'A\x00B'], None), (['A\nB'], None), (['A\tB'], None), (['A\x7fB'], None)]:
            with self.assertRaises(HTTPException) as raised:
                service.add_keys(1, codes, expires, 'owner')
            self.assertEqual(raised.exception.status_code, 422)
        db.connect.assert_not_called()

    @patch.dict('os.environ', {'MARKETPLACE_KEY_POOL_SECRET': ''})
    def test_missing_secret_never_stores_plaintext(self):
        db, _, _ = database()
        with self.assertRaises(HTTPException) as raised:
            VoucherWarehouseService(db, 'unused').add_keys(1, ['A'], None, 'owner')
        self.assertEqual(raised.exception.status_code, 503)
        db.connect.assert_not_called()

    def test_price_upsert_is_for_whole_nominal_and_locks_parent_first(self):
        # Первое сохранение пустого пула передаёт пустую версию и получает новую.
        db, conn, cur = database()
        timestamp = datetime(2026, 9, 22, tzinfo=timezone.utc)
        cur.fetchone.side_effect = [(3,), (11,), None, (timestamp,)]
        result = VoucherWarehouseService(db, 'unused').set_price(11, Decimal('42.123'), 'owner', expected_updated_at=None)
        self.assertIn('FOR UPDATE OF i', cur.execute.call_args_list[0].args[0])
        query, params = cur.execute.call_args.args
        self.assertIn('ON CONFLICT(catalog_nominal_id)', query)
        self.assertEqual(params, (11, Decimal('42.123'), 'owner'))
        self.assertEqual(result['price_updated_at'], timestamp)
        conn.commit.assert_called_once()

    def test_stale_price_version_cannot_overwrite_another_window(self):
        # И заполненная, и очищенная цена защищены одной версией записи.
        timestamp = datetime(2026, 9, 22, tzinfo=timezone.utc)
        for requested_price in [None, Decimal('0'), Decimal('123')]:
            db, conn, cur = database()
            cur.fetchone.side_effect = [(1,), (11,), (timestamp,)]
            with self.assertRaises(HTTPException) as raised:
                VoucherWarehouseService(db, 'unused').set_price(11, requested_price, 'owner', expected_updated_at=None)
            self.assertEqual(raised.exception.status_code, 409)
            conn.commit.assert_not_called()
            self.assertFalse(any('INSERT' in call.args[0] for call in cur.execute.call_args_list))

    def test_current_price_version_allows_explicit_replacement(self):
        # Повторное сохранение после просмотра новой цены использует её точную версию.
        db, conn, cur = database()
        timestamp = datetime(2026, 9, 22, tzinfo=timezone.utc)
        newer = datetime(2026, 9, 22, 1, tzinfo=timezone.utc)
        cur.fetchone.side_effect = [(1,), (11,), (timestamp,), (newer,)]
        result = VoucherWarehouseService(db, 'unused').set_price(11, None, 'owner', expected_updated_at=timestamp)
        self.assertEqual(result['price_updated_at'], newer)
        conn.commit.assert_called_once()

    def test_only_free_keys_can_be_deleted_and_scope_is_checked(self):
        db, conn, cur = database()
        cur.fetchone.side_effect = [(1,), (11,)]
        cur.fetchall.return_value = []
        with self.assertRaises(HTTPException) as raised:
            VoucherWarehouseService(db, 'unused').delete_keys(11, 99)
        self.assertEqual(raised.exception.status_code, 409)
        query, params = cur.execute.call_args.args
        self.assertIn("status='free'", query)
        self.assertIn('catalog_nominal_id=%s', query)
        self.assertEqual(params, (11, 99))
        conn.commit.assert_not_called()

    def test_list_keys_masks_codes_and_clamps_page(self):
        # Проверка пула SELECT 1 не должна мешать выбору изоляции для снимка склада.
        db, conn, cur = database()
        def execute(query, params=None):
            # PostgreSQL разрешает SET TRANSACTION только после завершения транзакции проверки пула.
            if query.startswith('SET TRANSACTION'):
                conn.rollback.assert_called_once()
        cur.execute.side_effect = execute
        cur.description = columns(['catalog_nominal_id', 'total', 'through_key_id'])
        cur.fetchall.side_effect = [[(11, 1, 5)], []]
        result = VoucherWarehouseService(db, 'unused').list_keys(11, 100, 20)
        self.assertIn('REPEATABLE READ, READ ONLY', cur.execute.call_args_list[0].args[0])
        query, params = cur.execute.call_args.args
        self.assertNotIn('pgp_sym_decrypt', query)
        self.assertNotIn('code_ciphertext', query)
        self.assertIn('masked_code', query)
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['through_key_id'], 5)
        self.assertEqual(params, (11, 20, 0))

    def test_bulk_delete_is_limited_to_snapshot_and_currently_free_keys(self):
        # Повторная очистка допустима, но ни новые, ни уже занятые ключи в неё не входят.
        db, conn, cur = database()
        cur.fetchone.side_effect = [(1,), (11,)]
        cur.fetchall.return_value = []
        result = VoucherWarehouseService(db, 'unused').delete_keys(11, through_key_id=5)
        query, params = cur.execute.call_args.args
        self.assertIn("status='free'", query)
        self.assertIn('key_id<=%s', query)
        self.assertEqual(params, (11, 5))
        self.assertEqual(result['removed'], 0)
        conn.commit.assert_called_once()

    @patch.dict('os.environ', {'MARKETPLACE_KEY_POOL_SECRET': 'test-only-secret-longer-than-32-characters'})
    def test_reveal_cannot_read_a_key_of_another_nominal(self):
        db, _, cur = database()
        cur.fetchone.return_value = None
        with self.assertRaises(HTTPException) as raised:
            VoucherWarehouseService(db, 'unused').reveal(11, 99)
        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(cur.execute.call_args.args[1][-2:], (11, 99))


class WarehouseCatalogTests(TestCase):
    def test_preview_reads_stock_of_requested_sku_without_key_data(self):
        # Предпросмотр читает тот же остаток, что склад, даже пока связки ещё нет.
        db, _, cur = database()
        cur.fetchone.return_value = (11, 'HT0000011', 'USD 30', Decimal('100'), 3)
        result = VoucherCatalogService(db, 'unused', {}).warehouse_snapshot(11)
        self.assertEqual(result, dict(catalog_nominal_id=11, sku='HT0000011', name='USD 30', price=100, free_count=3))
        self.assertEqual(cur.execute.call_args.args[1], (11,))
        cur.fetchone.return_value = None
        with self.assertRaises(HTTPException) as raised:
            VoucherCatalogService(db, 'unused', {}).warehouse_snapshot(99)
        self.assertEqual(raised.exception.status_code, 404)

    def test_link_same_sku_without_external_calls_or_snapshots(self):
        db, conn, cur = database()
        cur.fetchone.side_effect = [(1,), (11,), (5,)]
        provider = Mock()
        service = VoucherCatalogService(db, 'unused', {'interhub': provider})
        service.write_snapshot = Mock()
        service.save_item(None, 'owner', item_id=1, nominals=[VoucherNominalIn(name='USD 30', catalog_nominal_id=11,
            binding=VoucherBindingIn(supplier_code='warehouse', service_id='1', nominal_id='11'))])
        provider.targets.assert_not_called()
        service.write_snapshot.assert_not_called()
        conn.commit.assert_called_once()
        self.assertTrue(any('fulfillment_revision=fulfillment_revision+1' in call.args[0] for call in cur.execute.call_args_list))

    def test_rejects_new_nominal_and_cross_sku_or_service_links(self):
        for own, item, link in [(None, '1', '11'), (11, '1', '12'), (11, '2', '11')]:
            db, conn, cur = database()
            cur.fetchone.side_effect = [(1,), (11,)]
            with self.assertRaises(HTTPException) as raised:
                VoucherCatalogService(db, 'unused', {}).save_item(None, 'owner', item_id=1, nominals=[
                    VoucherNominalIn(name='USD 30', catalog_nominal_id=own,
                        binding=VoucherBindingIn(supplier_code='warehouse', service_id=item, nominal_id=link))])
            self.assertEqual(raised.exception.status_code, 422)
            conn.commit.assert_not_called()

    def test_catalog_uses_live_stock_and_pool_price_even_if_old_snapshot_differs(self):
        db, _, cur = database()
        offer = dict(offer_id=1, item_id=1, catalog_nominal_id=11, supplier_code='warehouse', price=1, stock_count=999,
                     warehouse_price=Decimal('125'), warehouse_stock=2, warehouse_price_at=None,
                     warehouse_service='New service name', warehouse_nominal='USD 30')
        cur.description = columns(offer.keys())
        cur.fetchall.side_effect = [[(1, 'Apple')], [(11, 1, 'USD 30', 0, 'HT0000001')], [tuple(offer.values())], [], [('warehouse', 'Склад')]]
        result = VoucherCatalogService(db, 'unused', {}).list_items()
        actual = result['items'][0]['nominals'][0]['offers'][0]
        self.assertEqual(actual['price'], 125)
        self.assertEqual(actual['stock_count'], 2)
        self.assertEqual(actual['service_title'], 'New service name')
        self.assertFalse(any(name.startswith('warehouse_') for name in actual))
        self.assertEqual(result['suppliers'], [{'code': 'warehouse', 'name': 'Склад'}])

    def test_keys_restrict_deletion_with_readable_conflict_and_no_commit(self):
        # PostgreSQL может вернуть отдельный код RESTRICT: пользователю нужен 409, а не 500.
        for nominal in [True, False]:
            db, conn, cur = database()
            cur.fetchone.side_effect = [(1,), (11,)]
            def execute(query, params):
                # Эмулируем запрет внешнего ключа только после попытки удалить номинал.
                if 'DELETE FROM app.voucher_catalog_nominals' in query:
                    raise RestrictViolation('warehouse keys exist')
            cur.execute.side_effect = execute
            service = VoucherCatalogService(db, 'unused', {})
            with self.assertRaises(HTTPException) as raised:
                if nominal:
                    service.delete_nominal(1, 11)
                else:
                    service.delete_item(1)
            self.assertEqual(raised.exception.status_code, 409)
            self.assertIn('складе', raised.exception.detail)
            conn.commit.assert_not_called()

    def test_scheduler_skips_warehouse(self):
        db, _, cur = database()
        cur.fetchall.return_value = [(1, 'warehouse', '1', '11')]
        provider = Mock()
        service = VoucherCatalogService(db, 'unused', {'interhub': provider})
        for job in ['prices', 'stocks']:
            self.assertEqual(service.refresh(job), 0)
        provider.targets.assert_not_called()
        provider.price.assert_not_called()
        provider.stocks.assert_not_called()
