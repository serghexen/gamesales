"""Контракт чтения остатков не выдаёт секреты и не выполняет внешний опрос."""
import unittest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from domains.supplier_stock_snapshot import stock_item, mount_supplier_stock_snapshot


class SnapshotTests(unittest.TestCase):
    def test_isolated_error_requires_a_successful_peer(self):
        # Полностью непонятный ответ услуги не обнуляет все её карточки.
        row=('1','2','active',5,None,'failed',[{'name':'USD 5','count':7}],True,
             '1732.40','RUB','2026-10-05T08:00:00Z','2026-10-06T08:00:00Z','private error')
        self.assertEqual(stock_item(row)['error_scope'],'item')
        self.assertEqual(stock_item((*row[:7],False,*row[8:]))['error_scope'],'common')
        self.assertNotIn('response',stock_item(row))

    def test_machine_auth_and_filtered_payload(self):
        # Без отдельного секрета маршрут закрыт, даже если приложение доступно пользователю.
        db=MagicMock(); cur=db.connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value=[('1','2','active',0,None,'',{},True,
                                    '1732.40','RUB','2026-10-05T08:00:00Z','2026-10-06T08:00:00Z','private error')]
        cur.fetchone.return_value=(None,'')
        app=FastAPI();mount_supplier_stock_snapshot(app,db=db,dsn='test')
        client=TestClient(app)
        with patch.dict('os.environ',{'SUPPLIER_STOCK_SNAPSHOT_TOKEN':'test-secret'*4}):
            self.assertEqual(client.get('/internal/supplier-stock/interhub').status_code,403)
            db.connect.assert_not_called()
            response=client.get('/internal/supplier-stock/interhub',headers={'X-Supplier-Stock-Token':'test-secret'*4})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['items'][0]['stock_count'],0)
        self.assertNotIn('test-secret'*4,response.text)
        self.assertFalse(response.json()['catalog_error'])

    def test_price_keeps_success_time_when_later_attempt_failed(self):
        # Ошибка сегодняшней попытки не меняет дату вчерашней успешной цены.
        item=stock_item(('1','2','active',5,None,'',{},True,
                         '1732.40','RUB','2026-10-05T08:00:00Z','2026-10-06T08:00:00Z','private error'))
        self.assertEqual(item['price'],'1732.40')
        self.assertEqual(item['price_updated_at'],'2026-10-05T08:00:00Z')
        self.assertEqual(item['price_checked_at'],'2026-10-06T08:00:00Z')
        self.assertIs(item['price_error'],True)
        self.assertNotIn('private error',str(item))

    def test_missing_price_stays_unknown(self):
        # Отсутствующая цена не превращается в ноль и не меняет контракт наличия.
        item=stock_item(('1','2','active',5,None,'',{},True,None,'RUB',None,None,''))
        self.assertIsNone(item['price'])
        self.assertIsNone(item['price_updated_at'])
        self.assertEqual(item['stock_count'],5)
