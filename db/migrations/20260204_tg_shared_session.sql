BEGIN;

CREATE TABLE IF NOT EXISTS tg.shared_session (
  id              smallint PRIMARY KEY DEFAULT 1,
  phone           text NOT NULL DEFAULT '',
  session_string  text NOT NULL DEFAULT '',
  phone_code_hash text,
  status          text NOT NULL DEFAULT 'pending',
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  last_used_at    timestamptz,
  updated_by_user_id bigint REFERENCES app.users(user_id)
);

INSERT INTO tg.shared_session (id, phone, session_string, phone_code_hash, status, created_at, updated_at, last_used_at)
SELECT 1, phone, session_string, phone_code_hash, status, created_at, updated_at, last_used_at
FROM tg.sessions
ORDER BY updated_at DESC
LIMIT 1
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS tg.contact_notes_shared (
  sender_id  bigint PRIMARY KEY,
  title      text NOT NULL DEFAULT '',
  info       text NOT NULL DEFAULT '',
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by_user_id bigint REFERENCES app.users(user_id)
);

INSERT INTO tg.contact_notes_shared (sender_id, title, info, updated_at)
SELECT sender_id,
       COALESCE(MAX(title), ''),
       COALESCE(MAX(info), ''),
       MAX(updated_at)
FROM tg.contact_notes
GROUP BY sender_id
ON CONFLICT (sender_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS tg.sent_messages (
  message_id bigint NOT NULL,
  chat_id    bigint NOT NULL,
  sent_by_user_id bigint NOT NULL REFERENCES app.users(user_id),
  sent_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (message_id, chat_id)
);

COMMIT;
