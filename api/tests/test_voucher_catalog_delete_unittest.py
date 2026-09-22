"""Удаление собственного номинала: область действия, права и атомарность."""
from unittest import TestCase
from types import SimpleNamespace

from fastapi import HTTPException
from psycopg.errors import ForeignKeyViolation

from domains.voucher_catalog_service import VoucherCatalogService
from tests import test_voucher_catalog_unittest as fixtures


class VoucherNominalDeleteTests(TestCase):
    def test_list_tolerates_a_nominal_recreated_between_reads(self):
        # Новый ID, появившийся между чтением номиналов и связок, не должен ломать весь каталог.
        db, _, cur = fixtures.database()
        cur.description = [SimpleNamespace(name=name) for name in ['offer_id', 'item_id', 'catalog_nominal_id', 'supplier_code']]
        cur.fetchall.side_effect = [[(1, 'Service')], [(11, 1, '1000 TRY', 0, 'HT0000001')], [(20, 1, 11, 'interhub'), (21, 1, 12, 'interhub')], [], []]
        result = VoucherCatalogService(db, 'unused', {}).list_items()
        self.assertEqual([offer['offer_id'] for offer in result['items'][0]['offers']], [20])

    def test_deletes_all_links_then_nominal_under_parent_lock(self):
        # Удаляем и активные, и ранее отвязанные предложения только выбранного номинала.
        db, conn, cur = fixtures.database()
        cur.fetchone.side_effect = [(1,), (11,)]
        VoucherCatalogService(db, 'unused', {}).delete_nominal(1, 11)
        calls = cur.execute.call_args_list
        self.assertIn('FOR UPDATE', calls[0].args[0])
        self.assertIn('FOR UPDATE', calls[1].args[0])
        self.assertIn('DELETE FROM app.voucher_catalog_offers', calls[2].args[0])
        self.assertNotIn('AND active', calls[2].args[0])
        self.assertIn('DELETE FROM app.voucher_catalog_nominals', calls[3].args[0])
        self.assertEqual(calls[2].args[1], (1, 11))
        self.assertEqual(calls[3].args[1], (1, 11))
        conn.commit.assert_called_once()

    def test_missing_parent_or_nominal_never_deletes_other_rows(self):
        # Чужой или уже удалённый ID возвращает 404 до первой записи.
        for result in [[None], [(1,), None]]:
            db, conn, cur = fixtures.database()
            cur.fetchone.side_effect = result
            with self.assertRaises(HTTPException) as raised:
                VoucherCatalogService(db, 'unused', {}).delete_nominal(1, 11)
            self.assertEqual(raised.exception.status_code, 404)
            self.assertFalse(any('DELETE' in call.args[0] for call in cur.execute.call_args_list))
            conn.commit.assert_not_called()

    def test_reference_conflict_rolls_back_deleted_offers_and_returns_409(self):
        # Будущая ссылка на номинал должна откатить удаление связок в той же транзакции.
        db, conn, cur = fixtures.database()
        cur.fetchone.side_effect = [(1,), (11,)]
        cur.execute.side_effect = [None, None, None, ForeignKeyViolation('private database detail')]
        with self.assertRaises(HTTPException) as raised:
            VoucherCatalogService(db, 'unused', {}).delete_nominal(1, 11)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertNotIn('private', raised.exception.detail)
        self.assertIs(db.connect.return_value.__exit__.call_args.args[0], ForeignKeyViolation)
        conn.commit.assert_not_called()


