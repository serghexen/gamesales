import json
import unittest
from unittest.mock import Mock
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app as app_module
from domains.interhub_api import mount_interhub_routes
from domains.deals_api import mount_deals_routes


def playstation_services():
    # Тестовый каталог содержит только разрешённые региональные сервисы и один посторонний сервис.
    return [
        {
            "service_id": 11125,
            "title": "po_PlayStation - Turkey",
            "category": "Games",
            "type": "VOUCHER",
            "fields": [{"name": "nominal", "value_list": [{"id": 28632, "title": "TRY 250"}, {"id": 28633, "title": "TRY 500"}]}],
        },
        {
            "service_id": 9811,
            "title": "po_PlayStation - Poland",
            "category": "Games",
            "type": "VOUCHER",
            "fields": [{"name": "nominal", "value_list": [{"id": 16793, "title": "PLN 100"}, {"id": 16796, "title": "PLN 200"}]}],
        },
        {
            "service_id": 99999,
            "title": "Steam - Turkey",
            "category": "Games",
            "type": "VOUCHER",
            "fields": [{"name": "nominal", "value_list": [{"id": 1, "title": "TRY 1"}]}],
        },
    ]


class FakeDealInterhubDb:
    def __init__(self):
        self.deals = {
            42: ("sale", "TR", "confirmed", None, "ORDER-42", "buyer-tr", "pending", 1),
            43: ("sale", "US", "confirmed", None, "ORDER-43", "buyer-us", "pending", 1),
            44: ("sale", "PL", "confirmed", None, "ORDER-44", "buyer-pl", "pending", 1),
            45: ("rental", "TR", "confirmed", None, "ORDER-45", "buyer-rental", "pending", 1),
        }
        self.transactions = {}
        self.purchase_costs = {}
        self.notes = {}
        self.sql = []

    def update_deal(self, deal_id, **changes):
        # Меняем состояние тестовой БД между настоящими HTTP-вызовами, а не подменяем ответы обработчиков.
        fields = ["deal_type", "region", "status", "returned_at", "order", "buyer", "flow", "version"]
        record = dict(zip(fields, self.deals[deal_id]))
        record.update(changes)
        self.deals[deal_id] = tuple(record[name] for name in fields)

    def update_row(self, deal_id):
        # Формат совпадает с выборкой сохранения сделки, включая агрегаты оплаченных покупок.
        deal = self.deals[deal_id]
        paid = [t for t in self.transactions.values() if t["deal_id"] == deal_id and t["state"] == "paid"]
        processing = [t for t in self.transactions.values() if t["deal_id"] == deal_id and t["state"] == "processing"]
        return (
            deal[0], deal[2], deal[6], deal[7], {"TR": 1, "PL": 2, "US": 3}[deal[1]],
            7, 1000, deal[4], "operator", 1, deal_id * 10, None, None, 1000,
            self.purchase_costs.get(deal_id, 0), None, None, None, 0, None, None,
            None, self.notes.get(deal_id, ""), "", deal[3], len(paid),
            sum(t["amount"] for t in paid), len(processing),
        )

    def transaction_row(self, transaction):
        return (
            transaction["agent_transaction_id"], transaction["state"], transaction.get("provider_status", 0),
            transaction.get("provider_message", ""), transaction["service_id"], transaction["nominal_id"],
            transaction["amount"], transaction.get("gift_code", ""), transaction["created_by"],
            "2026-09-01T10:00:00Z", "2026-09-01T10:00:00Z", transaction.get("nominal_title", ""),
        )

    def active_for_deal(self, deal_id):
        # Активной считается только незавершённая покупка; оплаченные ваучеры остаются отдельными строками истории.
        allowed = {"checked", "processing"}
        matches = [item for item in self.transactions.values() if item["deal_id"] == deal_id and item["state"] in allowed]
        return matches[-1] if matches else None


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self._one = None
        self._all = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(str(sql).split())
        self.db.sql.append(normalized)
        self._one = None
        self._all = []
        self.rowcount = 0
        if normalized.startswith("SELECT deal_id FROM app.deals"):
            self._one = (int(params[0]),) if int(params[0]) in self.db.deals else None
            return
        if normalized.startswith("SELECT deal_id FROM app.interhub_transactions"):
            item = self.db.transactions.get(str(params[0]))
            self._one = (item["deal_id"],) if item else None
            return
        if "set_config" in normalized:
            return
        if "FROM app.users" in normalized:
            self._one = ("Владелец", "owner")
            return
        if normalized.startswith("SELECT 1 FROM app.deal_flow_statuses") or "FROM app.messengers" in normalized:
            self._one = (1,)
            return
        if normalized.startswith("SELECT flow_status_code,"):
            deal_id = int(params[0])
            self._one = (self.db.deals[deal_id][6], any(
                t["deal_id"] == deal_id and t["state"] in {"paid", "processing"}
                for t in self.db.transactions.values()
            ))
            return
        if normalized.startswith("UPDATE app.deals SET lock_version"):
            deal_id = int(params[0])
            self.db.update_deal(deal_id, version=self.db.deals[deal_id][7] + 1)
            self.rowcount = 1
            return
        if normalized.startswith("UPDATE app.deals SET status_code='cancelled'"):
            deal_id = int(params[0])
            self.db.update_deal(deal_id, status="cancelled", version=self.db.deals[deal_id][7] + 1)
            self.rowcount = 1
            return
        if normalized.startswith("UPDATE app.deals SET flow_status_code='pending'"):
            deal_id = int(params[1])
            self.db.update_deal(deal_id, flow="pending", version=self.db.deals[deal_id][7] + 1)
            self.rowcount = 1
            return
        if normalized.startswith("UPDATE app.deal_items SET returned_at"):
            self.db.update_deal(int(params[1]), returned_at=params[0])
            self.rowcount = 1
            return
        if normalized.startswith("UPDATE app.deals SET deal_type_code"):
            deal_id = int(params[-2])
            if self.db.deals[deal_id][7] == params[-1]:
                self.db.update_deal(deal_id, deal_type=params[0], region={1: "TR", 2: "PL", 3: "US"}[params[5]],
                                    flow=params[4], version=int(params[-1]) + 1)
                self.rowcount = 1
            return
        if normalized.startswith("UPDATE app.deal_items SET account_id"):
            deal_id = int(params[-1]) // 10
            self.db.purchase_costs[deal_id] = float(params[4])
            self.db.notes[deal_id] = params[13]
            self.rowcount = 1
            return
        if "pg_advisory_xact_lock" in normalized:
            self._one = (None,)
            return
        if "FROM app.deals d" in normalized and "JOIN app.deal_items" in normalized:
            if normalized.startswith("SELECT d.deal_type_code, d.flow_status_code, di.returned_at"):
                deal_id = int(params[0])
                deal = self.db.deals[deal_id]
                self._one = (deal[0], deal[6], deal[3], any(
                    t["deal_id"] == deal_id and t["state"] == "processing" for t in self.db.transactions.values()
                ))
                return
            self._one = self.db.update_row(int(params[0])) if "SELECT COUNT(*)" in normalized else self.db.deals.get(int(params[0]))
            return
        if "FROM app.interhub_transactions" in normalized and "deal_id=%s" in normalized and "SELECT agent_transaction_id" in normalized:
            deal_id = int(params[0])
            if "agent_transaction_id=%s" in normalized:
                item = self.db.transactions.get(str(params[1]))
                self._one = self.db.transaction_row(item) if item and item["deal_id"] == deal_id else None
            elif "state<>'cancelled'" in normalized:
                items = [item for item in self.db.transactions.values() if item["deal_id"] == deal_id and item["state"] != "cancelled"]
                self._all = [self.db.transaction_row(item) for item in reversed(items)]
            else:
                item = self.db.active_for_deal(deal_id)
                self._one = self.db.transaction_row(item) if item else None
            return
        if normalized.startswith("INSERT INTO app.interhub_transactions"):
            request_params = json.loads(params[4])
            item = {
                "agent_transaction_id": str(params[0]), "service_id": int(params[1]), "amount": float(params[3]),
                "nominal_id": str(request_params.get("nominal") or ""), "state": "checked",
                "nominal_title": str(request_params.get("nominal_title") or ""),
                "provider_status": int(params[5] or 0), "provider_message": str(params[6] or ""),
                "gift_code": "", "created_by": str(params[9] or ""), "deal_id": int(params[10]),
                "status_check_attempts": 0,
            }
            self.db.transactions[item["agent_transaction_id"]] = item
            self.rowcount = 1
            return
        if normalized.startswith("UPDATE app.interhub_transactions SET state='cancelled'"):
            item = self.db.transactions.get(str(params[0]))
            if item and item["state"] == "checked":
                item["state"] = "cancelled"
                self.rowcount = 1
            return
        if "SET state='processing'" in normalized and "WHERE agent_transaction_id=%s AND deal_id=%s" in normalized:
            item = self.db.transactions.get(str(params[0]))
            if item and item["deal_id"] == int(params[1]) and item["state"] == "checked":
                item["state"] = "processing"
                item["provider_message"] = "Оплата отправлена в InterHub; ожидается ответ"
                self._one = (item["agent_transaction_id"],)
                self.rowcount = 1
            return
        if "SET state='processing', provider_message=%s" in normalized:
            item = self.db.transactions.get(str(params[1]))
            if item and ("AND state='processing'" not in normalized or item["state"] == "processing"):
                item["state"] = "processing"
                item["provider_message"] = params[0]
            return
        if normalized.startswith("SELECT state, status_check_attempts, deal_id FROM app.interhub_transactions"):
            item = self.db.transactions.get(str(params[0]))
            self._one = (item["state"], item["status_check_attempts"], item["deal_id"]) if item else None
            return
        if normalized.startswith("UPDATE app.interhub_transactions SET state=%s"):
            item = self.db.transactions.get(str(params[-1]))
            if item:
                item["state"] = str(params[0])
                item["provider_status"] = int(params[1] or 0)
                item["provider_message"] = str(params[2] or "")
                if str(params[4] or ""):
                    item["gift_code"] = str(params[4])
                self.rowcount = 1
            return
        if normalized.startswith("UPDATE app.deal_items SET purchase_cost"):
            deal_id = int(params[0])
            self.db.purchase_costs[deal_id] = sum(
                float(item["amount"])
                for item in self.db.transactions.values()
                if item["deal_id"] == deal_id and item["state"] == "paid"
            )
            self.rowcount = 1
            return
        if normalized.startswith("WITH filtered_history AS"):
            # Повторяем состав истории, включая ID покупки для связи строк в Excel со сделками.
            paid_items = [item for item in self.db.transactions.values() if item["state"] == "paid" and item.get("deal_id")]
            if "SELECT COUNT(*), COALESCE(SUM(amount), 0)" in normalized:
                self._one = (len(paid_items), sum(item["amount"] for item in paid_items))
            else:
                service_titles = {11125: "po_PlayStation - Turkey", 9811: "po_PlayStation - Poland"}
                rows = []
                for item in reversed(paid_items):
                    deal = self.db.deals[item["deal_id"]]
                    rows.append((
                        item["service_id"], service_titles[item["service_id"]], item["nominal_id"],
                        item.get("nominal_title", ""), item["amount"], item.get("gift_code", ""),
                        "2026-09-01T10:00:00Z", item["deal_id"], deal[4], deal[5], deal[1], item["created_by"],
                        item["agent_transaction_id"],
                    ))
                self._all = rows
            return
        raise AssertionError(f"Unexpected SQL in fake DB: {normalized}")

    def fetchone(self):
        return self._one

    def fetchall(self):
        return list(self._all)


