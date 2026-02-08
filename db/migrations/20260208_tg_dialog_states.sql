BEGIN;

CREATE TABLE IF NOT EXISTS tg.dialog_states (
  chat_id bigint PRIMARY KEY,
  status text NOT NULL DEFAULT 'new',
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by_user_id bigint REFERENCES app.users(user_id),
  CONSTRAINT ck_tg_dialog_states_status CHECK (status IN ('new', 'accepted', 'archived'))
);

COMMIT;
