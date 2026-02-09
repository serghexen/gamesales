import unittest
from unittest.mock import patch

from fastapi import HTTPException

import app as app_module
from app import (
    UserOut,
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
    verify_password,
)


class AuthHelpersTests(unittest.TestCase):
    # Проверяем, что хешируется и верифицируется один и тот же пароль.
    def test_hash_and_verify_password_roundtrip(self):
        raw = "secret-123"
        hashed = hash_password(raw)
        self.assertNotEqual(hashed, raw)
        self.assertTrue(verify_password(raw, hashed))
        self.assertFalse(verify_password("wrong", hashed))

    # Старые passlib-хеши тоже должны проходить проверку после миграции.
    def test_verify_legacy_passlib_hash(self):
        legacy_hash = "$pbkdf2-sha256$29000$53yPcY5x7n0vBWAMIYRwLg$SEHXTKQhM2FcG197WWW4MnD9awfIzoHmhJmM4A.gAVM"
        self.assertTrue(verify_password("secret-123", legacy_hash))
        self.assertFalse(verify_password("wrong", legacy_hash))

    # При пустом JWT_SECRET токен создавать нельзя.
    def test_create_access_token_requires_secret(self):
        with patch.object(app_module, "JWT_SECRET", ""):
            with self.assertRaises(HTTPException) as ctx:
                create_access_token(1, "admin", "admin")
            self.assertEqual(ctx.exception.status_code, 500)

    # Валидный токен должен корректно читаться в current user.
    def test_get_current_user_with_valid_bearer_token(self):
        with patch.object(app_module, "JWT_SECRET", "test-secret"), patch.object(app_module, "JWT_ALG", "HS256"):
            token = create_access_token(7, "alice", "manager")
            user = get_current_user(f"Bearer {token}")
            self.assertEqual(user.username, "alice")
            self.assertEqual(user.role, "manager")

    # Без Bearer заголовка должен быть 401.
    def test_get_current_user_rejects_missing_bearer(self):
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(None)
        self.assertEqual(ctx.exception.status_code, 401)

    # Невалидный токен должен давать 401.
    def test_get_current_user_rejects_invalid_token(self):
        with patch.object(app_module, "JWT_SECRET", "test-secret"), patch.object(app_module, "JWT_ALG", "HS256"):
            with self.assertRaises(HTTPException) as ctx:
                get_current_user("Bearer not.a.valid.token")
            self.assertEqual(ctx.exception.status_code, 401)

    # require_role пропускает пользователя с нужной ролью.
    def test_require_role_allows_expected_role(self):
        dep = require_role("admin")
        user = dep(UserOut(username="boss", role="admin"))
        self.assertEqual(user.username, "boss")

    # require_role блокирует пользователя с другой ролью.
    def test_require_role_forbids_wrong_role(self):
        dep = require_role("admin")
        with self.assertRaises(HTTPException) as ctx:
            dep(UserOut(username="manager", role="manager"))
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
