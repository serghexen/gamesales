-- migrate:no-transaction
-- Хранит оплаченный ключ до его атомарного закрепления за заказом Ozon или Яндекс Маркета.

ALTER TABLE app.marketplace_ozon_digital_supplier_attempts
  ADD COLUMN IF NOT EXISTS gift_code text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS code_applied_at timestamptz,
  ADD COLUMN IF NOT EXISTS finalization_error text NOT NULL DEFAULT '';

ALTER TABLE app.marketplace_yandex_digital_supplier_attempts
  ADD COLUMN IF NOT EXISTS gift_code text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS code_applied_at timestamptz,
  ADD COLUMN IF NOT EXISTS finalization_error text NOT NULL DEFAULT '';

-- Восстанавливает ключи уже оплаченных операций из общего журнала InterHub.
UPDATE app.marketplace_ozon_digital_supplier_attempts AS attempt
SET gift_code=COALESCE(NULLIF(attempt.gift_code, ''), transaction.gift_code),
    code_applied_at=CASE
      WHEN orders.delivered_codes @> jsonb_build_array(transaction.gift_code) THEN COALESCE(attempt.code_applied_at, attempt.updated_at)
      ELSE attempt.code_applied_at
    END
FROM app.interhub_transactions AS transaction,
     app.marketplace_ozon_digital_orders AS orders
WHERE transaction.agent_transaction_id=attempt.agent_transaction_id
  AND orders.id=attempt.order_id
  AND attempt.state='paid'
  AND transaction.gift_code<>''
  AND (attempt.gift_code='' OR attempt.code_applied_at IS NULL);

UPDATE app.marketplace_yandex_digital_supplier_attempts AS attempt
SET gift_code=COALESCE(NULLIF(attempt.gift_code, ''), transaction.gift_code),
    code_applied_at=CASE
      WHEN delivery.delivered_codes @> jsonb_build_array(transaction.gift_code) THEN COALESCE(attempt.code_applied_at, attempt.updated_at)
      ELSE attempt.code_applied_at
    END
FROM app.interhub_transactions AS transaction,
     app.marketplace_yandex_digital_deliveries AS delivery
WHERE transaction.agent_transaction_id=attempt.agent_transaction_id
  AND delivery.id=attempt.delivery_id
  AND attempt.state='paid'
  AND transaction.gift_code<>''
  AND (attempt.gift_code='' OR attempt.code_applied_at IS NULL);

-- Paid без ключа остается заблокированным и снова проверяется у InterHub вместо повторной покупки.
UPDATE app.marketplace_ozon_digital_supplier_attempts
SET next_status_check_at=COALESCE(next_status_check_at, now())
WHERE state='paid' AND code_applied_at IS NULL AND gift_code='';

UPDATE app.marketplace_yandex_digital_supplier_attempts
SET next_status_check_at=COALESCE(next_status_check_at, now())
WHERE state='paid' AND code_applied_at IS NULL AND gift_code='';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ozon_supplier_attempts_paid_unapplied
  ON app.marketplace_ozon_digital_supplier_attempts(updated_at, id)
  WHERE state='paid' AND code_applied_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_yandex_supplier_attempts_paid_unapplied
  ON app.marketplace_yandex_digital_supplier_attempts(updated_at, id)
  WHERE state='paid' AND code_applied_at IS NULL;
