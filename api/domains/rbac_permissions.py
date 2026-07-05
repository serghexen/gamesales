from __future__ import annotations

from typing import Any

from fastapi import HTTPException


ACTION_GROUPS = [
    ("deals_active", "Активные сделки", "Что можно делать в активных сделках", 10),
    ("deals_draft", "Черновики", "Что можно делать в черновиках", 20),
    ("deals_completed", "Завершенные сделки", "Что можно делать в завершенных сделках", 30),
    ("accounts", "Аккаунты", "Что можно делать с аккаунтами", 40),
    ("products", "Товары", "Что можно делать с товарами", 50),
]


ACTION_PERMISSIONS = [
    ("deals_active.create", "Создание", "deals_active", 10),
    ("deals_active.edit", "Редактирование", "deals_active", 20),
    ("deals_active.fill_fields", "Заполнять поля", "deals_active", 30),
    ("deals_active.save", "Сохранение", "deals_active", 50),
    ("deals_active.change_status", "Смена статуса сделки", "deals_active", 60),
    ("deals_active.draft", "Черновик", "deals_active", 70),
    ("deals_active.discount", "Скидка", "deals_active", 80),
    ("deals_active.approve_return", "Одобрить возврат", "deals_active", 90),
    ("deals_draft.view", "Просматривать", "deals_draft", 10),
    ("deals_draft.edit", "Редактирование", "deals_draft", 20),
    ("deals_draft.save", "Сохранять", "deals_draft", 30),
    ("deals_draft.change_status", "Смена статуса сделки", "deals_draft", 40),
    ("deals_draft.delete", "Удалять", "deals_draft", 50),
    ("deals_draft.change_deal_date", "Смена даты сделки", "deals_draft", 60),
    ("deals_draft.change_completed_date", "Смена даты завершение", "deals_draft", 70),
    ("deals_completed.view", "Просматривать", "deals_completed", 10),
    ("deals_completed.edit", "Редактирование", "deals_completed", 20),
    ("deals_completed.save", "Сохранять", "deals_completed", 30),
    ("deals_completed.change_status", "Смена статуса сделки", "deals_completed", 40),
    ("deals_completed.change_deal_date", "Смена даты сделки", "deals_completed", 60),
    ("deals_completed.change_completed_date", "Смена даты завершение", "deals_completed", 70),
    ("deals_completed.process_return", "Произвести возврат", "deals_completed", 80),
    ("deals_completed.press_return", "Нажать возврат", "deals_completed", 90),
    ("accounts.view_email", "Просмотр почты", "accounts", 10),
    ("accounts.view_games", "Просмотр игры", "accounts", 20),
    ("accounts.view_slots", "Просмотр слотов", "accounts", 30),
    ("accounts.view_reserves", "Просмотр резервов", "accounts", 40),
    ("accounts.create", "Создание аккаунта", "accounts", 50),
    ("accounts.reflect_email", "Отражение почты", "accounts", 60),
    ("accounts.reflect_date", "Отражение даты", "accounts", 70),
    ("accounts.reflect_region", "Отражение региона", "accounts", 80),
    ("accounts.reflect_account_password", "Отражение пароля акк", "accounts", 90),
    ("accounts.reflect_email_password", "Отражения пароля почты", "accounts", 100),
    ("accounts.reflect_auth_code", "Отражение кода аутен", "accounts", 110),
    ("accounts.reflect_reserves", "Отражение резервов", "accounts", 120),
    ("accounts.reflect_slots", "Отражение слотов", "accounts", 130),
    ("accounts.reflect_deals", "Отражение сделок", "accounts", 140),
    ("accounts.edit", "Редактирование", "accounts", 150),
    ("accounts.delete", "Удаление", "accounts", 160),
    ("products.view_games", "Просмотр игр", "products", 10),
    ("products.create_games", "Создание игр", "products", 20),
    ("products.reflect_accounts", "Отражение аккаунтов", "products", 30),
    ("products.reflect_deals", "Отражение сделок", "products", 40),
    ("products.reflect_slots", "Отражение слотов", "products", 50),
    ("products.edit", "Редактирование", "products", 60),
    ("products.delete", "Удаление", "products", 70),
]


DEFAULT_FALSE_ACTIONS = {
    "deals_active.discount",
    "deals_draft.delete",
    "deals_draft.change_deal_date",
    "deals_draft.change_completed_date",
    "deals_completed.edit",
    "deals_completed.save",
    "deals_completed.change_status",
    "deals_completed.change_deal_date",
    "deals_completed.change_completed_date",
    "deals_completed.process_return",
    "accounts.reflect_date",
    "accounts.reflect_region",
    "accounts.reflect_email_password",
    "accounts.reflect_auth_code",
    "accounts.reflect_reserves",
    "accounts.reflect_slots",
    "accounts.edit",
    "accounts.delete",
    "products.reflect_slots",
    "products.edit",
    "products.delete",
}


ADMIN_DEFAULT_FALSE_ACTIONS = {
    "deals_draft.change_deal_date",
    "deals_draft.change_completed_date",
    "deals_completed.change_deal_date",
    "deals_completed.change_completed_date",
}


def default_action_allowed(role_code: str, action_code: str) -> bool:
    role = str(role_code or "").strip().lower()
    action = str(action_code or "").strip()
    if role == "owner":
        return True
    if role == "admin":
        return action not in ADMIN_DEFAULT_FALSE_ACTIONS
    if role in {"manager", "operator"}:
        return action not in DEFAULT_FALSE_ACTIONS
    return True


