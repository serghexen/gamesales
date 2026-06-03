import io
import os
import unittest
import urllib.error
from unittest.mock import patch

from fastapi import HTTPException

from domains import yandex_market_service


class YandexMarketServiceTests(unittest.TestCase):
    def test_request_json_maps_rate_limit_to_readable_error(self):
        error_body = b'{"errors":[{"code":"METHOD_FAILURE","message":"Hit rate limit of 1 points per 2 minutes"}]}'
        http_error = urllib.error.HTTPError(
            url="https://api.partner.market.yandex.ru/v2/reports/united-orders/generate",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(error_body),
        )

        with patch.object(yandex_market_service.urllib.request, "urlopen", side_effect=http_error):
            with self.assertRaises(HTTPException) as ctx:
                yandex_market_service._request_json("POST", "https://example.test", token="token", payload={})

        self.assertEqual(ctx.exception.status_code, 429)
        self.assertIn("Лимит Yandex Market", str(ctx.exception.detail))

    def test_generate_rate_limit_guard_blocks_second_attempt(self):
        yandex_market_service._GENERATE_LAST_ATTEMPT.clear()

        with patch.dict(os.environ, {"YANDEX_MARKET_GENERATE_COOLDOWN_SEC": "10"}):
            yandex_market_service._guard_united_orders_generate_rate_limit(48186803)
            with self.assertRaises(HTTPException) as ctx:
                yandex_market_service._guard_united_orders_generate_rate_limit(48186803)

        self.assertEqual(ctx.exception.status_code, 429)
        self.assertIn("Повторите примерно через", str(ctx.exception.detail))


if __name__ == "__main__":
    unittest.main()
