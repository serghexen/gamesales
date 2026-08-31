-- Хранит независимые СБП-платежи CRM, входящие уведомления и отметки просмотра.
CREATE TABLE IF NOT EXISTS app.tbank_sbp_payments (
  payment_id bigserial PRIMARY KEY,
  public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
  created_by_user_id bigint NOT NULL REFERENCES app.users(user_id) ON DELETE RESTRICT,
  created_by_username text NOT NULL,
  buyer text NOT NULL CHECK (char_length(buyer) BETWEEN 1 AND 200),
  description text NOT NULL CHECK (char_length(description) BETWEEN 1 AND 128),
  terminal_key text NOT NULL,
  order_id text NOT NULL UNIQUE CHECK (char_length(order_id) <= 50),
  provider_payment_id text UNIQUE,
  amount bigint NOT NULL CHECK (amount > 0),
  currency text NOT NULL DEFAULT 'RUB' CHECK (currency = 'RUB'),
  state text NOT NULL DEFAULT 'created' CHECK (
    state IN ('created', 'init_pending', 'init_unknown', 'pending', 'confirmed', 'rejected', 'expired', 'cancelled', 'failed')
  ),
  provider_status text NOT NULL DEFAULT '',
  qr_data_url text NOT NULL DEFAULT '',
  last_error text NOT NULL DEFAULT '',
  next_reconcile_at timestamptz,
  reconcile_attempt_count integer NOT NULL DEFAULT 0 CHECK (reconcile_attempt_count >= 0),
  reconcile_lock_token uuid,
  reconcile_locked_until timestamptz,
  expires_at timestamptz,
  confirmed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tbank_sbp_payments_created
  ON app.tbank_sbp_payments(created_at DESC, payment_id DESC);

CREATE INDEX IF NOT EXISTS idx_tbank_sbp_payments_creator_created
  ON app.tbank_sbp_payments(created_by_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tbank_sbp_payments_reconcile
  ON app.tbank_sbp_payments(next_reconcile_at, created_at)
  WHERE state = 'pending';

CREATE TABLE IF NOT EXISTS app.tbank_sbp_payment_events (
  event_id bigserial PRIMARY KEY,
  event_fingerprint text NOT NULL UNIQUE,
  terminal_key text NOT NULL DEFAULT '',
  order_id text NOT NULL DEFAULT '',
  provider_payment_id text NOT NULL DEFAULT '',
  provider_status text NOT NULL DEFAULT '',
  amount bigint,
  signature_valid boolean NOT NULL,
  processing_state text NOT NULL DEFAULT 'received' CHECK (
    processing_state IN ('received', 'processed', 'ignored', 'failed')
  ),
  last_error text NOT NULL DEFAULT '',
  received_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_tbank_sbp_payment_events_order_received
  ON app.tbank_sbp_payment_events(order_id, received_at DESC);

CREATE TABLE IF NOT EXISTS app.tbank_sbp_payment_reads (
  payment_id bigint NOT NULL REFERENCES app.tbank_sbp_payments(payment_id) ON DELETE CASCADE,
  user_id bigint NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
  seen_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (payment_id, user_id)
);
