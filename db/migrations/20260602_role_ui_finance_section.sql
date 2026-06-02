INSERT INTO app.ui_sections(section_code, section_name, sort_order)
VALUES ('finance', 'Финансы', 80)
ON CONFLICT (section_code) DO UPDATE
SET section_name = EXCLUDED.section_name,
    sort_order = EXCLUDED.sort_order;

INSERT INTO app.role_ui_sections(role_code, section_code, can_view, updated_by)
SELECT
  r.code,
  'finance',
  CASE
    WHEN lower(r.code) IN ('admin', 'owner') THEN true
    ELSE false
  END AS can_view,
  'system'
FROM app.user_roles r
ON CONFLICT (role_code, section_code) DO NOTHING;
