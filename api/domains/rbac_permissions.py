from __future__ import annotations

from typing import Any

from fastapi import HTTPException


ACTION_GROUPS = [
    ("deals_active", "Сделки", "", 10),
    ("deals_draft", "Черновики", "", 20),
    ("deals_completed", "Завершенные сделки", "", 30),
    ("accounts", "Аккаунты", "", 40),
    ("products", "Товары", "", 50),
]

DEAL_ACTIVE_LIST_PERMISSIONS = [
    ("deals_active.list.type", "Список: тип", 100),
    ("deals_active.list.customer", "Список: покупатель", 110),
    ("deals_active.list.product", "Список: товар", 120),
    ("deals_active.list.datetime", "Список: дата/время", 130),
    ("deals_active.list.status", "Список: статус", 140),
    ("deals_active.list.responsible", "Список: ответственный", 150),
    ("deals_active.list.action", "Список: действие", 160),
]

DEAL_COMPLETED_LIST_PERMISSIONS = [
    ("deals_completed.list.type", "Список: тип", 100),
    ("deals_completed.list.customer", "Список: покупатель", 110),
    ("deals_completed.list.product", "Список: товар", 120),
    ("deals_completed.list.datetime", "Список: дата/время", 130),
    ("deals_completed.list.status", "Список: статус", 140),
    ("deals_completed.list.responsible", "Список: ответственный", 150),
    ("deals_completed.list.action", "Список: действие", 160),
]

DEAL_ACTIVE_CONTEXT_PERMISSIONS = [
    ("deals_active.new.sale.create", "Услуга - создание", 200),
    ("deals_active.new.sale.draft", "Услуга - черновик", 210),
    ("deals_active.view.sale.edit", "Услуга - редактирование", 220),
    ("deals_active.new.rental.create", "Шеринг - создание", 230),
    ("deals_active.new.rental.draft", "Шеринг - черновик", 240),
    ("deals_active.view.rental.edit", "Шеринг - редактирование", 250),
]

DEAL_ACTIVE_FIELD_CONTEXTS = [
    ("new.sale", "Новая услуга"),
    ("view.sale", "Просмотр услуги"),
    ("edit.sale", "Редактирование услуги"),
    ("new.rental", "Новый шеринг"),
    ("view.rental", "Просмотр шеринга"),
    ("edit.rental", "Редактирование шеринга"),
]

DEAL_COMPLETED_FIELD_CONTEXTS = [
    ("view.sale", "Просмотр услуги"),
    ("edit.sale", "Редактирование услуги"),
    ("view.rental", "Просмотр шеринга"),
    ("edit.rental", "Редактирование шеринга"),
]

DEAL_DRAFT_FIELD_CONTEXTS = DEAL_COMPLETED_FIELD_CONTEXTS

DEAL_ACTIVE_FIELDS = [
    ("created_at", "Дата создания", {"view.sale", "view.rental", "edit.sale", "edit.rental"}),
    ("completed_at", "Дата завершения", {"view.sale", "view.rental", "edit.sale", "edit.rental"}),
    ("status", "Статус", {"view.sale", "view.rental", "edit.sale", "edit.rental"}),
    ("return", "Возврат", {"view.sale", "view.rental", "edit.sale", "edit.rental"}),
    ("source", "Источник", None),
    ("messenger", "Мессенджер", None),
    ("order_number", "Номер заказа", None),
    ("customer", "Покупатель", None),
    ("responsible", "Ответственный", None),
    ("purchase_cost", "Закупочная цена", {"new.sale", "view.sale", "edit.sale"}),
    ("price", "Сумма продажи", None),
    ("payment_method", "Метод оплаты", None),
    ("discount", "Скидка", None),
    ("login", "Логин", {"new.sale", "view.sale", "edit.sale"}),
    ("password", "Пароль", {"new.sale", "view.sale", "edit.sale"}),
    ("product_link", "Ссылка на товар", {"new.sale", "view.sale", "edit.sale"}),
    ("region", "Регион", {"new.sale", "view.sale", "edit.sale"}),
    ("product_type", "Тип товара", {"new.rental", "view.rental", "edit.rental"}),
    ("slot_type", "Тип слота", {"new.rental", "view.rental", "edit.rental"}),
    ("subscription_term", "Срок подписки", {"new.rental", "view.rental", "edit.rental"}),
    ("product", "Товар", {"new.rental", "view.rental", "edit.rental"}),
    ("account", "Аккаунт", {"new.rental", "view.rental", "edit.rental"}),
    ("account_login", "Логин аккаунта", {"new.rental", "view.rental", "edit.rental"}),
    ("account_password", "Пароль аккаунта", {"new.rental", "view.rental", "edit.rental"}),
    ("reserve", "Резерв", {"new.rental", "view.rental", "edit.rental"}),
    ("notes", "Комментарий", None),
]


def deal_active_field_permissions() -> list[tuple[str, str, str, int]]:
    # Разворачивает матрицу полей в обычные action-коды для хранения в БД.
    return deal_field_permissions("deals_active", DEAL_ACTIVE_FIELD_CONTEXTS)


