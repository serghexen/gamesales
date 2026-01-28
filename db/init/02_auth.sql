CREATE TABLE IF NOT EXISTS app.user_roles (
  code text PRIMARY KEY,
  name text NOT NULL
);
COMMENT ON TABLE app.user_roles IS 'Справочник ролей пользователей';
COMMENT ON COLUMN app.user_roles.code IS 'Код роли';
COMMENT ON COLUMN app.user_roles.name IS 'Название роли';

CREATE TABLE IF NOT EXISTS app.users (
  user_id bigserial PRIMARY KEY,
  username text NOT NULL UNIQUE,
  password_hash text NOT NULL,
  role_code text NOT NULL DEFAULT 'manager' REFERENCES app.user_roles(code),
  created_at timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE app.users IS 'Пользователи системы';
COMMENT ON COLUMN app.users.user_id IS 'Идентификатор пользователя';
COMMENT ON COLUMN app.users.username IS 'Логин пользователя';
COMMENT ON COLUMN app.users.password_hash IS 'Хеш пароля';
COMMENT ON COLUMN app.users.role_code IS 'Роль пользователя';
COMMENT ON COLUMN app.users.created_at IS 'Дата создания пользователя';

INSERT INTO app.user_roles(code, name)
VALUES ('admin','Admin'),('manager','Manager')
ON CONFLICT (code) DO NOTHING;
