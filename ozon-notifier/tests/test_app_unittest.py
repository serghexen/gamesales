import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
SPEC = importlib.util.spec_from_file_location("ozon_notifier_app", APP_PATH)
APP = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = APP
SPEC.loader.exec_module(APP)


class OzonNotifierMessageTests(unittest.TestCase):
    def test_new_order_message_confirms_arrival_and_shows_actual_status_without_deadline(self):
        # Проверяет, что уведомление сохраняет факт поступления и не скрывает быструю автовыдачу.
        order = {
            "posting_number": "123-456",
            "order_number": "OZN-7",
            "product_name": "Подарочная карта",
            "required_qty": 2,
            "status": "supplier_processing",
            "waiting_deadline_at": datetime(2026, 7, 24, 12, 30, tzinfo=timezone.utc),
        }

        text = APP.message_text(order)

        self.assertIn("Поступил новый заказ Ozon", text)
        self.assertIn("Заказ: OZN-7", text)
        self.assertIn("Количество: 2", text)
        self.assertIn("Текущий статус: Обрабатывается поставщиком", text)
        self.assertNotIn("Дедлайн выдачи:", text)

    def test_status_update_shows_actual_order_state(self):
        # Проверяет, что после первого сообщения бот по-прежнему показывает текущий технический результат заказа.
        text = APP.message_text({"status": "delivered"})

        self.assertIn("Текущий статус: Выполнен", text)

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
