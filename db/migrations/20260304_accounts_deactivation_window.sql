-- Деактивация аккаунта с окном повторной активации 183 дня.
ALTER TABLE app.accounts
  ADD COLUMN IF NOT EXISTS is_deactivated boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS deactivated_at timestamptz,
  ADD COLUMN IF NOT EXISTS next_activation_at timestamptz;

-- Индекс для быстрых фильтров подбора аккаунтов в сделки.
CREATE INDEX IF NOT EXISTS ix_accounts_is_deactivated ON app.accounts (is_deactivated);

COMMENT ON COLUMN app.accounts.is_deactivated IS 'Признак деактивации аккаунта';
COMMENT ON COLUMN app.accounts.deactivated_at IS 'Когда аккаунт был деактивирован';
COMMENT ON COLUMN app.accounts.next_activation_at IS 'Когда аккаунт можно повторно активировать';
