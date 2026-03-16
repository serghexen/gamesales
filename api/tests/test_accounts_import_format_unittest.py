import unittest
from io import BytesIO
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

from openpyxl import Workbook

import app as app_module


class _ScriptedCursor:
    def __init__(self, script):
        self._script = script
        self._current = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, sql, params=None):
        if not self._script:
            raise AssertionError(f"Unexpected SQL without scripted response: {sql}")
        self._current = self._script.pop(0)
        self.rowcount = int(self._current.get("rowcount", 0))

    def fetchone(self):
        if not self._current:
            return None
        return self._current.get("one")

    def fetchall(self):
        if not self._current:
            return []
        return self._current.get("all", [])


class _ScriptedConnCtx:
    def __init__(self, script):
        self._script = list(script)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def commit(self):
        return None

    def cursor(self):
        return _ScriptedCursor(self._script)


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class AccountsImportFormatTests(unittest.TestCase):
    def _client(self):
        return TestClient(app_module.app)

    def _auth_headers(self, role="admin", username="admin", user_id=1):
        token = app_module.create_access_token(user_id, username, role)
        return {"Authorization": f"Bearer {token}"}

    # Собирает общий xlsx с произвольными листами.
    def _build_workbook(self):
        wb = Workbook()
        ws_summary = wb.active
        ws_summary.title = "Summary"
        ws_summary.append(["Логин", "Пароль", "Резерв 1"])
        ws_summary.append(["summary-login", "p", "r"])

        ws_mail_0 = wb.create_sheet("Почты")
        ws_mail_0.append(["Логин", "Пароль", "Резерв 1", "Резерв 2"])
        ws_mail_0.append(["user1@gmail.com", "pass-1", "res-1", "res-2"])

        ws_mail_1 = wb.create_sheet("Почты1")
        ws_mail_1.append(["Логин", "Пароль", "Резерв 1"])
        ws_mail_1.append(["user2@yahoo.com", "pass-2", "res-3"])

        ws_other = wb.create_sheet("Другое")
        ws_other.append(["Логин", "Пароль"])
        ws_other.append(["other@domain.com", "pass-x"])

        out = BytesIO()
        wb.save(out)
        return out.getvalue()

    # Проверяет, что validate читает только листы Почты* и не берет посторонние листы.
    def test_accounts_import_validate_reads_only_pochty_sheets(self):
        content = self._build_workbook()
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx([])),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/accounts/import/validate",
                    headers=self._auth_headers(role="admin"),
                    files={"file": ("accounts.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                )
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["ok"], True)
            self.assertEqual(body["total"], 2)
            self.assertEqual(len(body.get("warnings", [])), 0)

    # Проверяет предупреждение для логина без домена.
    def test_accounts_import_validate_warns_for_login_without_domain(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Почты"
        ws.append(["Логин", "Пароль", "Резерв 1"])
        ws.append(["broken-login", "pass-1", "res-1"])
        out = BytesIO()
        wb.save(out)
        content = out.getvalue()

        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx([])),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/accounts/import/validate",
                    headers=self._auth_headers(role="admin"),
                    files={"file": ("accounts.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                )
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["total"], 1)
            self.assertTrue(any("login@domain" in str(w.get("message") or "") for w in body.get("warnings", [])))

    # Проверяет, что парсер складывает резервы в reserve_values.
    def test_read_accounts_from_excel_collects_reserves(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Почты"
        ws.append(["Логин", "Пароль", "Резерв 1", "Резерв 2", "Резерв 10"])
        ws.append(["user@gmail.com", "pass-1", "one", "two", "ten"])
        out = BytesIO()
        wb.save(out)

        rows = app_module.read_accounts_from_excel(out.getvalue())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["account"], "user@gmail.com")
        self.assertEqual(rows[0]["password"], "pass-1")
        self.assertEqual(rows[0]["reserve_values"], {"reserve1": "one", "reserve2": "two", "reserve10": "ten"})


if __name__ == "__main__":
    unittest.main()
