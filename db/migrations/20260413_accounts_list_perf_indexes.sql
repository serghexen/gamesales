-- Ускоряет список аккаунтов: агрегации подписок и выборки связей account_assets.

CREATE INDEX IF NOT EXISTS idx_subscription_terms_active_account_product_valid_until
  ON app.subscription_terms(account_id, product_id, valid_until)
  WHERE is_archived IS NOT TRUE;

CREATE INDEX IF NOT EXISTS idx_account_assets_product_account_live
  ON app.account_assets(product_id, account_id)
  WHERE asset_type_code IN ('game', 'subscription');

CREATE INDEX IF NOT EXISTS idx_account_assets_account_product_live
  ON app.account_assets(account_id, product_id)
  WHERE asset_type_code IN ('game', 'subscription');