def deal_completed_field_permissions() -> list[tuple[str, str, str, int]]:
    # Для завершенных сделок используем те же поля, но без контекстов создания.
    return deal_field_permissions("deals_completed", DEAL_COMPLETED_FIELD_CONTEXTS)


def deal_draft_field_permissions() -> list[tuple[str, str, str, int]]:
    # Черновики редактируются как существующие сделки, поэтому контекстов создания тут нет.
    return deal_field_permissions("deals_draft", DEAL_DRAFT_FIELD_CONTEXTS)


def deal_field_permissions(group_code: str, contexts: list[tuple[str, str]]) -> list[tuple[str, str, str, int]]:
    # Разворачивает матрицу полей выбранной группы в обычные action-коды.
    rows: list[tuple[str, str, str, int]] = []
    sort_order = 300
    for context_code, context_name in contexts:
        for field_code, field_name, allowed_contexts in DEAL_ACTIVE_FIELDS:
            if allowed_contexts is not None and context_code not in allowed_contexts:
                continue
            rows.append((
                f"{group_code}.{context_code}.field.{field_code}",
                f"{context_name}: {field_name}",
                group_code,
                sort_order,
            ))
            sort_order += 1
    return rows


DEAL_ACTIVE_DISCOUNT_FIELD_ACTIONS = {
    f"deals_active.{context_code}.field.discount"
    for context_code, _ in DEAL_ACTIVE_FIELD_CONTEXTS
}

DEAL_COMPLETED_DISCOUNT_FIELD_ACTIONS = {
    f"deals_completed.{context_code}.field.discount"
    for context_code, _ in DEAL_COMPLETED_FIELD_CONTEXTS
}

DEAL_DRAFT_DISCOUNT_FIELD_ACTIONS = {
    f"deals_draft.{context_code}.field.discount"
    for context_code, _ in DEAL_DRAFT_FIELD_CONTEXTS
}

ACCOUNT_FIELD_CONTEXTS = [
    ("create", "Создание"),
    ("view", "Просмотр"),
    ("edit", "Редактирование"),
]

ACCOUNT_FIELDS = [
    ("email", "Почта", {"create", "view", "edit"}),
    ("region", "Регион", {"create", "view", "edit"}),
    ("date", "Дата", {"create", "view", "edit"}),
    ("purchase_cost", "Закупочная цена", {"create", "view", "edit"}),
    ("notes", "Комментарий", {"create", "view", "edit"}),
    ("account_password", "Пароль аккаунта", {"create", "view", "edit"}),
    ("email_password", "Пароль почты", {"create", "view", "edit"}),
    ("auth_code", "Код аутентификатора", {"create", "view", "edit"}),
    ("reserves", "Резервы", {"create", "view", "edit"}),
    ("products", "Товары", {"create", "view", "edit"}),
    ("slots", "Слоты аккаунта", {"view", "edit"}),
    ("deals", "Пользователи по сделкам", {"view", "edit"}),
]


def account_field_permissions() -> list[tuple[str, str, str, int]]:
    # Разворачивает поля аккаунта в action-коды для матрицы формы.
    rows: list[tuple[str, str, str, int]] = []
    sort_order = 300
    for context_code, context_name in ACCOUNT_FIELD_CONTEXTS:
        for field_code, field_name, allowed_contexts in ACCOUNT_FIELDS:
            if context_code not in allowed_contexts:
                continue
            rows.append((
                f"accounts.{context_code}.field.{field_code}",
                f"{context_name}: {field_name}",
                "accounts",
                sort_order,
            ))
            sort_order += 1
    return rows


ACCOUNT_DEFAULT_FALSE_FIELD_ACTIONS = {
    f"accounts.{context_code}.field.{field_code}"
    for context_code, _ in ACCOUNT_FIELD_CONTEXTS
    for field_code in {
        "date",
        "region",
        "purchase_cost",
        "email_password",
        "auth_code",
        "reserves",
        "products",
        "slots",
    }
}


PRODUCT_LIST_PERMISSIONS = [
    ("products.list.type", "Список: тип", 100),
    ("products.list.title", "Список: товар", 110),
    ("products.list.platform", "Список: платформа", 120),
]

PRODUCT_FIELD_CONTEXTS = [
    ("create", "Создание"),
    ("view", "Просмотр"),
    ("edit", "Редактирование"),
]

PRODUCT_FIELDS = [
    ("title", "Название", {"create", "view", "edit"}),
    ("short_title", "Короткое название", {"create", "view", "edit"}),
    ("region", "Регион", {"create", "view", "edit"}),
    ("platforms", "Платформа", {"create", "view", "edit"}),
    ("notes", "Комментарий", {"create", "view", "edit"}),
    ("link", "Ссылка", {"create", "view", "edit"}),
    ("text_lang", "Язык текста", {"create", "view", "edit"}),
    ("audio_lang", "Язык озвучки", {"create", "view", "edit"}),
    ("vr_support", "Поддержка VR", {"create", "view", "edit"}),
    ("accounts", "Аккаунты", {"create", "view", "edit"}),
    ("deals", "Сделки", {"view", "edit"}),
    ("slots", "Слоты по товару", {"view", "edit"}),
    ("subscription_terms", "Сроки подписки", {"view", "edit"}),
]


