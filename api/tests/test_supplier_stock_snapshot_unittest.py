"""Контракт чтения остатков не выдаёт секреты и не выполняет внешний опрос."""
import unittest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from domains.supplier_stock_snapshot import stock_item, mount_supplier_stock_snapshot


class SnapshotTests(unittest.TestCase):
    def test_isolated_error_requires_a_successful_peer(self):
        # Полностью непонятный ответ услуги не обнуляет все её карточки.
        row=('1','2','active',5,None,'failed',[{'name':'USD 5','count':7}],True)
        self.assertEqual(stock_item(row)['error_scope'],'item')
        self.assertEqual(stock_item((*row[:-1],False))['error_scope'],'common')
        self.assertNotIn('response',stock_item(row))

    def test_machine_auth_and_filtered_payload(self):
        # Без отдельного секрета маршрут закрыт, даже если приложение доступно пользователю.
        db=MagicMock(); cur=db.connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value=[('1','2','active',0,None,'',{},True)]
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
