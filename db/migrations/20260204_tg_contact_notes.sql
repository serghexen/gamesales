BEGIN;

CREATE TABLE IF NOT EXISTS tg.contact_notes (
  user_id    bigint NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
  sender_id  bigint NOT NULL,
  title      text NOT NULL DEFAULT '',
  info       text NOT NULL DEFAULT '',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, sender_id)
);

COMMIT;