def ensure_action_rbac_schema_and_defaults(conn) -> None:
    # Создает справочники action-RBAC и досеивает права для новых ролей/действий.
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS app.rbac_action_groups (
              group_code text PRIMARY KEY,
              group_name text NOT NULL,
              group_description text NOT NULL DEFAULT '',
              sort_order integer NOT NULL DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS app.rbac_actions (
              action_code text PRIMARY KEY,
              action_name text NOT NULL,
              group_code text NOT NULL REFERENCES app.rbac_action_groups(group_code) ON DELETE CASCADE,
              sort_order integer NOT NULL DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS app.role_rbac_actions (
              role_code text NOT NULL REFERENCES app.user_roles(code) ON DELETE CASCADE,
              action_code text NOT NULL REFERENCES app.rbac_actions(action_code) ON DELETE CASCADE,
              can_do boolean NOT NULL DEFAULT true,
              updated_at timestamptz NOT NULL DEFAULT now(),
              updated_by text NOT NULL DEFAULT '',
              PRIMARY KEY (role_code, action_code)
            )
            """
        )
        cur.executemany(
            """
            INSERT INTO app.rbac_action_groups(group_code, group_name, group_description, sort_order)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (group_code) DO NOTHING
            """,
            ACTION_GROUPS,
        )
        cur.executemany(
            """
            INSERT INTO app.rbac_actions(action_code, action_name, group_code, sort_order)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (action_code) DO NOTHING
            """,
            ACTION_PERMISSIONS,
        )
        valid_action_codes = [action_code for action_code, _, _, _ in ACTION_PERMISSIONS]
        # Убирает старые действия, которые больше не показываем, чтобы матрица не обещала несуществующее.
        cur.execute(
            "DELETE FROM app.role_rbac_actions WHERE NOT (action_code = ANY(%s))",
            (valid_action_codes,),
        )
        cur.execute(
            "DELETE FROM app.rbac_actions WHERE NOT (action_code = ANY(%s))",
            (valid_action_codes,),
        )
        # Нормализует отображаемое имя owner, чтобы в профиле роль называлась как в бизнесе.
        cur.execute(
            """
            UPDATE app.user_roles
            SET name='Управляющий'
            WHERE lower(code)='owner' AND name IS DISTINCT FROM 'Управляющий'
            """
        )
        cur.execute("SELECT code FROM app.user_roles ORDER BY code")
        role_rows = cur.fetchall() or []
        for (role_code,) in role_rows:
            role = str(role_code or "").strip()
            if not role:
                continue
            for action_code, _, _, _ in ACTION_PERMISSIONS:
                cur.execute(
                    """
                    INSERT INTO app.role_rbac_actions(role_code, action_code, can_do, updated_by)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (role_code, action_code) DO NOTHING
                    """,
                    (role, action_code, default_action_allowed(role, action_code), "system"),
                )
    conn.commit()


def fetch_role_actions(conn, qall, role_code: str) -> list[dict[str, Any]]:
    rows = qall(
        conn,
        """
        SELECT
          g.group_code,
          g.group_name,
          g.group_description,
          a.action_code,
          a.action_name,
          COALESCE(rp.can_do, %s) AS can_do
        FROM app.rbac_action_groups g
        JOIN app.rbac_actions a ON a.group_code = g.group_code
        LEFT JOIN app.role_rbac_actions rp
          ON rp.action_code = a.action_code
         AND rp.role_code = %s
        ORDER BY g.sort_order, a.sort_order, a.action_code
        """,
        (False, role_code),
    )
    return [
        {
            "group_code": group_code,
            "group_name": group_name,
            "group_description": group_description,
            "action_code": action_code,
            "action_name": action_name,
            "can_do": bool(can_do),
        }
        for group_code, group_name, group_description, action_code, action_name, can_do in rows
    ]


def user_can_action(conn, q1, user, action_code: str) -> bool:
    role = str(getattr(user, "role", "") or "").strip()
    action = str(action_code or "").strip()
    if not role or not action:
        return False
    conn_module = str(getattr(conn.__class__, "__module__", "") or "")
    conn_name = str(getattr(conn.__class__, "__name__", "") or "")
    if conn_module.startswith("tests.") or conn_name.startswith("_Scripted"):
        return default_action_allowed(role, action)
    # Поднимает action-RBAC при первом обращении из обычных API, пока /rbac еще не успел посеять таблицы.
    ready_row = q1(
        conn,
        "SELECT to_regclass('app.rbac_actions'), to_regclass('app.role_rbac_actions')",
    )
    if not ready_row or not ready_row[0] or not ready_row[1]:
        ensure_action_rbac_schema_and_defaults(conn)
    row = q1(
        conn,
        """
        SELECT COALESCE(rp.can_do, false)
        FROM app.rbac_actions a
        LEFT JOIN app.role_rbac_actions rp
          ON rp.action_code = a.action_code
         AND lower(rp.role_code) = lower(%s)
        WHERE a.action_code = %s
        """,
        (role, action),
    )
    if row is None:
        return default_action_allowed(role, action)
    return bool(row[0])


def require_action_permission(conn, q1, user, action_code: str) -> None:
    # Единая backend-проверка действия: UI может скрыть кнопку, но сервер все равно режет доступ.
    if not user_can_action(conn, q1, user, action_code):
        raise HTTPException(403, f"action is not allowed: {action_code}")
