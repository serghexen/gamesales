import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

from api.domains.dashboard_api import mount_dashboard_routes


class _FakeRedis:
    def __init__(self):
        self._data = {}
        self._zsets = {}
        self._hashes = {}

    # Храним presence в памяти, чтобы тестировать endpoint без реального Redis.
    def set(self, key, value, ex=None):
        _ = ex
        self._data[key] = value
        return True

    def get(self, key):
        return self._data.get(key)

    def hset(self, key, field, value):
        bucket = self._hashes.setdefault(key, {})
        bucket[str(field)] = value
        return 1

    def hmget(self, key, fields):
        bucket = self._hashes.get(key, {})
        return [bucket.get(str(field)) for field in (fields or [])]

    def hdel(self, key, *fields):
        bucket = self._hashes.get(key, {})
        deleted = 0
        for field in fields:
            field_key = str(field)
            if field_key in bucket:
                del bucket[field_key]
                deleted += 1
        return deleted

    def zadd(self, key, mapping):
        bucket = self._zsets.setdefault(key, {})
        for member, score in (mapping or {}).items():
            bucket[str(member)] = float(score)
        return 1

    def zremrangebyscore(self, key, min_score, max_score):
        bucket = self._zsets.get(key, {})
        if not bucket:
            return 0
        min_value = float("-inf") if str(min_score) == "-inf" else float(min_score)
        max_value = float("inf") if str(max_score) == "+inf" else float(max_score)
        to_delete = [member for member, score in bucket.items() if min_value <= float(score) <= max_value]
        for member in to_delete:
            del bucket[member]
        return len(to_delete)

    def zrangebyscore(self, key, min_score, max_score):
        bucket = self._zsets.get(key, {})
        min_value = float("-inf") if str(min_score) == "-inf" else float(min_score)
        max_value = float("inf") if str(max_score) == "+inf" else float(max_score)
        rows = [(member, float(score)) for member, score in bucket.items() if min_value <= float(score) <= max_value]
        rows.sort(key=lambda item: item[1])
        return [member for member, _ in rows]

    def scan_iter(self, match=None):
        prefix = (match or "").replace("*", "")
        for key in list(self._data.keys()):
            if not prefix or str(key).startswith(prefix):
                yield key


class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class _FakePsycopg:
    def connect(self, _dsn):
        return _FakeConn()


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class DashboardEndpointsTests(unittest.TestCase):
    # Проверяем, что нагрузка считается по purchase_at/created_at и связывается с менеджером по имени/логину.
    def test_managers_load_uses_purchase_date_and_matches_manager_name(self):
        app = FastAPI()
        fake_redis = _FakeRedis()
        sql_collector = []

        def fake_qall(_conn, sql, params=None):
            sql_collector.append((sql, params))
            return [("dmitry", "Дмитрий", 1)]

        with patch("api.domains.dashboard_api.redis.Redis.from_url", return_value=fake_redis):
            mount_dashboard_routes(
                app,
                DB_DSN="postgresql://test",
                psycopg=_FakePsycopg(),
                qall=fake_qall,
                get_current_user=lambda: SimpleNamespace(username="dmitry", role="manager"),
                redis_url="redis://local",
            )

            with TestClient(app) as client:
                res = client.get("/dashboard/managers-load")

        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["online_count"], 1)
        self.assertEqual(body["items"][0]["username"], "dmitry")
        self.assertEqual(body["items"][0]["pending_count"], 1)
        self.assertTrue(sql_collector, "SQL query was not executed")
        sql_text = sql_collector[0][0]
        self.assertIn("COALESCE(di.purchase_at, d.created_at)", sql_text)
        self.assertIn("lower(COALESCE(match_u.name, '')) = lower(COALESCE(d.responsible_username, ''))", sql_text)

    # Оператор должен попадать в блок "Сделок в работе" наравне с менеджером.
    def test_managers_load_includes_operator_role(self):
        app = FastAPI()
        fake_redis = _FakeRedis()
        sql_collector = []

        def fake_qall(_conn, sql, params=None):
            sql_collector.append((sql, params))
            return [("operator1", "Оператор", 2)]

        with patch("api.domains.dashboard_api.redis.Redis.from_url", return_value=fake_redis):
            mount_dashboard_routes(
                app,
                DB_DSN="postgresql://test",
                psycopg=_FakePsycopg(),
                qall=fake_qall,
                get_current_user=lambda: SimpleNamespace(username="operator1", role="operator"),
                redis_url="redis://local",
            )

            with TestClient(app) as client:
                res = client.get("/dashboard/managers-load")

        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["online_count"], 1)
        self.assertEqual(body["items"][0]["username"], "operator1")
        self.assertEqual(body["items"][0]["pending_count"], 2)
        self.assertTrue(sql_collector, "SQL query was not executed")
        sql_text = sql_collector[0][0]
        self.assertIn("lower(u.role_code) IN ('manager', 'operator')", sql_text)


if __name__ == "__main__":
    unittest.main()
