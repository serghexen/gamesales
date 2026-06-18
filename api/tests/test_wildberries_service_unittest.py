import json
import io
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch
import urllib.error

from domains import wildberries_service


class _Response:
    def __init__(self, status: int, payload):
        self.status = status
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


class WildberriesServiceTests(unittest.TestCase):
    def setUp(self):
        # Сбрасываем локальный лимитер, чтобы тесты запросов не зависели друг от друга.
        wildberries_service._REPORT_LAST_ATTEMPT.clear()

    # Агрегация должна свести продажи, возвраты и услуги к дневной сумме выплаты.
    def test_aggregate_report_rows_calculates_daily_gross_expense_and_payout(self):
        rows = [
            {
                "rrDate": "2026-06-01",
                "docTypeName": "Продажа",
                "retailAmount": "1000",
                "forPay": "800",
                "deliveryService": "50",
                "paidStorage": "10",
                "penalty": "5",
                "additionalPayment": "20",
                "rrdId": 10,
                "reportId": 7,
                "orderId": 101,
                "srid": "sale-1",
            },
            {
                "rrDate": "2026-06-01",
                "docTypeName": "Возврат",
                "retailAmount": "200",
                "forPay": "160",
                "rrdId": 11,
                "reportId": 7,
                "orderId": 102,
                "srid": "return-1",
            },
        ]

        result = wildberries_service.aggregate_wildberries_report_rows(rows, fallback_date=date(2026, 6, 1), store_code="sps")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["gross_amount"], 1000)
        self.assertEqual(result[0]["payout_amount"], 595)
        self.assertEqual(result[0]["expense_amount"], 405)
        self.assertEqual(result[0]["payload_json"]["returns"], "200")
        self.assertEqual(result[0]["payload_json"]["store_code"], "sps")
        self.assertIn("wildberries:sps:", result[0]["external_key_base"])

    # Видимый штраф WB должен уменьшать "Итого к оплате" как в ежедневном отчете ЛК.
    def test_aggregate_report_rows_subtracts_visible_daily_cabinet_penalty(self):
        rows = [
            {
                "rrDate": "2026-06-17",
                "docTypeName": "Продажа",
                "retailAmount": "8731",
                "forPay": "7676.89",
                "penalty": "155.32",
                "reportId": "410635220260617",
            },
        ]

        result = wildberries_service.aggregate_wildberries_report_rows(rows, fallback_date=date(2026, 6, 17), store_code="asat")

        self.assertEqual(result[0]["gross_amount"], 8731)
        self.assertEqual(result[0]["payout_amount"], Decimal("7521.57"))
        self.assertEqual(result[0]["expense_amount"], Decimal("1209.43"))
        self.assertEqual(result[0]["payload_json"]["penalty"], "155.32")

    # Сторно штрафа WB должно закрывать штраф в ноль, как в сводке ежедневного отчета ЛК.
    def test_aggregate_report_rows_nets_penalty_reversal(self):
        rows = [
            {
                "rrDate": "2026-06-13",
                "docTypeName": "Продажа",
                "retailAmount": "12328",
                "forPay": "10722.88",
                "reportId": "410635220260613",
            },
            {
                "rrDate": "2026-06-13",
                "sellerOperName": "Штраф",
                "retailAmount": "0",
                "forPay": "0",
                "penalty": "13.34",
                "reportId": "410635220260613",
            },
            {
                "rrDate": "2026-06-13",
                "sellerOperName": "Штраф",
                "retailAmount": "0",
                "forPay": "0",
                "penalty": "-13.34",
                "reportId": "410635220260613",
            },
        ]

        result = wildberries_service.aggregate_wildberries_report_rows(rows, fallback_date=date(2026, 6, 13), store_code="asat")

        self.assertEqual(result[0]["gross_amount"], 12328)
        self.assertEqual(result[0]["payout_amount"], Decimal("10722.88"))
        self.assertEqual(result[0]["expense_amount"], Decimal("1605.12"))
        self.assertEqual(result[0]["payload_json"]["penalty"], "0.00")

    # Загрузка должна продолжаться с последнего rrdId и завершаться после пустой страницы.
    def test_fetch_report_uses_rrd_id_pagination(self):
        responses = [
            _Response(200, [{"rrdId": 10, "rrDate": "2026-06-01"}]),
            _Response(200, [{"rrdId": 20, "rrDate": "2026-06-02"}]),
            _Response(204, []),
        ]
        requests = []

        def fake_urlopen(request, **kwargs):
            # Сохраняем тела запросов, чтобы проверить переход между страницами.
            requests.append(json.loads(request.data.decode("utf-8")))
            return responses.pop(0)

        with (
            patch.dict(
                "os.environ",
                {
                    "WILDBERRIES_TOKEN": "secret",
                    "WILDBERRIES_REPORT_LIMIT": "1",
                    "WILDBERRIES_REQUEST_INTERVAL_SEC": "0",
                },
            ),
            patch.object(wildberries_service.urllib.request, "urlopen", side_effect=fake_urlopen),
        ):
            rows = wildberries_service.fetch_wildberries_sales_report(date(2026, 6, 1), date(2026, 6, 2))

        self.assertEqual([row["rrdId"] for row in rows], [10, 20])
        self.assertEqual([request["rrdId"] for request in requests], [0, 10, 20])

    # Пустой токен должен завершать синхронизацию до обращения к WB.
    def test_fetch_report_requires_token(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(Exception, "WILDBERRIES_ASAT_TOKEN is not configured"):
                wildberries_service.fetch_wildberries_sales_report(date(2026, 6, 1), date(2026, 6, 1))

    # SPS должен использовать отдельный scoped-токен и не брать общий токен ASAT.
    def test_fetch_report_uses_store_scoped_token(self):
        captured_authorization = []

        def fake_urlopen(request, **kwargs):
            # Сохраняем только заголовок авторизации, не выводя его в рабочие логи.
            captured_authorization.append(request.headers.get("Authorization"))
            return _Response(200, [])

        with (
            patch.dict(
                "os.environ",
                {
                    "WILDBERRIES_TOKEN": "asat-token",
                    "WILDBERRIES_SPS_TOKEN": "sps-token",
                    "WILDBERRIES_REQUEST_INTERVAL_SEC": "0",
                },
                clear=True,
            ),
            patch.object(wildberries_service.urllib.request, "urlopen", side_effect=fake_urlopen),
        ):
            wildberries_service.fetch_wildberries_sales_report(
                date(2026, 6, 1),
                date(2026, 6, 1),
                store_code="sps",
            )

        self.assertEqual(captured_authorization, ["sps-token"])

    # Повторный запрос раньше лимита должен подождать и продолжить без ошибки.
    def test_report_rate_limit_waits_and_continues(self):
        clock = [100.0]
        progress = []

        def fake_sleep(seconds):
            # Двигаем монотонное время без реального ожидания теста.
            clock[0] += seconds

        with patch.dict("os.environ", {"WILDBERRIES_REQUEST_INTERVAL_SEC": "61"}):
            with (
                patch.object(wildberries_service.time, "monotonic", side_effect=lambda: clock[0]),
                patch.object(wildberries_service.time, "sleep", side_effect=fake_sleep),
            ):
                wildberries_service._wait_for_report_slot("token-asat", progress.append)
                wildberries_service._wait_for_report_slot("token-asat", progress.append)

        self.assertEqual(progress[0], "Ждем лимит Wildberries: 61 сек.")
        self.assertEqual(progress[-1], "Ждем лимит Wildberries: 1 сек.")

    # Ответ 429 от WB должен приводить к ожиданию и автоматическому повтору той же страницы.
    def test_report_page_retries_after_remote_rate_limit(self):
        rate_error = urllib.error.HTTPError(
            url="https://example.test",
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "2"},
            fp=io.BytesIO(b'{"error":"rate limit"}'),
        )
        progress = []
        with (
            patch.dict(
                "os.environ",
                {
                    "WILDBERRIES_REQUEST_INTERVAL_SEC": "0",
                    "WILDBERRIES_RATE_LIMIT_BUFFER_SEC": "0",
                },
            ),
            patch.object(
                wildberries_service.urllib.request,
                "urlopen",
                side_effect=[rate_error, _Response(200, [{"rrdId": 10}])],
            ),
            patch.object(wildberries_service.time, "sleep", return_value=None),
        ):
            page = wildberries_service._request_report_page(
                "https://example.test",
                token="secret",
                payload={"rrdId": 0},
                timeout=5,
                rate_key="token-asat",
                progress=progress.append,
            )

        self.assertEqual(page, [{"rrdId": 10}])
        self.assertEqual(progress, [
            "Wildberries ограничил запрос, повторяем через: 2 сек.",
            "Wildberries ограничил запрос, повторяем через: 1 сек.",
        ])

    # Многочасовой лимит новой API должен сразу переключать загрузку на старый отчет.
    def test_fetch_report_falls_back_to_legacy_report(self):
        rate_error = urllib.error.HTTPError(
            url="https://finance-api.test",
            code=429,
            msg="Too Many Requests",
            hdrs={"X-Ratelimit-Retry": "41938"},
            fp=io.BytesIO(b'{"title":"too many requests"}'),
        )
        legacy_row = {
            "rrd_id": 77,
            "realizationreport_id": 5,
            "rr_dt": "2026-06-07T00:00:00",
            "doc_type_name": "Продажа",
            "retail_amount": 1000,
            "ppvz_for_pay": 800,
            "delivery_rub": 50,
            "sa_name": "SKU-1",
        }
        progress = []
        with (
            patch.dict(
                "os.environ",
                {
                    "WILDBERRIES_TOKEN": "secret",
                    "WILDBERRIES_REQUEST_INTERVAL_SEC": "0",
                },
            ),
            patch.object(
                wildberries_service.urllib.request,
                "urlopen",
                side_effect=[rate_error, _Response(200, [legacy_row])],
            ),
        ):
            rows = wildberries_service.fetch_wildberries_sales_report(
                date(2026, 6, 7),
                date(2026, 6, 10),
                progress=progress.append,
            )

        self.assertEqual(rows[0]["rrdId"], 77)
        self.assertEqual(rows[0]["retailAmount"], 1000)
        self.assertEqual(rows[0]["vendorCode"], "SKU-1")
        self.assertIn("Переключаемся на резервный отчет Wildberries", progress)

    # Legacy-отчет должен передавать реальное время сброса лимита из заголовка WB.
    def test_legacy_report_returns_exact_rate_limit_wait(self):
        rate_error = urllib.error.HTTPError(
            url="https://statistics-api.test",
            code=429,
            msg="Too Many Requests",
            hdrs={"X-Ratelimit-Retry": "43087"},
            fp=io.BytesIO(b'{"title":"too many requests"}'),
        )
        with patch.object(wildberries_service.urllib.request, "urlopen", side_effect=rate_error):
            with self.assertRaisesRegex(Exception, "через 43087 сек"):
                wildberries_service._fetch_legacy_sales_report(
                    date(2026, 6, 7),
                    date(2026, 6, 10),
                    token="secret",
                    timeout=5,
                )


if __name__ == "__main__":
    unittest.main()