class FakeConnection:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return FakeCursor(self.db)

    def commit(self):
        return None


class FakePsycopg:
    def __init__(self, db):
        self.db = db

    def connect(self, _dsn):
        return FakeConnection(self.db)


class DealInterhubPurchaseTests(unittest.TestCase):
    def setUp(self):
        # Изолируем все внешние вызовы, включая оплату и получение отложенного результата.
        self.db = FakeDealInterhubDb()
        self.role = "operator"
        self.publish = Mock()
        self.pay = Mock(side_effect=lambda payload: {
            "success": True, "status": 0, "message": "Готово",
            "transaction_id": f"provider-{payload['agent_transaction_id']}",
            "params": {"gift_code": f"CODE-{payload['agent_transaction_id']}"}, "raw": {},
        })
        app = FastAPI()

        def current_user():
            # Оператор проходит обычную авторизацию без расширения owner-only endpoints.
            return app_module.UserOut(username=self.role, role=self.role)

        def require_role(_role):
            # Владелец тоже обязан проходить ограничения сделок, даже через общие платежные маршруты.
            def forbidden():
                if self.role == _role:
                    return current_user()
                raise HTTPException(403, "forbidden")
            return forbidden

        mount_interhub_routes(
            app,
            DB_DSN="fake",
            psycopg=FakePsycopg(self.db),
            get_current_user=current_user,
            require_role=require_role,
            UserOut=app_module.UserOut,
            InterHubServiceListOut=app_module.InterHubServiceListOut,
            InterHubBalanceOut=app_module.InterHubBalanceOut,
            InterHubPaymentRequestIn=app_module.InterHubPaymentRequestIn,
            InterHubPaymentCheckOut=app_module.InterHubPaymentCheckOut,
            InterHubPayRequestIn=app_module.InterHubPayRequestIn,
            InterHubVoucherBatchPayRequestIn=app_module.InterHubVoucherBatchPayRequestIn,
            interhub_get_services=playstation_services,
            interhub_get_balance=lambda: {"balance": 0, "currency": "RUB", "over_balance": 0, "over_limit": 0},
            interhub_calculate=lambda payload: {"success": True, "status": 0, "fixed_amount": 475.04, "message": "Цена получена", "raw": {}},
            interhub_check=lambda payload: {"success": True, "status": 0, "message": "Доступно", "transaction_id": payload["agent_transaction_id"], "raw": {}},
            interhub_pay=self.pay,
            interhub_check_status=lambda payload: {"success": True, "status": 0, "params": {"gift_code": "RECOVERED"}, "raw": {}},
            publish_deal_event=self.publish,
        )
        # Монтируем реальные сохранение и удаление рядом с покупками: цепочки проходят через одну тестовую БД.
        mount_deals_routes(
            app, DB_DSN="fake", psycopg=FakePsycopg(self.db),
            q1=app_module.q1, qall=app_module.qall, exec1=app_module.exec1,
            now_utc=lambda: datetime.now(timezone.utc),
            validate_date_in_range=lambda *args: None, validate_date_range=lambda *args: None,
            ensure_account_exists=lambda *args: None, ensure_source_exists=lambda *args: None,
            ensure_account_allows_slot_type=lambda *args: None, get_platform_id=lambda *args: 1,
            get_region_id=lambda conn, code: {"TR": 1, "PL": 2, "US": 3}[code],
            get_account_slot_free=lambda *args: 1, ensure_customer=lambda *args: 7,
            get_slot_type=lambda *args: None, account_has_ps4=lambda *args: False,
            release_slot_assignment=lambda *args: None, build_deals_filters=lambda *args: None,
            slots_summary=lambda *args: None, get_current_user=current_user,
        )
        self.client = TestClient(app)

    def prepare(self, deal_id=42, nominal="28632"):
        # Клиент передаёт версию именно той сохранённой карточки, для которой запрашивает цену.
        return self.client.post(f"/deals/{deal_id}/interhub/prepare", json={
            "nominal_id": nominal, "lock_version": self.db.deals[deal_id][7],
        })

    def buy(self, prepared, deal_id=42):
        # Для оплаты сохраняем версию и ID проверки, даже если карточка уже изменилась.
        return self.client.post(f"/deals/{deal_id}/interhub/pay", json={
            "agent_transaction_id": prepared["agent_transaction_id"], "lock_version": prepared["lock_version"],
        })

    def test_saving_historical_deal_preserves_purchase_cost_without_vouchers(self):
        # Старая сделка хранит ручной закуп без истории ваучеров; правка комментария не теряет сумму.
        self.role = "owner"
        for deal_id in (42, 44):
            for flow in ("pending", "completed", "draft"):
                with self.subTest(deal_id=deal_id, flow=flow):
                    self.db.update_deal(deal_id, flow=flow)
                    self.db.purchase_costs[deal_id] = 123.45
                    response = self.client.put(f"/deals/{deal_id}", json={
                        "lock_version": self.db.deals[deal_id][7],
                        "purchase_cost": 123.45, "notes": "уточнение старой сделки",
                    })
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(self.db.purchase_costs[deal_id], 123.45)
        self.pay.assert_not_called()

    def test_draft_to_purchase_save_and_delete_preserves_codes_and_cost(self):
        # Черновик не покупает; рабочая сделка покупает, затем сохраняется без потери суммы и истории.
        self.db.update_deal(42, flow="draft")
        blocked = self.prepare()
        self.assertEqual(blocked.status_code, 409)
        self.assertIn("черновике", blocked.json()["detail"])
        self.pay.assert_not_called()
        self.assertEqual(self.db.transactions, {})
        self.assertFalse(self.client.get("/deals/42/interhub").json()["purchase_allowed"])

        saved = self.client.put("/deals/42", json={"flow_status_code": "pending", "lock_version": 1})
        self.assertEqual(saved.status_code, 200, saved.text)
        prepared = self.prepare().json()
        paid = self.buy(prepared).json()
        self.assertEqual(paid["state"], "paid")
        self.assertEqual(self.db.deals[42][7], 3)
        self.assertEqual(self.buy(prepared).json()["gift_code"], paid["gift_code"])
        self.assertEqual(self.db.deals[42][7], 3)
        self.assertEqual(self.pay.call_count, 1)

        stale = self.client.put("/deals/42", json={"lock_version": 2, "purchase_cost": 0})
        self.assertEqual(stale.status_code, 409)
        saved = self.client.put("/deals/42", json={"lock_version": 3, "purchase_cost": 0, "notes": "после покупки"})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.db.purchase_costs[42], 475.04)
        self.assertEqual(self.db.notes[42], "после покупки")
        self.assertEqual(self.client.delete("/deals/42").status_code, 400)

        # Даже перевод обратно в черновик не позволяет удалить оплаченный код.
        saved = self.client.put("/deals/42", json={"lock_version": 4, "flow_status_code": "draft"})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.prepare().status_code, 409)
        self.assertEqual(self.client.delete("/deals/42").status_code, 409)
        history = self.client.get("/deals/42/interhub").json()
        self.assertEqual(history["purchases"][0]["gift_code"], paid["gift_code"])
        self.assertEqual(history["lock_version"], 5)
        self.assertEqual(self.db.deals[42][2], "confirmed")

    def test_empty_draft_can_still_be_deleted(self):
        # Обычное удаление неоплаченного черновика остаётся доступным.
        self.db.update_deal(42, flow="draft")
        self.assertEqual(self.client.delete("/deals/42").status_code, 200)
        self.assertEqual(self.db.deals[42][2], "cancelled")
        self.assertEqual(self.prepare().status_code, 404)

    def test_region_change_requires_new_check_and_keeps_paid_region(self):
        # Старый турецкий check нельзя оплатить после сохранения Польши.
        old = self.prepare().json()
        saved = self.client.put("/deals/42", json={"lock_version": 1, "region_code": "PL"})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.buy(old).status_code, 409)
        self.assertEqual(self.prepare().status_code, 422)
        self.pay.assert_not_called()
        new = self.prepare(nominal="16793").json()
        paid = self.buy(new).json()
        self.assertEqual(paid["service_id"], 9811)
        self.assertEqual(paid["nominal_title"], "PLN 100")
        self.assertEqual(self.db.deals[42][7], 3)
        blocked = self.client.put("/deals/42", json={"lock_version": 3, "region_code": "TR"})
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(self.db.deals[42][1], "PL")

    def test_stale_or_missing_version_and_draft_transition_prevent_payment(self):
        # Версию нельзя обойти прямым запросом; переход в черновик запрещает даже ранее проверенную покупку.
        self.assertEqual(self.client.post("/deals/42/interhub/prepare", json={"nominal_id": "28632"}).status_code, 422)
        old = self.prepare().json()
        self.assertEqual(self.client.put("/deals/42", json={"lock_version": 1, "notes": "правка"}).status_code, 200)
        self.assertEqual(self.buy(old).status_code, 409)
        self.assertEqual(self.client.post("/deals/42/interhub/prepare", json={"nominal_id": "28632", "lock_version": 1}).status_code, 409)
        updated = self.prepare().json()
        self.assertEqual(self.client.put("/deals/42", json={"lock_version": 2, "flow_status_code": "draft"}).status_code, 200)
        self.assertEqual(self.buy(updated).status_code, 409)
        self.pay.assert_not_called()

    def test_save_and_delete_cannot_overtake_processing_payment(self):
        # Проверяем окно между отправкой денег и ответом поставщика через реальные HTTP-обработчики.
        prepared = self.prepare().json()
        normal_pay = self.pay.side_effect

        def during_pay(payload):
            # Имитируем второй запрос, пришедший до ответа поставщика.
            save = self.client.put("/deals/42", json={"lock_version": 1, "flow_status_code": "draft"})
            self.assertEqual(save.status_code, 409)
            self.assertEqual(self.db.deals[42][6], "pending")
            self.db.update_deal(42, flow="draft")
            self.assertEqual(self.client.delete("/deals/42").status_code, 409)
            self.db.update_deal(42, flow="pending")
            return normal_pay(payload)

        self.pay.side_effect = during_pay
        self.assertEqual(self.buy(prepared).json()["state"], "paid")
        self.assertEqual(self.db.purchase_costs[42], 475.04)
        self.assertTrue(any("FOR UPDATE" in sql and "app.deals" in sql for sql in self.db.sql))

    def test_transaction_from_another_deal_cannot_be_paid(self):
        # Номер транзакции сам по себе не даёт доступ к оплате или коду другой сделки.
        prepared = self.prepare().json()
        self.assertEqual(self.buy(prepared, deal_id=44).status_code, 409)
        self.pay.assert_not_called()

    def test_common_payment_routes_cannot_bypass_deal_restrictions(self):
        # Нельзя обойти запрет черновика через старое окно платежей даже с ролью владельца.
        prepared = self.prepare().json()
        self.db.update_deal(42, flow="draft")
        self.role = "owner"
        identifier = prepared["agent_transaction_id"]
        self.assertEqual(self.client.post("/integrations/interhub/pay", json={"agent_transaction_id": identifier}).status_code, 409)
        self.assertEqual(self.client.post("/integrations/interhub/vouchers/pay-batch", json={
            "agent_transaction_id": identifier, "batch_id": "d7bd8701-36c2-430e-8580-04256070b950", "quantity": 2,
        }).status_code, 409)
        self.assertEqual(self.client.post("/integrations/interhub/check", json={
            "agent_transaction_id": identifier, "service_id": 9811, "account": "", "amount": 10, "params": {"nominal": "16793"},
        }).status_code, 409)
        self.pay.assert_not_called()
        self.assertEqual(self.db.transactions[identifier]["service_id"], 11125)

    def test_background_confirmation_updates_version_exactly_once(self):
        # Отложенный ответ увеличивает версию и сумму; повторная сверка не создаёт второго начисления.
        self.pay.side_effect = lambda payload: {"success": True, "status": 1, "message": "Ожидание", "raw": {}}
        prepared = self.prepare().json()
        self.assertEqual(self.buy(prepared).json()["state"], "processing")
        self.assertEqual(self.db.deals[42][7], 1)
        self.role = "owner"
        for _ in range(2):
            response = self.client.post("/integrations/interhub/check-status", json={"agent_transaction_id": prepared["agent_transaction_id"]})
            self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.db.deals[42][7], 2)
        self.assertEqual(self.db.purchase_costs[42], 475.04)
        self.publish.assert_called_once_with("deal_updated", 42, "supplier")
        payload = self.client.get("/deals/42/interhub").json()
        self.assertEqual(payload["lock_version"], 2)
        self.assertEqual(payload["purchases"][0]["gift_code"], "RECOVERED")

    def test_late_payment_timeout_cannot_revert_confirmed_code(self):
        # Сверка успела сохранить код раньше, чем исходный сетевой запрос сообщил о таймауте.
        prepared = self.prepare().json()

        def confirmed_before_timeout(payload):
            # Вместо сети используем второй запрос к тому же приложению.
            self.role = "owner"
            response = self.client.post("/integrations/interhub/check-status", json=payload)
            self.assertEqual(response.status_code, 200)
            raise TimeoutError("lost response")

        self.pay.side_effect = confirmed_before_timeout
        result = self.buy(prepared).json()
        self.assertEqual(result["state"], "paid")
        self.assertEqual(result["gift_code"], "RECOVERED")
        self.assertEqual(self.db.deals[42][7], 2)

    def test_return_waits_for_payment_and_then_preserves_vouchers_and_version(self):
        # Возврат не пересекается с оплатой, а после оплаты оставляет код в истории без права купить ещё.
        prepared = self.prepare().json()
        normal_pay = self.pay.side_effect

        def during_pay(payload):
            # Незавершённая оплата блокирует отдельный старый маршрут возврата.
            self.assertEqual(self.client.post("/deals/42/return").status_code, 409)
            return normal_pay(payload)

        self.pay.side_effect = during_pay
        paid = self.buy(prepared).json()
        completed = self.client.put("/deals/42", json={"flow_status_code": "completed", "lock_version": 2, "purchase_cost": 0})
        self.assertEqual(completed.status_code, 200, completed.text)
        returned = self.client.post("/deals/42/return")
        self.assertEqual(returned.status_code, 200, returned.text)
        self.assertEqual(self.db.deals[42][7], 4)
        self.assertEqual(self.prepare().status_code, 409)
        history = self.client.get("/deals/42/interhub").json()
        self.assertFalse(history["purchase_allowed"])
        self.assertEqual(history["purchases"][0]["gift_code"], paid["gift_code"])

    def test_completed_deals_reject_new_preparation_and_payment_for_all_roles_and_regions(self):
        # Завершение между проверкой и оплатой закрывает старое подтверждение, даже с актуальной версией.
        for deal_id, nominal in [(42, "28632"), (44, "16793")]:
            prepared = self.prepare(deal_id, nominal).json()
            completed = self.client.put(f"/deals/{deal_id}", json={"flow_status_code": "completed", "lock_version": 1})
            self.assertEqual(completed.status_code, 200, completed.text)
            for role in ["operator", "manager", "admin", "owner"]:
                self.role = role
                with self.subTest(deal_id=deal_id, role=role):
                    self.assertEqual(self.prepare(deal_id, nominal).status_code, 409)
                    for version in [1, self.db.deals[deal_id][7]]:
                        response = self.buy({**prepared, "lock_version": version}, deal_id)
                        self.assertEqual(response.status_code, 409, response.text)
                        self.assertIn("завершённой", response.json()["detail"])
                    history = self.client.get(f"/deals/{deal_id}/interhub").json()
                    self.assertFalse(history["purchase_allowed"])
                    self.assertEqual(history["nominals"], [])
        self.pay.assert_not_called()

    def test_completed_deal_keeps_paid_code_cost_and_idempotent_retry(self):
        # Скрытое поле отправляет ноль, но завершение сохраняет сумму ваучеров и повторно не платит.
        prepared = self.prepare().json()
        paid = self.buy(prepared).json()
        completed = self.client.put("/deals/42", json={"flow_status_code": "completed", "lock_version": 2, "purchase_cost": 0})
        self.assertEqual(completed.status_code, 200, completed.text)
        self.assertEqual(self.db.purchase_costs[42], 475.04)
        history = self.client.get("/deals/42/interhub").json()
        self.assertFalse(history["purchase_allowed"])
        self.assertEqual(history["purchases"][0]["gift_code"], paid["gift_code"])
        self.assertEqual(self.buy(prepared).json()["gift_code"], paid["gift_code"])
        self.assertEqual(self.pay.call_count, 1)
        self.assertEqual(self.prepare().status_code, 409)

    def test_operator_gets_only_the_service_selected_by_deal_region(self):
        response = self.client.get("/deals/42/interhub")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["service_id"], 11125)
        self.assertEqual([item["title"] for item in payload["nominals"]], ["TRY 250", "TRY 500"])
        self.assertNotIn("TRY 1", [item["title"] for item in payload["nominals"]])

        poland = self.client.get("/deals/44/interhub").json()
        self.assertEqual(poland["service_id"], 9811)
        self.assertEqual([item["title"] for item in poland["nominals"]], ["PLN 100", "PLN 200"])

    def test_rejects_unsupported_region_and_non_service_deal(self):
        self.assertEqual(self.client.get("/deals/43/interhub").status_code, 422)
        self.assertEqual(self.client.get("/deals/45/interhub").status_code, 422)

    def test_second_pay_for_one_deal_returns_same_code_without_second_provider_call(self):
        prepared = self.client.post("/deals/42/interhub/prepare", json={"nominal_id": "28632", "lock_version": self.db.deals[42][7]})
        self.assertEqual(prepared.status_code, 200)
        self.assertEqual(prepared.json()["state"], "checked")

        transaction_id = prepared.json()["agent_transaction_id"]
        first = self.client.post("/deals/42/interhub/pay", json={"agent_transaction_id": transaction_id, "lock_version": self.db.deals[42][7]})
        second = self.client.post("/deals/42/interhub/pay", json={"agent_transaction_id": transaction_id, "lock_version": self.db.deals[42][7]})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["state"], "paid")
        self.assertEqual(first.json()["gift_code"], second.json()["gift_code"])
        self.assertEqual(self.pay.call_count, 1)
        self.assertEqual(self.db.purchase_costs[42], 475.04)

    def test_different_deals_keep_separate_transactions_codes_and_history_links(self):
        # Разные сделки сохраняют свои коды и идентификаторы в общей истории и выгрузке.
        tr_prepared = self.client.post("/deals/42/interhub/prepare", json={"nominal_id": "28632", "lock_version": self.db.deals[42][7]}).json()
        tr_paid = self.client.post("/deals/42/interhub/pay", json={"agent_transaction_id": tr_prepared["agent_transaction_id"], "lock_version": self.db.deals[42][7]}).json()
        self.role = "manager"
        pl_prepared = self.client.post("/deals/44/interhub/prepare", json={"nominal_id": "16793", "lock_version": self.db.deals[44][7]}).json()
        pl_paid = self.client.post("/deals/44/interhub/pay", json={"agent_transaction_id": pl_prepared["agent_transaction_id"], "lock_version": self.db.deals[44][7]}).json()

        self.assertNotEqual(tr_paid["agent_transaction_id"], pl_paid["agent_transaction_id"])
        self.assertNotEqual(tr_paid["gift_code"], pl_paid["gift_code"])
        history = self.client.get("/integrations/interhub/transactions/paid").json()
        self.assertEqual(history["total"], 2)
        self.assertEqual({item["deal_id"] for item in history["items"]}, {42, 44})
        self.assertEqual({item["created_by"] for item in history["items"]}, {"operator", "manager"})
        self.assertEqual({item["agent_transaction_id"] for item in history["items"]},
                         {tr_paid["agent_transaction_id"], pl_paid["agent_transaction_id"]})
        self.assertEqual(history["total_amount"], 950.08)

    def test_one_deal_keeps_every_paid_nominal_and_sums_purchase_cost(self):
        # Повторная покупка того же или другого номинала создаёт новый код, но остаётся в той же сделке.
        first_prepared = self.client.post("/deals/42/interhub/prepare", json={"nominal_id": "28632", "lock_version": self.db.deals[42][7]}).json()
        first_paid = self.client.post(
            "/deals/42/interhub/pay", json={"agent_transaction_id": first_prepared["agent_transaction_id"], "lock_version": self.db.deals[42][7]},
        ).json()
        second_prepared = self.client.post("/deals/42/interhub/prepare", json={"nominal_id": "28633", "lock_version": self.db.deals[42][7]}).json()
        second_paid = self.client.post(
            "/deals/42/interhub/pay", json={"agent_transaction_id": second_prepared["agent_transaction_id"], "lock_version": self.db.deals[42][7]},
        ).json()
        old_retry = self.client.post(
            "/deals/42/interhub/pay", json={"agent_transaction_id": first_prepared["agent_transaction_id"], "lock_version": self.db.deals[42][7]},
        ).json()

        self.assertNotEqual(first_paid["agent_transaction_id"], second_paid["agent_transaction_id"])
        self.assertNotEqual(first_paid["gift_code"], second_paid["gift_code"])
        self.assertEqual(old_retry["gift_code"], first_paid["gift_code"])
        deal = self.client.get("/deals/42/interhub").json()
        self.assertEqual([item["nominal_title"] for item in deal["purchases"]], ["TRY 500", "TRY 250"])
        self.assertEqual(self.db.purchase_costs[42], 950.08)
        self.assertEqual(self.pay.call_count, 2)


if __name__ == "__main__":
    unittest.main()
