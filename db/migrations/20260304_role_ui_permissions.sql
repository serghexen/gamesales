CREATE TABLE IF NOT EXISTS app.ui_sections (
  section_code text PRIMARY KEY,
  section_name text NOT NULL,
  sort_order integer NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS app.role_ui_sections (
  role_code text NOT NULL REFERENCES app.user_roles(code) ON DELETE CASCADE,
  section_code text NOT NULL REFERENCES app.ui_sections(section_code) ON DELETE CASCADE,
  can_view boolean NOT NULL DEFAULT true,
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by text NOT NULL DEFAULT '',
  PRIMARY KEY (role_code, section_code)
);

INSERT INTO app.ui_sections(section_code, section_name, sort_order)
VALUES
  ('deals', 'Сделки', 10),
  ('accounts', 'Аккаунты', 20),
  ('products', 'Товары', 30),
  ('ns-gift', 'NS Gift', 40),
  ('telegram', 'Чаты', 50),
  ('analytics', 'Аналитика', 60),
  ('catalogs', 'Справочники', 70),
  ('users', 'Пользователи', 80),
  ('profile', 'Профиль', 90),
  ('dashboard', 'Дашборд', 100)
ON CONFLICT (section_code) DO UPDATE
SET section_name = EXCLUDED.section_name,
    sort_order = EXCLUDED.sort_order;

INSERT INTO app.role_ui_sections(role_code, section_code, can_view, updated_by)
SELECT
  r.code,
  s.section_code,
  CASE
    WHEN lower(r.code) IN ('admin', 'owner') THEN true
    WHEN s.section_code IN ('analytics', 'catalogs', 'users', 'dashboard') THEN false
    ELSE true
  END AS can_view,
  'system'
FROM app.user_roles r
CROSS JOIN app.ui_sections s
ON CONFLICT (role_code, section_code) DO NOTHING;
