"""Проверки порядка выдачи без покупок ваучеров и сетевых обращений."""
from unittest import TestCase
from unittest.mock import Mock

from fastapi import HTTPException
from pydantic import ValidationError

from domains.voucher_catalog_api import VoucherNominalIn, VoucherRoutingIn
from domains.voucher_catalog_service import VoucherCatalogService
from tests import test_voucher_catalog_unittest as fixtures

database = fixtures.database


def routing(revision=4, ids=(20, 10), enabled=(True, False)):
    # Порядок массива — контракт API; явные номера клиент не задаёт.
    return VoucherRoutingIn(revision=revision, offers=[{'offer_id': key, 'enabled': flag} for key, flag in zip(ids, enabled)])


class VoucherRoutingTests(TestCase):
    def test_order_and_enabled_flags_are_saved_together_without_changing_snapshots(self):
        # Настройка выдачи не удаляет связки и не обнуляет цену или остаток отключённого предложения.
        cur = Mock()
        cur.fetchone.return_value = (4,)
        cur.fetchall.return_value = [(10,), (20,)]
        VoucherCatalogService.save_routing(cur, 1, 11, routing())
        writes = [call for call in cur.execute.call_args_list if 'UPDATE app.voucher_catalog_offers' in call.args[0]]
        self.assertEqual([call.args[1] for call in writes], [(1, True, 1, 11, 20), (2, False, 1, 11, 10)])
        for call in writes:
            self.assertNotIn('price=', call.args[0])
            self.assertNotIn('stock_count=', call.args[0])
            self.assertNotIn('active=', call.args[0])
        self.assertIn('fulfillment_revision=fulfillment_revision+1', cur.execute.call_args.args[0])

    def test_stale_revision_cannot_overwrite_a_newer_order(self):
        # Даже при неизменном составе поставщиков устаревшая карточка не перезапишет свежий порядок.
        cur = Mock()
        cur.fetchone.return_value = (5,)
        with self.assertRaises(HTTPException) as raised:
            VoucherCatalogService.save_routing(cur, 1, 11, routing())
        self.assertEqual(raised.exception.status_code, 409)
        self.assertFalse(any('UPDATE' in call.args[0] for call in cur.execute.call_args_list))

    def test_foreign_missing_and_duplicate_offer_ids_are_rejected_before_writes(self):
        # Полный набор должен совпасть с активными связками именно этого собственного номинала.
        for ids in [(10, 99), (10,), (10, 10)]:
            with self.subTest(ids=ids):
                cur = Mock()
                cur.fetchone.return_value = (4,)
                cur.fetchall.return_value = [(10,), (20,)]
                with self.assertRaises(HTTPException) as raised:
                    VoucherCatalogService.save_routing(cur, 1, 11, routing(ids=ids))
                self.assertEqual(raised.exception.status_code, 409)
                self.assertFalse(any('UPDATE' in call.args[0] for call in cur.execute.call_args_list))

    def test_missing_nominal_and_empty_new_nominal(self):
        # Пустой порядок разрешён для номинала без связок, но чужой ID не допускается.
        cur = Mock()
        cur.fetchone.return_value = None
        with self.assertRaises(HTTPException) as raised:
            VoucherCatalogService.save_routing(cur, 1, 11, routing())
        self.assertEqual(raised.exception.status_code, 404)
        cur.fetchone.return_value = (0,)
        cur.fetchall.return_value = []
        VoucherCatalogService.save_routing(cur, 1, 11, routing(revision=0, ids=(), enabled=()))
        self.assertIn('UPDATE app.voucher_catalog_nominals', cur.execute.call_args.args[0])

    def test_save_uses_parent_lock_and_never_reads_provider_for_routing(self):
        # Имя и приоритеты сохраняются одной транзакцией под общей блокировкой услуги.
        db, conn, cur = database()
        cur.fetchone.side_effect = [(1,), (11,), (4,)]
        cur.fetchall.return_value = [(10,), (20,)]
        provider = Mock()
        service = VoucherCatalogService(db, 'unused', {'interhub': provider})
        service.save_item(None, 'admin', item_id=1, nominals=[VoucherNominalIn(name='1000 TRY', catalog_nominal_id=11, routing=routing())])
        self.assertIn('FOR UPDATE', cur.execute.call_args_list[0].args[0])
        conn.commit.assert_called_once()
        provider.targets.assert_not_called()
        provider.price.assert_not_called()
        provider.stocks.assert_not_called()

    def test_conflict_does_not_commit_renaming_or_partial_routing(self):
        # Отказ проверки версии откатывает также предшествующее изменение имени номинала.
        db, conn, cur = database()
        cur.fetchone.side_effect = [(1,), (11,), (5,)]
        service = VoucherCatalogService(db, 'unused', {})
        with self.assertRaises(HTTPException):
            service.save_item(None, 'admin', item_id=1, nominals=[VoucherNominalIn(name='New', catalog_nominal_id=11, routing=routing())])
        conn.commit.assert_not_called()
        self.assertIs(db.connect.return_value.__exit__.call_args.args[0], HTTPException)

    def test_duplicate_routing_and_routing_for_new_nominal_are_invalid(self):
        # Некорректную структуру отвергаем ещё до получения внешних цен.
        db, _, _ = database()
        service = VoucherCatalogService(db, 'unused', {})
        for nominal_id, value in [(None, routing()), (11, routing(ids=(10, 10)))]:
            with self.assertRaises(HTTPException) as raised:
                service.prepare_nominals([VoucherNominalIn(name='1000 TRY', catalog_nominal_id=nominal_id, routing=value)])
            self.assertEqual(raised.exception.status_code, 422)
        db.connect.assert_not_called()

    def test_unlink_invalidates_open_routing_card(self):
        # Отвязка блокирует того же родителя и увеличивает версию состава поставщиков.
        db, conn, cur = database()
        cur.fetchone.side_effect = [(1,), (11,)]
        VoucherCatalogService(db, 'unused', {}).unlink(1, 20)
        self.assertIn('FOR UPDATE', cur.execute.call_args_list[0].args[0])
        self.assertIn('fulfillment_revision=fulfillment_revision+1', cur.execute.call_args.args[0])
        self.assertEqual(cur.execute.call_args.args[1], (11,))
        conn.commit.assert_called_once()

    def test_enabled_requires_a_real_boolean(self):
        # Строка false не должна незаметно стать включённым переключателем.
        with self.assertRaises(ValidationError):
            VoucherRoutingIn(revision=0, offers=[{'offer_id': 1, 'enabled': 'false'}])


class VoucherRoutingApiTests(TestCase):
    def setUp(self):
        # Переиспользуем изолированное приложение каталога без глобального lifespan.
        fixtures.VoucherCatalogApiTests.setUp(self)

    def test_routing_is_passed_to_atomic_nominal_save_and_protected_by_permissions(self):
        # Права совпадают с редактором каталога; отдельного обходного endpoint нет.
        payload = {'nominals': [{'name': '1000 TRY', 'catalog_nominal_id': 11, 'routing': routing().model_dump()}]}
        response = self.client.post('/voucher-catalog/items/1/nominals', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.save_item.call_args.kwargs['nominals'][0].routing, routing())
        self.user.role = 'operator'
        self.assertEqual(self.client.post('/voucher-catalog/items/1/nominals', json=payload).status_code, 403)