class VoucherNominalDeleteApiTests(TestCase):
    def setUp(self):
        # Изолированное приложение проверяет права без запуска фоновых задач.
        fixtures.VoucherCatalogApiTests.setUp(self)

    def test_deletion_is_scoped_and_does_not_call_unlink(self):
        # Удаление номинала и отвязка поставщика остаются разными операциями.
        response = self.client.delete('/voucher-catalog/items/7/nominals/11')
        self.assertEqual(response.status_code, 200)
        self.service.delete_nominal.assert_called_once_with(7, 11)
        self.service.unlink.assert_not_called()

    def test_readonly_user_cannot_delete(self):
        # Разрешённый просмотр не даёт права удалять собственные номиналы.
        self.user.role = 'operator'
        self.assertEqual(self.client.delete('/voucher-catalog/items/7/nominals/11').status_code, 403)
        self.service.delete_nominal.assert_not_called()

    def test_denied_section_cannot_delete(self):
        # Даже администратор без доступа к разделу не может обойти интерфейс прямым запросом.
        self.service.can_view.return_value = False
        self.assertEqual(self.client.delete('/voucher-catalog/items/7/nominals/11').status_code, 403)
        self.service.delete_nominal.assert_not_called()


class VoucherServiceDeleteTests(TestCase):
    def test_deletes_only_selected_service_and_all_its_contents_under_lock(self):
        # Удаляем все связки, включая отвязанные, затем номиналы и саму услугу.
        db, conn, cur = fixtures.database()
        cur.fetchone.return_value = (7,)
        VoucherCatalogService(db, 'unused', {}).delete_item(7)
        calls = cur.execute.call_args_list
        self.assertIn('FOR UPDATE', calls[0].args[0])
        self.assertEqual(len(calls), 4)
        for call, table in zip(calls[1:], ['offers', 'nominals', 'items']):
            self.assertEqual(call.args, (f'DELETE FROM app.voucher_catalog_{table} WHERE item_id=%s', (7,)))
        conn.commit.assert_called_once()

    def test_missing_service_returns_404_without_writes(self):
        # Повторное удаление не должно затронуть соседние услуги.
        db, conn, cur = fixtures.database()
        cur.fetchone.return_value = None
        with self.assertRaises(HTTPException) as raised:
            VoucherCatalogService(db, 'unused', {}).delete_item(7)
        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(cur.execute.call_count, 1)
        conn.commit.assert_not_called()

    def test_conflict_at_any_delete_rolls_back_the_whole_transaction(self):
        # Ссылка на услугу, номинал или предложение защищает весь состав от частичного удаления.
        for successful_calls in [1, 2, 3]:
            with self.subTest(successful_calls=successful_calls):
                db, conn, cur = fixtures.database()
                cur.fetchone.return_value = (7,)
                cur.execute.side_effect = [None] * successful_calls + [ForeignKeyViolation('private detail')]
                with self.assertRaises(HTTPException) as raised:
                    VoucherCatalogService(db, 'unused', {}).delete_item(7)
                self.assertEqual(raised.exception.status_code, 409)
                self.assertNotIn('private', raised.exception.detail)
                self.assertIs(db.connect.return_value.__exit__.call_args.args[0], ForeignKeyViolation)
                conn.commit.assert_not_called()


class VoucherServiceDeleteApiTests(TestCase):
    def setUp(self):
        # Проверяем маршрут без подключения к БД и запуска воркеров.
        fixtures.VoucherCatalogApiTests.setUp(self)

    def test_admin_and_owner_can_delete_service(self):
        # Разрешённое действие передаёт в сервис только выбранный ID.
        for role in ['admin', 'owner']:
            self.user.role = role
            self.service.delete_item.reset_mock()
            response = self.client.delete('/voucher-catalog/items/7')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {'ok': True})
            self.service.delete_item.assert_called_once_with(7)
        self.service.delete_nominal.assert_not_called()
        self.service.unlink.assert_not_called()

    def test_readonly_or_denied_section_cannot_delete(self):
        # Доступ на чтение и скрытый раздел не разрешают прямой запрос удаления.
        for role, allowed in [('operator', True), ('admin', False)]:
            self.user.role = role
            self.service.can_view.return_value = allowed
            self.assertEqual(self.client.delete('/voucher-catalog/items/7').status_code, 403)
        self.service.delete_item.assert_not_called()
