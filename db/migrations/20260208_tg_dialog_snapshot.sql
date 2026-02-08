BEGIN;

CREATE TABLE IF NOT EXISTS tg.dialog_snapshot (
  chat_id       bigint PRIMARY KEY,
  title         text NOT NULL DEFAULT '',
  unread_count  integer NOT NULL DEFAULT 0,
  is_group      boolean NOT NULL DEFAULT false,
  is_channel    boolean NOT NULL DEFAULT false,
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tg_dialog_snapshot_updated_at
  ON tg.dialog_snapshot(updated_at DESC);

COMMIT;
