from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from .rbac_permissions import (
    ACTION_PERMISSIONS,
    ensure_action_rbac_schema_and_defaults,
    fetch_role_actions,
)


class RoleSectionPermissionIn(BaseModel):
    section_code: str
    can_view: bool


class RoleSectionPermissionsUpdateIn(BaseModel):
    items: list[RoleSectionPermissionIn]


class RoleActionPermissionIn(BaseModel):
    action_code: str
    can_do: bool


class RoleActionPermissionsUpdateIn(BaseModel):
    items: list[RoleActionPermissionIn]


def mount_rbac_routes(
    app,
    *,
    DB_DSN,
    psycopg,
    q1,
    qall,
    exec1,
    get_current_user,
    require_role,
):
    # Справочник UI-разделов, которыми можно управлять из ролевой модели.
    UI_SECTIONS = [
        ("deals", "Сделки", 10),
        ("accounts", "Аккаунты", 20),
        ("products", "Товары", 30),
        ("ns-gift", "Магазин", 40),
        ("catalogs", "Справочники", 50),
        ("finance", "Финансы", 60),
        ("users", "Пользователи", 70),
        ("dashboard", "Дашборд", 80),
        ("telegram", "Чаты", 90)
    ]

    # Возвращает дефолтную видимость раздела для роли, если явная настройка еще не задана.
    def default_section_visibility(role_code: str, section_code: str) -> bool:
        role = str(role_code or "").strip().lower()
        section = str(section_code or "").strip().lower()
        if role in {"admin", "owner"}:
            return True
        if section in {"catalogs", "finance", "users", "dashboard"}:
            return False
        return True

    # Определяет обрыв соединения с БД, при котором можно безопасно один раз повторить RBAC-запрос.
    def is_retryable_rbac_connection_error(exc: Exception) -> bool:
        text = str(exc or "").lower()
        return (
            "server closed the connection unexpectedly" in text
            or "consuming input failed" in text
            or "terminating connection due to administrator command" in text
            or "connection not open" in text
        )

    # Открывает соединение, готовит RBAC-справочники и повторяет запрос при протухшем коннекте.
    def run_rbac_operation(operation):
        attempts = 4
        for attempt in range(attempts):
            try:
                with psycopg.connect(DB_DSN) as conn:
                    ensure_rbac_schema_and_defaults(conn)
                    return operation(conn)
            except Exception as exc:
                if attempt + 1 >= attempts or not is_retryable_rbac_connection_error(exc):
                    raise
        raise RuntimeError("RBAC operation failed")

    # Гарантирует наличие RBAC-таблиц и дефолтных значений для всех ролей и разделов.
    def ensure_rbac_schema_and_defaults(conn) -> None:
        with conn.cursor() as cur:
            # Не трогает справочники на каждом чтении, если матрица уже полностью посеяна.
            cur.execute(
                """
                SELECT
                  to_regclass('app.ui_sections'),
                  to_regclass('app.role_ui_sections'),
                  to_regclass('app.rbac_actions'),
                  to_regclass('app.role_rbac_actions')
                """
            )
            table_row = cur.fetchone()
            tables_ready = table_row and all(table_row)
            if tables_ready:
                cur.execute("SELECT count(*) FROM app.user_roles")
                role_count = int((cur.fetchone() or [0])[0] or 0)
                cur.execute("SELECT count(*) FROM app.ui_sections")
                section_count = int((cur.fetchone() or [0])[0] or 0)
                cur.execute("SELECT count(*) FROM app.role_ui_sections")
                section_perm_count = int((cur.fetchone() or [0])[0] or 0)
                cur.execute("SELECT count(*) FROM app.rbac_actions")
                action_count = int((cur.fetchone() or [0])[0] or 0)
                cur.execute("SELECT count(*) FROM app.role_rbac_actions")
                action_perm_count = int((cur.fetchone() or [0])[0] or 0)
                cur.execute("SELECT count(*) FROM app.ui_sections WHERE section_code = 'analytics'")
                stale_analytics_section_count = int((cur.fetchone() or [0])[0] or 0)
                cur.execute(
                    "SELECT count(*) FROM app.rbac_actions WHERE NOT (action_code = ANY(%s))",
                    ([action_code for action_code, _, _, _ in ACTION_PERMISSIONS],),
                )
                stale_action_count = int((cur.fetchone() or [0])[0] or 0)
                if (
                    role_count > 0
                    and section_count >= len(UI_SECTIONS)
                    and section_perm_count >= role_count * len(UI_SECTIONS)
                    and action_count >= len(ACTION_PERMISSIONS)
                    and action_perm_count >= role_count * len(ACTION_PERMISSIONS)
                    and stale_analytics_section_count == 0
                    and stale_action_count == 0
                ):
                    return
        exec1(
            conn,
            """
            CREATE TABLE IF NOT EXISTS app.ui_sections (
              section_code text PRIMARY KEY,
              section_name text NOT NULL,
              sort_order integer NOT NULL DEFAULT 0
            )
            """,
        )
        exec1(
            conn,
            """
            CREATE TABLE IF NOT EXISTS app.role_ui_sections (
              role_code text NOT NULL REFERENCES app.user_roles(code) ON DELETE CASCADE,
              section_code text NOT NULL REFERENCES app.ui_sections(section_code) ON DELETE CASCADE,
              can_view boolean NOT NULL DEFAULT true,
              updated_at timestamptz NOT NULL DEFAULT now(),
              updated_by text NOT NULL DEFAULT '',
              PRIMARY KEY (role_code, section_code)
            )
            """,
        )
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO app.ui_sections(section_code, section_name, sort_order)
                VALUES (%s, %s, %s)
                ON CONFLICT (section_code) DO NOTHING
                """,
                UI_SECTIONS,
            )
            # Удаляем старый раздел аналитики из RBAC, чтобы он не возвращался в матрицу доступов.
            cur.execute("DELETE FROM app.ui_sections WHERE section_code = 'analytics'")
            cur.execute("SELECT code FROM app.user_roles ORDER BY code")
            role_rows = cur.fetchall() or []
            for (role_code,) in role_rows:
                role = str(role_code or "").strip()
                if not role:
                    continue
                for section_code, _, _ in UI_SECTIONS:
                    cur.execute(
                        """
                        INSERT INTO app.role_ui_sections(role_code, section_code, can_view, updated_by)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (role_code, section_code) DO NOTHING
                        """,
                        (role, section_code, default_section_visibility(role, section_code), "system"),
                    )
        ensure_action_rbac_schema_and_defaults(conn)

    # Читает права роли по разделам в стабильной сортировке.
    def fetch_role_sections(conn, role_code: str) -> list[dict[str, Any]]:
        rows = qall(
            conn,
            """
            SELECT
              s.section_code,
              s.section_name,
              COALESCE(rp.can_view, %s) AS can_view
            FROM app.ui_sections s
            LEFT JOIN app.role_ui_sections rp
              ON rp.section_code = s.section_code
             AND rp.role_code = %s
            ORDER BY s.sort_order, s.section_code
            """,
            (False, role_code),
        )
        result: list[dict[str, Any]] = []
        for section_code, section_name, can_view in rows:
            result.append(
                {
                    "section_code": section_code,
                    "section_name": section_name,
                    "can_view": bool(can_view),
                }
            )
        return result

    @app.get("/rbac/ui-sections")
    def list_ui_sections(user=Depends(get_current_user)):
        def load_sections(conn):
            rows = qall(
                conn,
                "SELECT section_code, section_name, sort_order FROM app.ui_sections ORDER BY sort_order, section_code",
            )
            return [
                {"section_code": r0, "section_name": r1, "sort_order": int(r2 or 0)}
                for (r0, r1, r2) in rows
            ]
        return run_rbac_operation(load_sections)

    @app.get("/rbac/my-sections")
    def get_my_sections(user=Depends(get_current_user)):
        role_code = str(getattr(user, "role", "") or "").strip()
        if not role_code:
            raise HTTPException(400, "Role is not defined in token")
        return run_rbac_operation(lambda conn: {"role_code": role_code, "items": fetch_role_sections(conn, role_code)})

    @app.get("/rbac/my-permissions")
    def get_my_permissions(user=Depends(get_current_user)):
        role_code = str(getattr(user, "role", "") or "").strip()
        if not role_code:
            raise HTTPException(400, "Role is not defined in token")
        def load_my_permissions(conn):
            sections = fetch_role_sections(conn, role_code)
            actions = fetch_role_actions(conn, qall, role_code)
            return {"role_code": role_code, "sections": sections, "actions": actions}
        return run_rbac_operation(load_my_permissions)

    @app.get("/rbac/roles/{role_code}/sections")
    def get_role_sections(role_code: str, user=Depends(require_role("admin", "owner"))):
        role = str(role_code or "").strip().lower()
        if not role:
            raise HTTPException(400, "role_code is required")
        def load_role_sections(conn):
            role_row = q1(conn, "SELECT code FROM app.user_roles WHERE lower(code)=lower(%s)", (role,))
            if not role_row:
                raise HTTPException(404, "Role not found")
            rows = fetch_role_sections(conn, str(role_row[0]))
            return {"role_code": str(role_row[0]), "items": rows}
        return run_rbac_operation(load_role_sections)

    @app.get("/rbac/roles/{role_code}/actions")
    def get_role_actions(role_code: str, user=Depends(require_role("admin", "owner"))):
        role = str(role_code or "").strip().lower()
        if not role:
            raise HTTPException(400, "role_code is required")
        def load_role_actions(conn):
            role_row = q1(conn, "SELECT code FROM app.user_roles WHERE lower(code)=lower(%s)", (role,))
            if not role_row:
                raise HTTPException(404, "Role not found")
            rows = fetch_role_actions(conn, qall, str(role_row[0]))
            return {"role_code": str(role_row[0]), "items": rows}
        return run_rbac_operation(load_role_actions)

    @app.put("/rbac/roles/{role_code}/sections")
    def save_role_sections(
        role_code: str,
        payload: RoleSectionPermissionsUpdateIn,
        user=Depends(require_role("admin", "owner")),
    ):
        role = str(role_code or "").strip().lower()
        if not role:
            raise HTTPException(400, "role_code is required")
        items = list(payload.items or [])
        if not items:
            raise HTTPException(400, "items is required")
        actor = str(getattr(user, "username", "") or "").strip() or "system"
        def save_sections(conn):
            role_row = q1(conn, "SELECT code FROM app.user_roles WHERE lower(code)=lower(%s)", (role,))
            if not role_row:
                raise HTTPException(404, "Role not found")
            target_role = str(role_row[0])
            section_rows = qall(conn, "SELECT section_code FROM app.ui_sections")
            known_sections = {str(row[0]) for row in (section_rows or [])}
            with conn.cursor() as cur:
                for item in items:
                    section_code = str(item.section_code or "").strip()
                    if section_code not in known_sections:
                        raise HTTPException(400, f"Unknown section_code: {section_code}")
                    cur.execute(
                        """
                        INSERT INTO app.role_ui_sections(role_code, section_code, can_view, updated_at, updated_by)
                        VALUES (%s, %s, %s, now(), %s)
                        ON CONFLICT (role_code, section_code) DO UPDATE
                          SET can_view=EXCLUDED.can_view,
                              updated_at=now(),
                              updated_by=EXCLUDED.updated_by
                        """,
                        (target_role, section_code, bool(item.can_view), actor),
                    )
            conn.commit()
            rows = fetch_role_sections(conn, target_role)
            return {"ok": True, "role_code": target_role, "items": rows}
        return run_rbac_operation(save_sections)

    @app.put("/rbac/roles/{role_code}/actions")
    def save_role_actions(
        role_code: str,
        payload: RoleActionPermissionsUpdateIn,
        user=Depends(require_role("admin", "owner")),
    ):
        role = str(role_code or "").strip().lower()
        if not role:
            raise HTTPException(400, "role_code is required")
        items = list(payload.items or [])
        if not items:
            raise HTTPException(400, "items is required")
        actor = str(getattr(user, "username", "") or "").strip() or "system"
        def save_actions(conn):
            role_row = q1(conn, "SELECT code FROM app.user_roles WHERE lower(code)=lower(%s)", (role,))
            if not role_row:
                raise HTTPException(404, "Role not found")
            target_role = str(role_row[0])
            action_rows = qall(conn, "SELECT action_code FROM app.rbac_actions")
            known_actions = {str(row[0]) for row in (action_rows or [])}
            with conn.cursor() as cur:
                for item in items:
                    action_code = str(item.action_code or "").strip()
                    if action_code not in known_actions:
                        raise HTTPException(400, f"Unknown action_code: {action_code}")
                    cur.execute(
                        """
                        INSERT INTO app.role_rbac_actions(role_code, action_code, can_do, updated_at, updated_by)
                        VALUES (%s, %s, %s, now(), %s)
                        ON CONFLICT (role_code, action_code) DO UPDATE
                          SET can_do=EXCLUDED.can_do,
                              updated_at=now(),
                              updated_by=EXCLUDED.updated_by
                        """,
                        (target_role, action_code, bool(item.can_do), actor),
                    )
            conn.commit()
            rows = fetch_role_actions(conn, qall, target_role)
            return {"ok": True, "role_code": target_role, "items": rows}
        return run_rbac_operation(save_actions)
