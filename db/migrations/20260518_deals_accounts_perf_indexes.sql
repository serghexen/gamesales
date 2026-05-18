-- Индексы под рабочие запросы сделок/аккаунтов:
-- 1) поиск customer по nickname,
-- 2) проверка активного slot-assignment по deal_item_id,
-- 3) join/filter deal_items по deal_id/account_id,
-- 4) базовый фильтр списка сделок по статусам/дате.

CREATE INDEX IF NOT EXISTS idx_customers_nickname
  ON app.customers(nickname);

CREATE INDEX IF NOT EXISTS idx_asa_deal_item_active
  ON app.account_slot_assignments(deal_item_id)
  WHERE released_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_deal_items_deal_id
  ON app.deal_items(deal_id);

CREATE INDEX IF NOT EXISTS idx_deal_items_account_id
  ON app.deal_items(account_id);

CREATE INDEX IF NOT EXISTS idx_deals_status_flow_created_deal
  ON app.deals(status_code, flow_status_code, created_at, deal_id);
