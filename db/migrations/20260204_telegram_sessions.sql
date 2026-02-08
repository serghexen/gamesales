BEGIN;

CREATE SCHEMA IF NOT EXISTS tg;

CREATE TABLE IF NOT EXISTS tg.sessions (
  user_id         bigint PRIMARY KEY REFERENCES app.users(user_id) ON DELETE CASCADE,
  phone           text NOT NULL,
  session_string  text NOT NULL DEFAULT '',
  phone_code_hash text,
  status          text NOT NULL DEFAULT 'pending',
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  last_used_at    timestamptz
);

COMMIT;
