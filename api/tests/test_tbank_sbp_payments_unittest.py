"""Контрактные проверки независимых QR-платежей СБП в CRM."""

from __future__ import annotations

import base64
import hashlib
import unittest
from datetime import datetime, timezone
from inspect import getsource
from unittest.mock import MagicMock, patch

from fastapi import FastAPI

from domains.tbank_sbp_payments import (
    SbpPaymentCreateIn,
    TBankClient,
    TBankSettings,
    _ssl_context,
    make_token,
    mount_tbank_sbp_payment_routes,
    notification_token_is_valid,
    payment_list_where,
    payment_receipt,
    provider_state,
    qr_data_url,
    should_apply_provider_state,
)


class TBankSbpPaymentsTests(unittest.TestCase):
    def test_token_uses_sorted_root_scalars_and_ignores_receipt(self) -> None:
        payload = {
            "TerminalKey": "Terminal",
            "Amount": 1000,
            "OrderId": "crm_1",
            "Receipt": {"ignored": "nested"},
        }
        expected = "1000" + "crm_1" + "password" + "Terminal"

        self.assertEqual(make_token(payload, "password"), hashlib.sha256(expected.encode()).hexdigest())

    def test_notification_signature_handles_boolean_values(self) -> None:
        payload = {"TerminalKey": "Terminal", "Success": True, "Status": "CONFIRMED"}
        payload["Token"] = make_token(payload, "password")

        self.assertTrue(notification_token_is_valid(payload, "password"))
        self.assertFalse(notification_token_is_valid({**payload, "Status": "REJECTED"}, "password"))

    def test_qr_is_safe_image_data_url(self) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'
        result = qr_data_url(svg)

        self.assertTrue(result.startswith("data:image/svg+xml;base64,"))
        self.assertEqual(base64.b64decode(result.split(",", 1)[1]).decode(), svg)
        with self.assertRaises(RuntimeError):
            qr_data_url('<svg xmlns="http://www.w3.org/2000/svg"><foreignObject /></svg>')

    def test_receipt_uses_operator_description_as_ffd_12_service(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "TBANK_RECEIPT_EMAIL": "Asat@Asatmail.com",
                "TBANK_RECEIPT_TAXATION": "usn_income_outcome",
                "TBANK_RECEIPT_TAX": "none",
            },
        ):
            receipt = payment_receipt(amount=199_000, description="A Way Out для PS5")

        self.assertEqual(receipt["FfdVersion"], "1.2")
        self.assertEqual(receipt["Email"], "asat@asatmail.com")
        self.assertEqual(receipt["Taxation"], "usn_income_outcome")
        self.assertEqual(receipt["Items"][0]["Name"], "A Way Out для PS5")
        self.assertEqual(receipt["Items"][0]["PaymentObject"], "service")
        self.assertEqual(receipt["Items"][0]["PaymentMethod"], "full_payment")
        self.assertEqual(receipt["Items"][0]["Tax"], "none")

    def test_init_sends_description_but_never_internal_buyer(self) -> None:
        captured = []
        client = TBankClient(TBankSettings("https://example.test/v2", "Terminal", "secret", "n", "s", "f", 3))
        client.call = lambda method, payload: captured.append((method, payload)) or {"Success": True}

        client.init(
            order_id="crm_1",
            amount=199_000,
            description="A Way Out для PS5",
            expires_at=datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc),
            receipt={"Items": [{"Name": "A Way Out для PS5"}]},
        )

        self.assertEqual(captured[0][0], "Init")
        self.assertEqual(captured[0][1]["Description"], "A Way Out для PS5")
        self.assertNotIn("buyer", {key.lower(): value for key, value in captured[0][1].items()})

    def test_terminal_states_are_monotonic(self) -> None:
        self.assertEqual(provider_state("CONFIRMED"), "confirmed")
        self.assertEqual(provider_state("DEADLINE_EXPIRED"), "expired")
        self.assertFalse(should_apply_provider_state("confirmed", "pending"))
        self.assertFalse(should_apply_provider_state("rejected", "pending"))
        self.assertTrue(should_apply_provider_state("pending", "confirmed"))

    def test_routes_are_authenticated_but_not_role_restricted(self) -> None:
        app = FastAPI()
        mount_tbank_sbp_payment_routes(
            app,
            database_url="",
            psycopg=None,
            get_current_user=lambda: None,
            get_user_id=lambda *_args: 1,
        )
        paths = {route.path for route in app.routes}
        fields = SbpPaymentCreateIn.model_fields

        self.assertIn("/payments/tbank/sbp", paths)
        self.assertIn("/payments/tbank/sbp/mark-seen", paths)
        self.assertIn("/payments/tbank/notifications", paths)
        self.assertIn("buyer", fields)
        self.assertNotIn("created_by_user_id", fields)

    def test_database_flow_has_concurrency_and_idempotency_guards(self) -> None:
        source = getsource(__import__("domains.tbank_sbp_payments", fromlist=["_"]))

        self.assertIn("FOR UPDATE SKIP LOCKED", source)
        self.assertIn("ON CONFLICT (event_fingerprint) DO NOTHING", source)
        self.assertIn("created_by_user_id", source)
        self.assertIn("NULLIF(BTRIM(creator.name), '')", source)
        self.assertIn("LEFT JOIN app.users creator", source)
        self.assertIn("WHERE order_id=%s AND terminal_key=%s", source)

    def test_history_filters_are_parameterized_for_large_lists(self) -> None:
        where_sql, params = payment_list_where(
            mine=True,
            user_id=17,
            state="confirmed",
            search="FIFA 27",
        )

        self.assertIn("p.created_by_user_id=%s", where_sql)
        self.assertIn("p.state=%s", where_sql)
        self.assertIn("p.description ILIKE %s", where_sql)
        self.assertNotIn("FIFA 27", where_sql)
        self.assertEqual(params, (17, "confirmed", "%FIFA 27%", "%FIFA 27%", "%FIFA 27%", "%FIFA 27%"))
        with self.assertRaises(ValueError):
            payment_list_where(mine=False, user_id=17, state="unknown-state", search="")

    def test_custom_ca_bundle_extends_normal_trust_store(self) -> None:
        expected = MagicMock()
        with patch.dict("os.environ", {"TBANK_CA_BUNDLE": "/etc/ssl/certs/ca-certificates.crt"}), patch(
            "domains.tbank_sbp_payments.ssl.create_default_context", return_value=expected
        ):
            actual = _ssl_context()

        self.assertIs(actual, expected)
        expected.load_verify_locations.assert_called_once_with(cafile="/etc/ssl/certs/ca-certificates.crt")


if __name__ == "__main__":
    unittest.main()
