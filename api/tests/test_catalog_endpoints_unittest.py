import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

import app as app_module


class _DummyConnCtx:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def commit(self):
        return None


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class CatalogEndpointsTests(unittest.TestCase):
    def _client(self):
        return TestClient(app_module.app)

    def _auth_headers(self, role="admin", username="admin", user_id=1):
        token = app_module.create_access_token(user_id, username, role)
        return {"Authorization": f"Bearer {token}"}

    # Получение платформ должно отдавать список с приведением slot_capacity к int.
    def test_list_platforms_success(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "qall", return_value=[("ps4", "PlayStation 4", 2)]),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/platforms", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), [{"code": "ps4", "name": "PlayStation 4", "slot_capacity": 2}])

    # Без bearer-токена защищенный endpoint должен возвращать 401.
    def test_list_platforms_requires_auth(self):
        with patch.object(app_module, "ensure_startup_schema", return_value=None):
            with self._client() as client:
                res = client.get("/platforms")
            self.assertEqual(res.status_code, 401)

    # Невалидный токен должен возвращать 401.
    def test_list_platforms_invalid_token(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/platforms", headers={"Authorization": "Bearer broken.token.value"})
            self.assertEqual(res.status_code, 401)

    # Создание платформы должно нормализовать code в lowercase.
    def test_create_platform_success(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "q1", return_value=(9,)),
            patch.object(app_module, "exec1", return_value=1) as exec1_mock,
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/platforms",
                    headers=self._auth_headers(role="admin"),
                    json={"code": "PS5", "name": "PlayStation 5", "slot_capacity": 4},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"code": "ps5", "name": "PlayStation 5", "slot_capacity": 4})
            self.assertTrue(exec1_mock.called)

    # Менеджер не должен иметь доступ к admin-only endpoint создания платформы.
    def test_create_platform_forbidden_for_manager(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/platforms",
                    headers=self._auth_headers(role="manager"),
                    json={"code": "PS5", "name": "PlayStation 5", "slot_capacity": 4},
                )
            self.assertEqual(res.status_code, 403)

    # Валидация create_platform: пустые поля -> 400.
    def test_create_platform_validation_error(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/platforms",
                    headers=self._auth_headers(role="admin"),
                    json={"code": "", "name": "", "slot_capacity": 0},
                )
            self.assertEqual(res.status_code, 400)

    # Обновление платформы должно возвращать 404, если записи нет.
    def test_update_platform_not_found(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "q1", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/platforms/ps4",
                    headers=self._auth_headers(role="admin"),
                    json={"name": "PS4 Slim", "slot_capacity": 2},
                )
            self.assertEqual(res.status_code, 404)

    # Удаление платформы должно отдавать ok=true.
    def test_delete_platform_success(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "q1", return_value=(1,)),
            patch.object(app_module, "exec1", return_value=1),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.delete("/platforms/ps4", headers=self._auth_headers(role="admin"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

    # Менеджер не должен иметь доступ к удалению платформы.
    def test_delete_platform_forbidden_for_manager(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.delete("/platforms/ps4", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 403)

    # Получение регионов должно отдавать float purchase_cost_rate.
    def test_list_regions_success(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "qall", return_value=[("RU", "Russia", 1.25)]),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/regions", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), [{"code": "RU", "name": "Russia", "purchase_cost_rate": 1.25}])

    # Создание региона должно нормализовать code в uppercase.
    def test_create_region_success(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "q1", return_value=(9,)),
            patch.object(app_module, "exec1", return_value=1) as exec1_mock,
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/regions",
                    headers=self._auth_headers(role="admin"),
                    json={"code": "ru", "name": "Russia", "purchase_cost_rate": 1.1},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"code": "RU", "name": "Russia", "purchase_cost_rate": 1.1})
            self.assertTrue(exec1_mock.called)
            self.assertGreaterEqual(exec1_mock.call_count, 2)

    # Менеджер не должен иметь доступ к созданию региона.
    def test_create_region_forbidden_for_manager(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/regions",
                    headers=self._auth_headers(role="manager"),
                    json={"code": "RU", "name": "Russia", "purchase_cost_rate": 1.1},
                )
            self.assertEqual(res.status_code, 403)

    # Удаление региона должно возвращать 404, если записи нет.
    def test_delete_region_not_found(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "q1", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.delete("/regions/RU", headers=self._auth_headers(role="admin"))
            self.assertEqual(res.status_code, 404)

    # Получение доменов должно возвращать справочник в формате PlatformOut.
    def test_list_domains_success(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "qall", return_value=[("gmail.com", "gmail.com")]),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/domains", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), [{"code": "gmail.com", "name": "gmail.com", "slot_capacity": 0}])

    # Создание домена должно нормализовать имя в lowercase.
    def test_create_domain_success(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "exec1", return_value=1) as exec1_mock,
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/domains",
                    headers=self._auth_headers(role="admin"),
                    json={"name": "GMAIL.COM"},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"code": "gmail.com", "name": "gmail.com", "slot_capacity": 0})
            self.assertTrue(exec1_mock.called)

    # Пустое имя домена должно возвращать 400.
    def test_create_domain_validation_error(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post("/domains", headers=self._auth_headers(role="admin"), json={"name": "  "})
            self.assertEqual(res.status_code, 400)

    # Менеджер не должен иметь доступ к созданию домена.
    def test_create_domain_forbidden_for_manager(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post("/domains", headers=self._auth_headers(role="manager"), json={"name": "gmail.com"})
            self.assertEqual(res.status_code, 403)

    # Удаление домена должно отдавать ok=true.
    def test_delete_domain_success(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "q1", return_value=(1,)),
            patch.object(app_module, "exec1", return_value=1),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.delete("/domains/gmail.com", headers=self._auth_headers(role="admin"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

    # Получение источников должно отдавать список SourceOut.
    def test_list_sources_success(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "qall", return_value=[(10, "tg", "Telegram")]),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/sources", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), [{"source_id": 10, "code": "tg", "name": "Telegram"}])

    # Создание источника должно возвращать созданную запись.
    def test_create_source_success(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "q1", return_value=(3, "tg", "Telegram")),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/sources",
                    headers=self._auth_headers(role="admin"),
                    json={"code": "TG", "name": "Telegram"},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"source_id": 3, "code": "tg", "name": "Telegram"})

    # Пустые code/name для источника должны возвращать 400.
    def test_create_source_validation_error(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/sources",
                    headers=self._auth_headers(role="admin"),
                    json={"code": " ", "name": ""},
                )
            self.assertEqual(res.status_code, 400)

    # Менеджер не должен иметь доступ к созданию источника.
    def test_create_source_forbidden_for_manager(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/sources",
                    headers=self._auth_headers(role="manager"),
                    json={"code": "tg", "name": "Telegram"},
                )
            self.assertEqual(res.status_code, 403)

    # Обновление источника должно отдавать 404, если записи нет.
    def test_update_source_not_found(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "q1", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/sources/7",
                    headers=self._auth_headers(role="admin"),
                    json={"name": "New name"},
                )
            self.assertEqual(res.status_code, 404)

    # Удаление источника должно отдавать ok=true.
    def test_delete_source_success(self):
        with (
            patch.object(app_module, "ensure_startup_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "q1", return_value=(1,)),
            patch.object(app_module, "exec1", return_value=1),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.delete("/sources/7", headers=self._auth_headers(role="admin"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})


if __name__ == "__main__":
    unittest.main()
