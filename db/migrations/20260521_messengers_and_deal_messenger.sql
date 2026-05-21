BEGIN;

CREATE TABLE IF NOT EXISTS app.messengers (
  messenger_id bigserial PRIMARY KEY,
  code text NOT NULL,
  name text NOT NULL,
  is_archived boolean NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS ix_messengers_archived ON app.messengers (is_archived);
CREATE INDEX IF NOT EXISTS ix_messengers_code ON app.messengers (code);

ALTER TABLE app.deals
  ADD COLUMN IF NOT EXISTS messenger_id bigint REFERENCES app.messengers(messenger_id);

CREATE INDEX IF NOT EXISTS ix_deals_messenger_id ON app.deals (messenger_id);

COMMIT;
