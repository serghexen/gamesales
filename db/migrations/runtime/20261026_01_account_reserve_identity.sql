-- Сохраняем постоянную личность резервов; существующие значения и сделки не удаляем.
ALTER TABLE app.account_reserve_claims ADD COLUMN reused_at timestamptz;

CREATE TABLE app.account_reserve_codes (
  reserve_id bigserial PRIMARY KEY,
  account_id bigint NOT NULL REFERENCES app.accounts(account_id),
  reserve_key text NOT NULL,
  value_hash text,
  is_listed boolean NOT NULL DEFAULT true,
  issued_at timestamptz,
  issued_by text,
  consumed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(account_id, reserve_key)
);
CREATE INDEX account_reserve_codes_hash_idx ON app.account_reserve_codes(account_id, value_hash);

INSERT INTO app.account_reserve_codes(account_id, reserve_key, value_hash, created_at)
SELECT account_id, secret_key, encode(sha256(convert_to(secret_value, 'UTF8')), 'hex'), COALESCE(created_at,now())
FROM app.account_secrets WHERE secret_key ~ '^reserve[0-9]+$';

-- Помним даже отсутствующие старые ячейки, чтобы их номера никогда не использовались повторно.
INSERT INTO app.account_reserve_codes(account_id, reserve_key, is_listed)
SELECT account_id, reserve_key, false FROM (
  SELECT account_id, reserve_key FROM app.deal_items WHERE account_id IS NOT NULL
  UNION SELECT account_id, reserve_key FROM app.account_reserve_claims
) old WHERE reserve_key ~ '^reserve[0-9]+$'
ON CONFLICT (account_id, reserve_key) DO NOTHING;

UPDATE app.account_reserve_codes c SET issued_at=a.claimed_at, issued_by=a.claimed_by
FROM app.account_reserve_claims a
WHERE c.account_id=a.account_id AND c.reserve_key=a.reserve_key;

-- Старый UI позволял копировать из сделки без claim; такие значения считаем уже раскрытыми.
UPDATE app.account_reserve_codes c SET issued_at=old.first_at, issued_by='legacy'
FROM (
  SELECT i.account_id, i.reserve_key, min(d.created_at) AS first_at
  FROM app.deal_items i JOIN app.deals d USING(deal_id)
  WHERE d.deal_type_code='rental' AND d.status_code<>'cancelled'
  GROUP BY i.account_id, i.reserve_key
) old WHERE c.account_id=old.account_id AND c.reserve_key=old.reserve_key AND c.issued_at IS NULL;

CREATE TABLE app.account_reserve_events (
  event_id bigserial PRIMARY KEY,
  reserve_id bigint NOT NULL REFERENCES app.account_reserve_codes(reserve_id),
  deal_id bigint REFERENCES app.deals(deal_id),
  event_type text NOT NULL,
  actor text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX account_reserve_events_reserve_idx ON app.account_reserve_events(reserve_id);

COMMENT ON TABLE app.account_reserve_codes IS 'Постоянные ID резервов; значение хранится в account_secrets до завершения сделки';
COMMENT ON TABLE app.account_reserve_events IS 'История выдачи и удаления резервов без самих кодов';