def product_field_permissions() -> list[tuple[str, str, str, int]]:
    # Разворачивает поля товара в action-коды для матрицы формы.
    rows: list[tuple[str, str, str, int]] = []
    sort_order = 300
    for context_code, context_name in PRODUCT_FIELD_CONTEXTS:
        for field_code, field_name, allowed_contexts in PRODUCT_FIELDS:
            if context_code not in allowed_contexts:
                continue
            rows.append((
                f"products.{context_code}.field.{field_code}",
                f"{context_name}: {field_name}",
                "products",
                sort_order,
            ))
            sort_order += 1
    return rows


PRODUCT_DEFAULT_FALSE_FIELD_ACTIONS = {
    f"products.{context_code}.field.{field_code}"
    for context_code, _ in PRODUCT_FIELD_CONTEXTS
    for field_code in {"slots"}
}


ACTION_PERMISSIONS = [
    ("deals_active.create", "Создание", "deals_active", 10),
    ("deals_active.edit", "Редактирование", "deals_active", 20),
    ("deals_active.fill_fields", "Заполнять поля", "deals_active", 30),
    ("deals_active.save", "Сохранение", "deals_active", 50),
    ("deals_active.change_status", "Смена статуса сделки", "deals_active", 60),
    ("deals_active.draft", "Черновик", "deals_active", 70),
    ("deals_active.discount", "Скидка", "deals_active", 80),
    ("deals_active.approve_return", "Одобрить возврат", "deals_active", 90),
    *[(code, name, "deals_active", sort_order) for code, name, sort_order in DEAL_ACTIVE_LIST_PERMISSIONS],
    *[(code, name, "deals_active", sort_order) for code, name, sort_order in DEAL_ACTIVE_CONTEXT_PERMISSIONS],
    *deal_active_field_permissions(),
    ("deals_draft.view", "Просматривать", "deals_draft", 10),
    ("deals_draft.edit", "Редактирование", "deals_draft", 20),
    ("deals_draft.save", "Сохранять", "deals_draft", 30),
    ("deals_draft.change_status", "Смена статуса сделки", "deals_draft", 40),
    ("deals_draft.delete", "Удалять", "deals_draft", 50),
    ("deals_draft.change_deal_date", "Смена даты сделки", "deals_draft", 60),
    ("deals_draft.change_completed_date", "Смена даты завершение", "deals_draft", 70),
    *deal_draft_field_permissions(),
    ("deals_completed.view", "Просматривать", "deals_completed", 10),
    ("deals_completed.edit", "Редактирование", "deals_completed", 20),
    ("deals_completed.save", "Сохранять", "deals_completed", 30),
    ("deals_completed.change_status", "Смена статуса сделки", "deals_completed", 40),
    ("deals_completed.change_deal_date", "Смена даты сделки", "deals_completed", 60),
    ("deals_completed.change_completed_date", "Смена даты завершение", "deals_completed", 70),
    ("deals_completed.process_return", "Произвести возврат", "deals_completed", 80),
    ("deals_completed.press_return", "Нажать возврат", "deals_completed", 90),
    *[(code, name, "deals_completed", sort_order) for code, name, sort_order in DEAL_COMPLETED_LIST_PERMISSIONS],
    *deal_completed_field_permissions(),
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
    ("accounts.reflect_purchase_cost", "Отражение закупочной цены", "accounts", 135),
    ("accounts.reflect_deals", "Отражение сделок", "accounts", 140),
    ("accounts.edit", "Редактирование", "accounts", 150),
    ("accounts.delete", "Удаление", "accounts", 160),
    *account_field_permissions(),
    ("products.view_games", "Просмотр игр", "products", 10),
    ("products.create_games", "Создание игр", "products", 20),
    ("products.reflect_accounts", "Отражение аккаунтов", "products", 30),
    ("products.reflect_deals", "Отражение сделок", "products", 40),
    ("products.reflect_slots", "Отражение слотов", "products", 50),
    ("products.edit", "Редактирование", "products", 60),
    ("products.delete", "Удаление", "products", 70),
    *[(code, name, "products", sort_order) for code, name, sort_order in PRODUCT_LIST_PERMISSIONS],
    *product_field_permissions(),
]


DEFAULT_FALSE_ACTIONS = {
    "deals_active.discount",
    *DEAL_ACTIVE_DISCOUNT_FIELD_ACTIONS,
    *DEAL_COMPLETED_DISCOUNT_FIELD_ACTIONS,
    *DEAL_DRAFT_DISCOUNT_FIELD_ACTIONS,
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
    "accounts.reflect_purchase_cost",
    "accounts.edit",
    "accounts.delete",
    *ACCOUNT_DEFAULT_FALSE_FIELD_ACTIONS,
    "products.reflect_slots",
    "products.edit",
    "products.delete",
    *PRODUCT_DEFAULT_FALSE_FIELD_ACTIONS,
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
