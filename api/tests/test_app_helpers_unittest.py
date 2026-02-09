import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException

from app import (
    MIN_DATE,
    MAX_LOGO_BYTES,
    detect_logo_mime_from_bytes,
    fetch_logo_from_url,
    normalize_date,
    normalize_datetime,
    normalize_platform_codes,
    validate_date_in_range,
    validate_date_not_future,
    validate_date_range,
)


class _FakeUrlResp:
    def __init__(self, payload: bytes, content_type: str):
        self._payload = payload
        self.headers = {"Content-Type": content_type}

    def read(self, _size=None):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class AppHelpersTests(unittest.TestCase):
    # Проверяем очистку, приведение к нижнему регистру и удаление дублей платформ.
    def test_normalize_platform_codes_deduplicates_and_trims(self):
        raw = ["PS5", " ps5 ", "PS4", "", None, "ps4", "  xBoX  "]
        self.assertEqual(normalize_platform_codes(raw), ["ps5", "ps4", "xbox"])

    # Пустой список и None должны превращаться в пустой массив.
    def test_normalize_platform_codes_empty_inputs(self):
        self.assertEqual(normalize_platform_codes(None), [])
        self.assertEqual(normalize_platform_codes([]), [])

    # datetime без tz должен считаться UTC.
    def test_normalize_datetime_adds_utc_for_naive_datetime(self):
        value = datetime(2026, 2, 1, 12, 30, 0)
        normalized = normalize_datetime(value)
        self.assertEqual(normalized.tzinfo, timezone.utc)

    # date должен превращаться в datetime с полуночью UTC.
    def test_normalize_datetime_from_date(self):
        value = date(2026, 2, 1)
        normalized = normalize_datetime(value)
        self.assertEqual(normalized, datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc))

    # datetime должен превращаться в date.
    def test_normalize_date_from_datetime(self):
        value = datetime(2026, 2, 1, 12, 30, tzinfo=timezone.utc)
        self.assertEqual(normalize_date(value), date(2026, 2, 1))

    # Валидатор диапазона дат должен падать, если дата в будущем.
    def test_validate_date_in_range_raises_for_future_date(self):
        future = date.today() + timedelta(days=1)
        with self.assertRaises(HTTPException):
            validate_date_in_range(future, "purchase_at")

    # Валидатор диапазона дат должен падать, если дата раньше MIN_DATE.
    def test_validate_date_in_range_raises_for_too_old_date(self):
        old = MIN_DATE - timedelta(days=1)
        with self.assertRaises(HTTPException):
            validate_date_in_range(old, "purchase_at")

    # Валидатор "не в будущем" должен принимать текущий день.
    def test_validate_date_not_future_accepts_today(self):
        validate_date_not_future(date.today(), "purchase_at")

    # Валидатор диапазона должен падать, когда конец раньше начала.
    def test_validate_date_range_raises_for_inverted_range(self):
        start = date(2026, 2, 10)
        end = date(2026, 2, 9)
        with self.assertRaises(HTTPException):
            validate_date_range(start, end, "period")

    # Валидатор диапазона должен пропускать корректный интервал.
    def test_validate_date_range_accepts_valid_range(self):
        start = date(2026, 2, 1)
        end = date(2026, 2, 9)
        validate_date_range(start, end, "period")

    # Определение MIME по сигнатурам изображений.
    def test_detect_logo_mime_from_bytes(self):
        jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 16
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
        webp = b"RIFF" + b"\x01\x00\x00\x00" + b"WEBP" + b"\x00" * 8
        unknown = b"NOT_IMAGE_DATA"

        self.assertEqual(detect_logo_mime_from_bytes(jpeg), "image/jpeg")
        self.assertEqual(detect_logo_mime_from_bytes(png), "image/png")
        self.assertEqual(detect_logo_mime_from_bytes(webp), "image/webp")
        self.assertEqual(detect_logo_mime_from_bytes(unknown), "")

    # Если content-type корректный, mime должен браться из заголовка.
    def test_fetch_logo_from_url_uses_content_type_header(self):
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 32
        with patch("app.urllib.request.urlopen", return_value=_FakeUrlResp(data, "image/jpeg")):
            blob, mime = fetch_logo_from_url("https://example.com/logo.jpg")
        self.assertEqual(blob, data)
        self.assertEqual(mime, "image/jpeg")

    # Если content-type невалидный, mime должен определяться по сигнатуре байтов.
    def test_fetch_logo_from_url_fallback_to_signature_detection(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        with patch("app.urllib.request.urlopen", return_value=_FakeUrlResp(data, "application/octet-stream")):
            blob, mime = fetch_logo_from_url("https://example.com/logo.bin")
        self.assertEqual(blob, data)
        self.assertEqual(mime, "image/png")

    # Неизвестный формат должен приводить к ошибке.
    def test_fetch_logo_from_url_rejects_unknown_logo_type(self):
        data = b"NOT_IMAGE_DATA"
        with patch("app.urllib.request.urlopen", return_value=_FakeUrlResp(data, "application/octet-stream")):
            with self.assertRaises(ValueError):
                fetch_logo_from_url("https://example.com/file.bin")

    # Слишком большой файл должен отклоняться.
    def test_fetch_logo_from_url_rejects_too_large_logo(self):
        data = b"\xff\xd8\xff\xe0" + b"\x00" * (MAX_LOGO_BYTES + 8)
        with patch("app.urllib.request.urlopen", return_value=_FakeUrlResp(data, "image/jpeg")):
            with self.assertRaises(ValueError):
                fetch_logo_from_url("https://example.com/huge.jpg")


if __name__ == "__main__":
    unittest.main()
