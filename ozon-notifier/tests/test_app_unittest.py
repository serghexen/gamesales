import importlib.util
import sys
import unittest
from pathlib import Path


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
SPEC = importlib.util.spec_from_file_location("ozon_notifier_app", APP_PATH)
APP = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = APP
SPEC.loader.exec_module(APP)


class OzonNotifierMessageTests(unittest.TestCase):
    def test_error_alert_contains_manual_action_and_order_details(self):
        # Проверяет, что оператор видит понятное действие без технического текста поставщика.
        order = {
            "posting_number": "123-456",
            "order_number": "OZN-7",
            "product_name": "Подарочная карта",
            "required_qty": 2,
            "status": "supplier_processing",
            "last_error": "Interhub не вернул ключ",
        }

        text = APP.alert_text(order)

        self.assertIn("Требуется оператор", text)
        self.assertIn("Площадка: Ozon", text)
        self.assertIn("Заказ: OZN-7", text)
        self.assertIn("Количество: 2", text)
        self.assertIn("Причина: Необходим ручной ввод или ручная отправка.", text)
        self.assertNotIn("Interhub", text)

    def test_successful_order_does_not_create_alert(self):
        # Проверяет, что успешная выдача не создаёт уведомление и не засоряет рабочий чат.
        key = APP.alert_key({"status": "delivered"})

        self.assertEqual(key, "")

    def test_resolved_problem_creates_a_separate_resolution_notification(self):
        # Проверяет, что после тревоги об успехе приходит отдельное сообщение, а не изменение старого текста.
        order = {
            "order_number": "OZN-8",
            "product_name": "Steam Wallet 1000 ₽",
            "required_qty": 1,
            "status": "delivered",
            "last_status": "alert:error:abc",
        }

        self.assertEqual(APP.notification_key(order), "resolved")
        self.assertIn("✅ Проблема решена", APP.resolution_text(order))
        self.assertIn("Площадка: Ozon", APP.resolution_text(order))
        self.assertIn("Текущий статус: Выполнен", APP.resolution_text(order))

    def test_yandex_market_error_alert_hides_provider_detail(self):
        # Проверяет, что тревога Яндекс Маркета показывает оператору действие без технической ошибки поставщика.
        delivery = {
            "order_id": 101,
            "offer_id": "PSN-500",
            "item_name": "PlayStation Store 500 ₽",
            "required_qty": 1,
            "status": "market_unknown",
            "last_error": "Сетевая ошибка поставщика",
        }

        text = APP.yandex_alert_text(delivery)

        self.assertIn("Требуется оператор", text)
        self.assertIn("Площадка: Яндекс Маркет", text)
        self.assertIn("Заказ: 101", text)
        self.assertIn("Необходим ручной ввод или ручная отправка.", text)
        self.assertNotIn("Сетевая ошибка поставщика", text)

    def test_yandex_market_resolution_requires_a_previous_alert(self):
        # Проверяет, что успешная выдача Яндекс Маркета сама по себе не создаёт сообщение о решении.
        successful_delivery = {"status": "market_delivered", "last_status": ""}
        resolved_delivery = {"status": "market_delivered", "last_status": "alert:market_unknown"}

        self.assertEqual(APP.yandex_notification_key(successful_delivery), "")
        self.assertEqual(APP.yandex_notification_key(resolved_delivery), "resolved")
        self.assertIn("✅ Проблема решена", APP.yandex_resolution_text(resolved_delivery))

    def test_manual_order_and_changed_error_have_distinct_alerts(self):
        # Проверяет, что ручная обработка и новая причина ошибки доставляются как отдельные полезные тревоги.
        manual_key = APP.alert_key({"status": "manual_required", "operator_wait_expired": False})
        first_error_key = APP.alert_key({"status": "manual_required", "last_error": "Первая ошибка"})
        second_error_key = APP.alert_key({"status": "manual_required", "last_error": "Другая ошибка"})

        self.assertEqual(manual_key, "alert:manual_required")
        self.assertNotEqual(first_error_key, second_error_key)

    def test_unknown_status_is_shown_as_processing(self):
        # Оставляет нейтральный понятный статус, пока новый технический код Ozon не добавлен в словарь.
        self.assertEqual(APP.status_title("new_ozon_status"), "Обрабатывается")

    def test_subscription_commands_support_group_suffix(self):
        # Принимает команду из группы, где Telegram дописывает имя бота после символа @.
        self.assertEqual(APP.command_kind("/subscribe@ozon_orders_bot"), "subscribe")
        self.assertEqual(APP.command_kind("/stop"), "unsubscribe")

    def test_minimum_poll_interval_protects_database(self):
        # Не даёт настройкой опустить опрос БД ниже безопасного минимального интервала.
        previous = APP.os.environ.get("OZON_NOTIFIER_TEST_INTERVAL")
        APP.os.environ["OZON_NOTIFIER_TEST_INTERVAL"] = "1"
        try:
            self.assertEqual(APP.env_int("OZON_NOTIFIER_TEST_INTERVAL", default=15, minimum=5), 5)
        finally:
            if previous is None:
                APP.os.environ.pop("OZON_NOTIFIER_TEST_INTERVAL", None)
            else:
                APP.os.environ["OZON_NOTIFIER_TEST_INTERVAL"] = previous
