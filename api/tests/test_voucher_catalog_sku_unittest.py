"""SKU принадлежит номиналу, возвращается читателям и не задаётся клиентом."""
from unittest import TestCase

from domains.voucher_catalog_api import VoucherNominalIn
from domains.voucher_catalog_service import VoucherCatalogService
from tests import test_voucher_catalog_unittest as fixtures


class VoucherSkuTests(TestCase):
    def test_list_returns_persisted_sku_for_each_nominal(self):
        # Два номинала одной услуги имеют разные постоянные коды независимо от поставщиков.
        db, _, cur = fixtures.database()
        cur.description = []
        cur.fetchall.side_effect = [
            [(1, 'Blizzard — EUR')],
            [(11, 1, 'EUR 20', 0, 'HT0000001'), (15, 1, 'EUR 50', 2, 'HT0000002')],
            [], [], [],
        ]
        result = VoucherCatalogService(db, 'unused', {}).list_items()
        self.assertEqual([row['sku'] for row in result['items'][0]['nominals']], ['HT0000001', 'HT0000002'])

    def test_create_uses_database_default_and_rename_preserves_sku(self):
        # Чужой SKU из запроса не попадает ни в INSERT, ни в UPDATE номинала.
        for nominal_id in [None, 11]:
            with self.subTest(nominal_id=nominal_id):
                db, conn, cur = fixtures.database()
                cur.fetchone.side_effect = [(1,), (11,)]
                payload = VoucherNominalIn.model_validate({
                    'name': 'EUR 20', 'catalog_nominal_id': nominal_id,
                    'sku': 'HT9999999', 'sku_number': 9999999,
                })
                VoucherCatalogService(db, 'unused', {}).save_item(None, 'admin', item_id=1, nominals=[payload])
                query, params = cur.execute.call_args_list[1].args
                self.assertIn('INSERT INTO' if nominal_id is None else 'UPDATE', query)
                self.assertNotIn('sku', query)
                self.assertNotIn('HT9999999', params)
                conn.commit.assert_called_once()
