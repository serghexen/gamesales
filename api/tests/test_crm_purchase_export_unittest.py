import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from domains.crm_purchase_export import iter_crm_purchase_export


class CrmPurchaseExportTests(unittest.TestCase):
    def test_reads_every_batch_once_and_preserves_purchase_fields(self):
        # Одно чтение должно сохранить все строки архива, включая старые покупки без сделки.
        created_at = datetime(2026, 8, 1, tzinfo=timezone.utc)
        first = ("crm-1", 7, "Steam", "15", "15 USD", Decimal("12.50"), "CODE-1", created_at,
                 42, "000123", "buyer", "TR", "operator")
        last = ("crm-501", 8, "Apple", "16", "10 USD", Decimal("10.00"), "CODE-2", created_at,
                None, "", "", "", "owner")
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchmany.side_effect = [[first] * 500, [last], []]
        conn = MagicMock()
        conn.__enter__.return_value = conn
        conn.cursor.return_value = cursor
        driver = SimpleNamespace(connect=MagicMock(return_value=conn))

        rows = list(iter_crm_purchase_export(
            psycopg=driver, dsn="test", date_from=date(2026, 8, 1), date_to=date(2026, 8, 31),
        ))

        self.assertEqual(len(rows), 501)
        self.assertEqual(rows[0], {
            "agent_transaction_id": "crm-1", "service_id": 7, "service_title": "Steam",
            "nominal": "15", "nominal_title": "15 USD", "price": Decimal("12.50"),
            "gift_code": "CODE-1", "created_at": created_at, "deal_id": 42,
            "order_number": "000123", "customer_nickname": "buyer", "region_code": "TR", "created_by": "operator",
        })
        self.assertEqual(rows[-1]["agent_transaction_id"], "crm-501")
        self.assertIsNone(rows[-1]["deal_id"])
        cursor.execute.assert_called_once()
        sql, params = cursor.execute.call_args.args
        self.assertEqual(params, [date(2026, 8, 1), date(2026, 8, 31)])
        self.assertIn("t.state='paid'", sql)
        self.assertIn("created_at >= (%s::date::timestamp AT TIME ZONE 'Europe/Moscow')", sql)
        self.assertIn("created_at < ((%s::date + 1)::timestamp AT TIME ZONE 'Europe/Moscow')", sql)
        self.assertNotIn("COUNT(*)", sql)
        self.assertNotIn("OFFSET", sql)
        self.assertNotIn("deal_id IS NOT NULL", sql)
        conn.__exit__.assert_called_once()

    def test_open_period_has_no_artificial_date_limit(self):
        # Пустые поля дат означают весь архив, без ограничения количества покупок.
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchmany.return_value = []
        conn = MagicMock()
        conn.__enter__.return_value = conn
        conn.cursor.return_value = cursor
        rows = list(iter_crm_purchase_export(
            psycopg=SimpleNamespace(connect=lambda _dsn: conn), dsn="test", date_from=None, date_to=None,
        ))
        self.assertEqual(rows, [])
        self.assertEqual(cursor.execute.call_args.args[1], [])
        self.assertNotIn("t.created_at >=", cursor.execute.call_args.args[0])
        self.assertNotIn("t.created_at <", cursor.execute.call_args.args[0])
