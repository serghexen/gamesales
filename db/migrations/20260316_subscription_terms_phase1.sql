BEGIN;

-- Справочник сроков подписок: конкретный аккаунт + дата окончания по базовому товару подписки.
CREATE TABLE IF NOT EXISTS app.subscription_terms (
  term_id bigserial PRIMARY KEY,
  product_id bigint NOT NULL REFERENCES app.subscription_products(product_id) ON DELETE CASCADE,
  account_id bigint NOT NULL REFERENCES app.accounts(account_id) ON DELETE RESTRICT,
  valid_until date NOT NULL,
  notes text,
  is_archived boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE app.subscription_terms IS 'Сроки подписок по базовому товару';
COMMENT ON COLUMN app.subscription_terms.product_id IS 'Базовый товар типа subscription';
COMMENT ON COLUMN app.subscription_terms.account_id IS 'Аккаунт, на котором действует срок подписки';
COMMENT ON COLUMN app.subscription_terms.valid_until IS 'Дата окончания срока';

CREATE INDEX IF NOT EXISTS idx_subscription_terms_product ON app.subscription_terms(product_id, valid_until);
CREATE INDEX IF NOT EXISTS idx_subscription_terms_account ON app.subscription_terms(account_id);
CREATE INDEX IF NOT EXISTS idx_subscription_terms_archived ON app.subscription_terms(is_archived);

-- Привязываем сделки и слот-назначения к конкретному сроку подписки.
ALTER TABLE app.deal_items
  ADD COLUMN IF NOT EXISTS subscription_term_id bigint REFERENCES app.subscription_terms(term_id) ON DELETE RESTRICT;

ALTER TABLE app.account_slot_assignments
  ADD COLUMN IF NOT EXISTS subscription_term_id bigint REFERENCES app.subscription_terms(term_id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_deal_items_subscription_term_id ON app.deal_items(subscription_term_id);
CREATE INDEX IF NOT EXISTS idx_slot_assignments_subscription_term_id ON app.account_slot_assignments(subscription_term_id);

-- Один срок подписки не должен быть одновременно занят в нескольких активных назначениях.
CREATE UNIQUE INDEX IF NOT EXISTS uq_slot_assignments_active_subscription_term
  ON app.account_slot_assignments(subscription_term_id)
  WHERE subscription_term_id IS NOT NULL AND released_at IS NULL;

COMMIT;
