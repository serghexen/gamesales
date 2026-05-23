from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import Depends, HTTPException

from .deals_models import RentalCreate, DealCreate, DealUpdate, DealListItem, DealListOut


def mount_deals_routes(
    app,
    *,
    DB_DSN,
    psycopg,
    q1,
    qall,
    exec1,
    now_utc,
    validate_date_in_range,
    validate_date_range,
    ensure_account_exists,
    ensure_source_exists,
    ensure_account_allows_slot_type,
    get_platform_id,
    get_region_id,
    get_account_slot_free,
    ensure_customer,
    get_slot_type,
    account_has_ps4,
    release_slot_assignment,
    build_deals_filters,
    slots_summary,
    get_current_user,
    publish_deal_event=None,
):
    # Нормализуем текстовые поля клиента, чтобы в БД не попадали пустые строки.
    def normalize_customer_field(value: Optional[str]) -> Optional[str]:
        normalized = (value or "").strip()
        return normalized or None

    # Нормализует ключ резерва к формату reserveN; если значение невалидно, возвращает None.
    def normalize_reserve_key(value: Optional[str]) -> Optional[str]:
        raw = (value or "").strip().lower()
        if not raw:
            return None
        if not raw.startswith("reserve"):
            return None
        suffix = raw.replace("reserve", "", 1).strip()
        if not suffix.isdigit():
            return None
        return f"reserve{int(suffix)}"

    # Возвращает резервы аккаунта в виде пар (reserve_key, decoded_value), отсортированные по номеру.
    def list_account_reserves(conn, account_id: int):
        rows = qall(
            conn,
            """
            SELECT secret_key, secret_value
            FROM app.account_secrets
            WHERE account_id=%s
              AND secret_key LIKE 'reserve%%'
            ORDER BY secret_key
            """,
            (account_id,),
        )
        parsed = []
        for secret_key, secret_value in rows:
            key = normalize_reserve_key(secret_key)
            if not key:
                continue
            # В БД секреты уже хранятся в base64; пустые значения резервами не считаем.
            value = str(secret_value or "").strip()
            if not value:
                continue
            parsed.append((key, value))
        parsed.sort(key=lambda item: int(item[0].replace("reserve", "", 1)))
        return parsed

    # Возвращает множество уже занятых reserve_key по аккаунту в rental-сделках.
    def get_used_reserve_keys(conn, account_id: int, *, exclude_deal_id: Optional[int] = None):
        if exclude_deal_id is None:
            rows = qall(
                conn,
                """
                SELECT DISTINCT di.reserve_key
                FROM app.deal_items di
                JOIN app.deals d ON d.deal_id = di.deal_id
                WHERE d.deal_type_code='rental'
                  AND di.account_id=%s
                  AND di.reserve_key IS NOT NULL
                  AND d.status_code <> 'cancelled'
                """,
                (account_id,),
            )
        else:
            rows = qall(
                conn,
                """
                SELECT DISTINCT di.reserve_key
                FROM app.deal_items di
                JOIN app.deals d ON d.deal_id = di.deal_id
                WHERE d.deal_type_code='rental'
                  AND di.account_id=%s
                  AND di.reserve_key IS NOT NULL
                  AND d.status_code <> 'cancelled'
                  AND d.deal_id <> %s
                """,
                (account_id, exclude_deal_id),
            )
        return {normalize_reserve_key(row[0]) for row in rows if normalize_reserve_key(row[0])}

    # Выбирает первый свободный резерв аккаунта; если свободных нет, возвращает None.
    def pick_first_free_reserve_key(conn, account_id: int, *, exclude_deal_id: Optional[int] = None) -> Optional[str]:
        reserves = list_account_reserves(conn, account_id)
        if not reserves:
            return None
        used_keys = get_used_reserve_keys(conn, account_id, exclude_deal_id=exclude_deal_id)
        for reserve_key, _ in reserves:
            if reserve_key not in used_keys:
                return reserve_key
        return None

    # Проверяет привилегии пользователя для операций с завершенными/возвратными сделками.
    def has_completed_deal_access(user) -> bool:
        role = (getattr(user, "role", "") or "").strip().lower()
        username = (getattr(user, "username", "") or "").strip().lower()
        return role in {"admin", "owner"} or username in {"admin", "owner"}

    # Находит owner и возвращает отображаемое имя для поля "Ответственный".
    def resolve_owner_responsible_name(conn) -> str:
        row = q1(
            conn,
            """
            SELECT name, username
            FROM app.users
            WHERE lower(role_code)='owner'
            ORDER BY user_id ASC
            LIMIT 1
            """,
        )
        owner_name = str(row[0]).strip() if row and row[0] is not None else ""
        owner_username = str(row[1]).strip() if row and len(row) > 1 and row[1] is not None else ""
        resolved_name = owner_name or owner_username
        if not resolved_name:
            raise HTTPException(400, "owner user not found")
        return resolved_name

    # Обновляем дополнительные поля клиента только когда пришли непустые значения.
    def update_customer_credentials(conn, customer_id: Optional[int], login: Optional[str], password: Optional[str]):
        if not customer_id:
            return
        customer_login = normalize_customer_field(login)
        customer_password = normalize_customer_field(password)
        if customer_login is None and customer_password is None:
            return
        updates = []
        params = []
        if customer_login is not None:
            updates.append("customer_login=%s")
            params.append(customer_login)
        if customer_password is not None:
            updates.append("customer_password=%s")
            params.append(customer_password)
        if not updates:
            return
        params.append(customer_id)
        exec1(conn, f"UPDATE app.customers SET {', '.join(updates)} WHERE customer_id=%s", tuple(params))

    # Проверяет уникальность номера заказа для источников ym/ozon/wb в связке (source_id, order_number).
    def validate_market_order_number_unique(
        conn,
        source_id: Optional[int],
        order_number: Optional[str],
        exclude_deal_id: Optional[int] = None,
    ):
        normalized_order = (order_number or "").strip()
        if not source_id or not normalized_order:
            return
        source_row = q1(
            conn,
            "SELECT code FROM app.sources WHERE source_id=%s AND is_archived IS NOT TRUE",
            (source_id,),
        )
        source_code = str(source_row[0] or "") if source_row else ""
        # Правило включается только для источников ym/ozon/wb.
        normalized_source_code = source_code.lower().strip()
        if normalized_source_code not in {"ym", "ozon", "wb"}:
            return
        # Разделяем запросы на две ветки, чтобы Postgres не получал "безтиповый" NULL-параметр.
        if exclude_deal_id is None:
            conflict_row = q1(
                conn,
                """
                SELECT
                  d.deal_id,
                  c.nickname,
                  (
                    SELECT p.title
                    FROM app.deal_items di2
                    LEFT JOIN app.products p ON p.product_id = di2.product_id
                    WHERE di2.deal_id = d.deal_id
                    ORDER BY di2.deal_item_id DESC
                    LIMIT 1
                  ) AS product_title,
                  COALESCE(d.completed_at, d.created_at) AS deal_dt
                FROM app.deals d
                JOIN app.customers c ON c.customer_id = d.customer_id
                WHERE c.source_id=%s
                  AND lower(btrim(COALESCE(d.order_number, ''))) = lower(btrim(%s))
                LIMIT 1
                """,
                (source_id, normalized_order),
            )
        else:
            conflict_row = q1(
                conn,
                """
                SELECT
                  d.deal_id,
                  c.nickname,
                  (
                    SELECT p.title
                    FROM app.deal_items di2
                    LEFT JOIN app.products p ON p.product_id = di2.product_id
                    WHERE di2.deal_id = d.deal_id
                    ORDER BY di2.deal_item_id DESC
                    LIMIT 1
                  ) AS product_title,
                  COALESCE(d.completed_at, d.created_at) AS deal_dt
                FROM app.deals d
                JOIN app.customers c ON c.customer_id = d.customer_id
                WHERE c.source_id=%s
                  AND lower(btrim(COALESCE(d.order_number, ''))) = lower(btrim(%s))
                  AND d.deal_id <> %s
                LIMIT 1
                """,
                (source_id, normalized_order, exclude_deal_id),
            )
        if conflict_row:
            conflict_deal_id = int(conflict_row[0])
            # В unit-тестах mock может вернуть только deal_id, поэтому читаем поля безопасно.
            conflict_customer = str(conflict_row[1] or "").strip() if len(conflict_row) > 1 else ""
            conflict_product = str(conflict_row[2] or "").strip() if len(conflict_row) > 2 else ""
            conflict_dt = conflict_row[3] if len(conflict_row) > 3 else None
            if not conflict_customer:
                conflict_customer = "—"
            if not conflict_product:
                conflict_product = "—"
            conflict_date_text = conflict_dt.isoformat() if conflict_dt else "—"
            # Возвращаем подсказку с deal_id, чтобы менеджер мог сразу открыть конфликтующую сделку.
            raise HTTPException(
                409,
                f"order_number must be unique for source ym/ozon/wb; deal_id={conflict_deal_id}; customer={conflict_customer}; product={conflict_product}; created_at={conflict_date_text}",
            )

    # Проверяет, что мессенджер существует и не в архиве.
    def ensure_messenger_exists(conn, messenger_id: Optional[int]):
        if not messenger_id:
            return
        row = q1(conn, "SELECT 1 FROM app.messengers WHERE messenger_id=%s AND is_archived IS NOT TRUE", (messenger_id,))
        if not row:
            raise HTTPException(400, f"Unknown messenger_id: {messenger_id}")

    # Валидирует product_id и тип товара для операций со сделками.
    def validate_deal_product_id(
        conn,
        *,
        product_id: Optional[int],
        for_rental: bool,
        must_be_active: bool,
    ) -> Optional[str]:
        if product_id is None:
            return None
        # Параметр оставлен для совместимости сигнатуры в текущем этапе миграции.
        _ = must_be_active
        row = q1(
            conn,
            """
            SELECT type_code, is_archived
            FROM app.products
            WHERE product_id=%s
            """,
            (product_id,),
        )
        if not row:
            raise HTTPException(400, f"Unknown product_id: {product_id}")
        type_code = str(row[0] or "").strip().lower()
        is_archived = bool(row[1]) if row[1] is not None else False
        if is_archived:
            raise HTTPException(400, f"Product is archived: {product_id}")
        if for_rental and type_code not in {"game", "subscription"}:
            raise HTTPException(400, "rental supports only products with type game or subscription")
        return type_code

    # Проверяет срок подписки для rental: срок должен принадлежать товару/аккаунту и быть свободным.
    def validate_subscription_term_for_rental(
        conn,
        *,
        subscription_term_id: Optional[int],
        product_id: Optional[int],
        account_id: Optional[int],
        exclude_deal_item_id: Optional[int] = None,
    ) -> None:
        if subscription_term_id is None:
            return
        if not product_id or not account_id:
            raise HTTPException(400, "subscription_term_id requires product_id and account_id")
        term_row = q1(
            conn,
            """
            SELECT product_id, account_id, is_archived
            FROM app.subscription_terms
            WHERE term_id=%s
            """,
            (subscription_term_id,),
        )
        if not term_row:
            raise HTTPException(400, f"Unknown subscription_term_id: {subscription_term_id}")
        # В тестовых моках может приходить сокращенный формат без is_archived.
        if len(term_row) > 2 and bool(term_row[2]):
            raise HTTPException(400, "subscription term is archived")
        if int(term_row[0]) != int(product_id):
            raise HTTPException(400, "subscription_term_id does not match selected product")
        if int(term_row[1]) != int(account_id):
            raise HTTPException(400, "subscription_term_id does not match selected account")
        # Проверку фактической емкости выполняем отдельно по slot_type_code.
        # Здесь валидируем только связку срока с выбранным товаром и аккаунтом.

    # Считает свободные места для срока подписки по выбранному типу слота.
    # Для П2 (mode=activate) занятость общая между PS4/PS5, для П3 считаем по конкретному slot_type_code.
    def get_subscription_term_slot_free(conn, *, subscription_term_id: int, slot_type_code: str) -> int:
        slot_row = q1(
            conn,
            "SELECT mode, capacity FROM app.slot_types WHERE code=%s",
            (slot_type_code,),
        )
        if not slot_row:
            raise HTTPException(400, "Unknown slot_type_code")
        slot_mode = str(slot_row[0] or "").strip().lower()
        slot_capacity = int(slot_row[1] or 0)
        if slot_capacity <= 0:
            return 0

        if slot_mode == "activate":
            occupied_row = q1(
                conn,
                """
                SELECT COUNT(*)
                FROM app.account_slot_assignments asa
                JOIN app.slot_types st ON st.code = asa.slot_type_code
                WHERE asa.subscription_term_id=%s
                  AND asa.released_at IS NULL
                  AND st.mode='activate'
                """,
                (subscription_term_id,),
            )
        else:
            occupied_row = q1(
                conn,
                """
                SELECT COUNT(*)
                FROM app.account_slot_assignments
                WHERE subscription_term_id=%s
                  AND slot_type_code=%s
                  AND released_at IS NULL
                """,
                (subscription_term_id, slot_type_code),
            )
        occupied = int((occupied_row[0] if occupied_row else 0) or 0)
        return max(slot_capacity - occupied, 0)

    @app.post("/rentals")
    def create_rental(payload: RentalCreate, user=Depends(get_current_user)):
        if not payload.slot_type_code:
            raise HTTPException(400, "slot_type_code is required for rental")
        if not payload.product_id:
            raise HTTPException(400, "product_id is required for rental")
        validate_date_in_range(payload.purchase_at, "purchase_at")
        validate_date_in_range(payload.start_at, "start_at")
        validate_date_in_range(payload.end_at, "end_at")
        validate_date_range(payload.start_at, payload.end_at, "end_at")
    
        start_at = payload.start_at or now_utc()
        end_at = payload.end_at
    
        with psycopg.connect(DB_DSN) as conn:
            # Валидируем product_id для rental в product-first режиме.
            product_type_code = validate_deal_product_id(
                conn,
                product_id=payload.product_id,
                for_rental=True,
                must_be_active=True,
            )
            # Получаем region_id и заодно проверяем существование аккаунта — один запрос вместо двух
            account_row = q1(conn, "SELECT region_id FROM app.accounts WHERE account_id=%s", (payload.account_id,))
            if not account_row:
                raise HTTPException(400, f"Unknown account_id: {payload.account_id}")
            region_id = int(account_row[0]) if account_row[0] is not None else None
            ensure_source_exists(conn, payload.source_id)
            slot_type = ensure_account_allows_slot_type(conn, payload.account_id, payload.slot_type_code)
            platform_id = get_platform_id(conn, slot_type[1])
            # ensure customer exists
            row = q1(conn, "SELECT customer_id, source_id FROM app.customers WHERE nickname=%s", (payload.customer_nickname,))
            if row:
                customer_id = int(row[0])
                if payload.source_id and not row[1]:
                    exec1(
                        conn,
                        "UPDATE app.customers SET source_id=%s WHERE customer_id=%s",
                        (payload.source_id, customer_id),
                    )
            else:
                row = q1(
                    conn,
                    "INSERT INTO app.customers(nickname, source_id) VALUES (%s, %s) RETURNING customer_id",
                    (payload.customer_nickname, payload.source_id),
                )
                customer_id = int(row[0])
    
            # Проверяем свободные места: для игр старая модель по аккаунту, для подписок — по сроку.
            if product_type_code == "subscription" and payload.subscription_term_id is not None:
                validate_subscription_term_for_rental(
                    conn,
                    subscription_term_id=payload.subscription_term_id,
                    product_id=payload.product_id,
                    account_id=payload.account_id,
                )
                free = get_subscription_term_slot_free(
                    conn,
                    subscription_term_id=int(payload.subscription_term_id),
                    slot_type_code=payload.slot_type_code,
                )
            else:
                free = get_account_slot_free(conn, payload.account_id, payload.slot_type_code)
            if free < 1:
                raise HTTPException(409, "Not enough free slots for selected slot type")
    
            # create deal + item
            deal_row = q1(conn, """
                INSERT INTO app.deals(
                  deal_type_code, status_code, flow_status_code, region_id, customer_id, currency, total_amount, responsible_username
                )
                VALUES ('rental', 'confirmed', 'pending', %s, %s, 'RUB', %s, %s)
                RETURNING deal_id
            """, (region_id, customer_id, payload.price, user.username))
            deal_id = int(deal_row[0])
    
            # Для новых строк аренды сохраняем только product_id.
            row_item = q1(conn, """
                    INSERT INTO app.deal_items(
                      deal_id, account_id, product_id, platform_id,
                      qty, price, purchase_cost, start_at, end_at, slots_used, slot_type_code, subscription_term_id, purchase_at, notes, game_link
                    )
                    VALUES (
                      %s, %s, %s, %s,
                      1, %s, 0, %s, %s, 1, %s, %s, %s, %s, %s
                    )
                    RETURNING deal_item_id
                """, (
                    deal_id, payload.account_id, payload.product_id, platform_id,
                    payload.price, start_at, end_at, payload.slot_type_code, payload.subscription_term_id, payload.purchase_at, None, None
                ))
            deal_item_id = int(row_item[0])
            exec1(
                conn,
                """
                INSERT INTO app.account_slot_assignments(
                  account_id, slot_type_code, customer_id, product_id, subscription_term_id, deal_id, deal_item_id, assigned_by
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    payload.account_id,
                    payload.slot_type_code,
                    customer_id,
                    payload.product_id,
                    payload.subscription_term_id,
                    deal_id,
                    deal_item_id,
                    user.username,
                ),
            )
            conn.commit()

            # return updated slots
            occ2, free2 = slots_summary(conn, payload.account_id, platform_id)
            return {"deal_id": deal_id, "account_id": payload.account_id, "occupied_slots": occ2, "free_slots": free2}
    
    @app.post("/deals")
    def create_deal(payload: DealCreate, user=Depends(get_current_user)):
        deal_type = payload.deal_type_code.strip().lower()
        if deal_type not in ("sale", "rental"):
            raise HTTPException(400, "deal_type_code must be sale or rental")
        # Для создания поддерживаем draft и для продаж, и для шеринга.
        new_flow_status = (payload.flow_status_code or "pending").strip().lower()
        sale_is_draft = deal_type == "sale" and new_flow_status == "draft"
        rental_is_draft = deal_type == "rental" and new_flow_status == "draft"
        if deal_type == "rental" and not rental_is_draft:
            if not payload.slot_type_code:
                raise HTTPException(400, "slot_type_code is required for rental")
            if not payload.account_id:
                raise HTTPException(400, "account_id is required for rental")
            if not payload.product_id:
                raise HTTPException(400, "product_id is required for rental")
        if deal_type == "sale" and not sale_is_draft:
            if not (payload.customer_nickname or "").strip():
                raise HTTPException(400, "customer_nickname is required for non-draft sale")
            if not payload.region_code:
                raise HTTPException(400, "region_code is required for sale")
        if new_flow_status != "draft" and not payload.messenger_id:
            raise HTTPException(400, "messenger_id is required for non-draft deal")
        if deal_type == "sale":
            payload.slots_used = 0
            if not payload.purchase_at and not sale_is_draft:
                payload.purchase_at = now_utc()
        validate_date_in_range(payload.purchase_at, "purchase_at")
        validate_date_in_range(payload.start_at, "start_at")
        validate_date_in_range(payload.end_at, "end_at")
        validate_date_range(payload.start_at, payload.end_at, "end_at")
    
        with psycopg.connect(DB_DSN) as conn:
            # Нормализуем поля "номер заказа" и "ответственный", чтобы не хранить служебные значения.
            order_number = (payload.order_number or "").strip() or None
            responsible_username = (payload.responsible_username or "").strip() or None
            if responsible_username == "current_user":
                responsible_username = user.username
            if payload.flow_status_code is not None:
                row = q1(conn, "SELECT 1 FROM app.deal_flow_statuses WHERE code=%s", (new_flow_status,))
                if not row:
                    raise HTTPException(400, "Unknown flow_status_code")
            # Для rental работаем только по product_id.
            selected_product_type_code = None
            if payload.product_id is not None:
                # Проверяем product_id заранее, чтобы вернуть понятную 4xx ошибку вместо SQL-ошибки.
                selected_product_type_code = validate_deal_product_id(
                    conn,
                    product_id=payload.product_id,
                    for_rental=(deal_type == "rental"),
                    must_be_active=(deal_type == "rental" and not rental_is_draft),
                )
            if deal_type == "rental" and not rental_is_draft:
                ensure_account_exists(conn, payload.account_id)
            ensure_source_exists(conn, payload.source_id)
            ensure_messenger_exists(conn, payload.messenger_id)
            platform_id = None
            if deal_type == "rental" and not rental_is_draft:
                slot_type = ensure_account_allows_slot_type(conn, payload.account_id, payload.slot_type_code)
                platform_id = get_platform_id(conn, slot_type[1])
            region_id = get_region_id(conn, payload.region_code)
            if region_id is None:
                if payload.account_id:
                    region_row = q1(conn, "SELECT region_id FROM app.accounts WHERE account_id=%s", (payload.account_id,))
                    region_id = int(region_row[0]) if region_row and region_row[0] is not None else None

            customer_id = None
            customer_nickname = (payload.customer_nickname or "").strip()
            if customer_nickname:
                row = q1(conn, "SELECT customer_id, source_id FROM app.customers WHERE nickname=%s", (customer_nickname,))
                if row:
                    customer_id = int(row[0])
                    if payload.source_id and not row[1]:
                        exec1(
                            conn,
                            "UPDATE app.customers SET source_id=%s WHERE customer_id=%s",
                            (payload.source_id, customer_id),
                        )
                else:
                    row = q1(
                        conn,
                        """
                        INSERT INTO app.customers(nickname, source_id, customer_login, customer_password)
                        VALUES (%s, %s, %s, %s)
                        RETURNING customer_id
                        """,
                        (
                            customer_nickname,
                            payload.source_id,
                            normalize_customer_field(payload.login),
                            normalize_customer_field(payload.password),
                        ),
                    )
                    customer_id = int(row[0])
                # Для уже существующего клиента обновляем логин/пароль, если они реально переданы.
                update_customer_credentials(conn, customer_id, payload.login, payload.password)
            # Проверяем уникальность только когда номер заказа действительно заполнен.
            if order_number and customer_id is not None:
                customer_row = q1(conn, "SELECT source_id FROM app.customers WHERE customer_id=%s", (customer_id,))
                customer_source_id = int(customer_row[0]) if customer_row and customer_row[0] is not None else None
                validate_market_order_number_unique(conn, customer_source_id, order_number)
    
            selected_subscription_term_id = int(payload.subscription_term_id) if payload.subscription_term_id is not None else None
            if deal_type == "rental" and not rental_is_draft:
                if selected_product_type_code == "subscription" and selected_subscription_term_id is not None:
                    validate_subscription_term_for_rental(
                        conn,
                        subscription_term_id=selected_subscription_term_id,
                        product_id=payload.product_id,
                        account_id=payload.account_id,
                    )
                    free = get_subscription_term_slot_free(
                        conn,
                        subscription_term_id=selected_subscription_term_id,
                        slot_type_code=payload.slot_type_code,
                    )
                else:
                    free = get_account_slot_free(conn, payload.account_id, payload.slot_type_code)
                if free < 1:
                    raise HTTPException(409, "Not enough free slots for selected slot type")
            should_validate_term_separately = (
                deal_type == "rental"
                and selected_subscription_term_id is not None
                and (rental_is_draft or selected_product_type_code != "subscription")
            )
            if should_validate_term_separately:
                validate_subscription_term_for_rental(
                    conn,
                    subscription_term_id=selected_subscription_term_id,
                    product_id=payload.product_id,
                    account_id=payload.account_id,
                )

            selected_reserve_key = None
            if deal_type == "rental" and payload.account_id and customer_id is not None:
                # Резерв подбираем только когда есть покупатель, иначе оставляем ключ пустым.
                normalized_payload_reserve = normalize_reserve_key(payload.reserve_key)
                if normalized_payload_reserve:
                    used_keys = get_used_reserve_keys(conn, payload.account_id)
                    selected_reserve_key = normalized_payload_reserve if normalized_payload_reserve not in used_keys else None
                if selected_reserve_key is None:
                    selected_reserve_key = pick_first_free_reserve_key(conn, payload.account_id)
    
            deal_row = q1(conn, """
                INSERT INTO app.deals(
                  deal_type_code, status_code, flow_status_code, region_id, customer_id, messenger_id, currency, total_amount, order_number, responsible_username
                )
                VALUES (%s, 'confirmed', %s, %s, %s, %s, 'RUB', %s, %s, %s)
                RETURNING deal_id
            """, (deal_type, new_flow_status, region_id, customer_id, payload.messenger_id, payload.price, order_number, responsible_username))
            deal_id = int(deal_row[0])
    
            # Для новых сделок (sale/rental) храним только product_id.
            product_link = payload.product_link
            if deal_type == "rental" and not rental_is_draft:
                row_item = q1(conn, """
                    INSERT INTO app.deal_items(
                      deal_id, account_id, product_id, platform_id,
                      qty, price, purchase_cost, fee, purchase_at, start_at, end_at, slots_used, slot_type_code, subscription_term_id, reserve_key, notes, game_link
                    )
                    VALUES (
                      %s, %s, %s, %s,
                      1, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING deal_item_id
                """, (
                    deal_id, payload.account_id, payload.product_id, platform_id,
                    payload.price, payload.purchase_cost, payload.purchase_at, payload.start_at, payload.end_at,
                    1, payload.slot_type_code, selected_subscription_term_id, selected_reserve_key, payload.notes, product_link
                ))
            else:
                row_item = q1(conn, """
                    INSERT INTO app.deal_items(
                      deal_id, account_id, product_id, platform_id,
                      qty, price, purchase_cost, fee, purchase_at, start_at, end_at, slots_used, slot_type_code, reserve_key, notes, game_link
                    )
                    VALUES (
                      %s, %s, %s, %s,
                      1, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING deal_item_id
                """, (
                    deal_id, payload.account_id, payload.product_id, platform_id,
                    payload.price, payload.purchase_cost, payload.purchase_at, payload.start_at, payload.end_at,
                    0, payload.slot_type_code, None, payload.notes, product_link
                ))
            deal_item_id = int(row_item[0])
            if deal_type == "rental" and not rental_is_draft:
                exec1(
                    conn,
                    """
                    INSERT INTO app.account_slot_assignments(
                      account_id, slot_type_code, customer_id, product_id, subscription_term_id, deal_id, deal_item_id, assigned_by
                    )
                    VALUES (
                      %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        payload.account_id,
                        payload.slot_type_code,
                        customer_id,
                        payload.product_id,
                        selected_subscription_term_id,
                        deal_id,
                        deal_item_id,
                        user.username,
                    ),
                )
            conn.commit()
            # После фиксации публикуем событие, чтобы клиенты могли обновить список сделок в реальном времени.
            if publish_deal_event:
                try:
                    publish_deal_event("deal_created", deal_id, user.username)
                except Exception:
                    # Ошибка нотификации не должна ломать сохранение сделки.
                    pass
    
            return {"deal_id": deal_id}
    
    @app.put("/deals/{deal_id}")
    def update_deal(deal_id: int, payload: DealUpdate, user=Depends(get_current_user)):
        if payload.purchase_at is not None:
            validate_date_in_range(payload.purchase_at, "purchase_at")
        if payload.created_at is not None:
            validate_date_in_range(payload.created_at, "created_at")
        if payload.completed_at is not None:
            validate_date_in_range(payload.completed_at, "completed_at")
        if payload.start_at is not None:
            validate_date_in_range(payload.start_at, "start_at")
        if payload.end_at is not None:
            validate_date_in_range(payload.end_at, "end_at")
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.user', %s, true)", (user.username,))
            row = q1(
                conn,
                """
                SELECT
                  d.deal_type_code,
                  d.status_code,
                  d.flow_status_code,
                  d.lock_version,
                  d.region_id,
                  d.customer_id,
                  d.total_amount,
                  d.order_number,
                  d.responsible_username,
                  d.messenger_id,
                  di.deal_item_id,
                  di.account_id,
                  di.platform_id,
                  di.price,
                  di.purchase_cost,
                  di.purchase_at,
                  di.start_at,
                  di.end_at,
                  di.slots_used,
                  di.slot_type_code,
                  di.subscription_term_id,
                  di.reserve_key,
                  di.notes,
                  di.game_link,
                  di.returned_at
                FROM app.deals d
                JOIN app.deal_items di ON di.deal_id = d.deal_id
                WHERE d.deal_id=%s
                ORDER BY di.deal_item_id ASC
                LIMIT 1
                """,
                (deal_id,),
            )
            if not row:
                raise HTTPException(404, "Deal not found")
    
            if len(row) >= 25:
                current_type, status_code, flow_status_code, current_lock_version, region_id, customer_id, total_amount, order_number, responsible_username, current_messenger_id, deal_item_id, \
                    account_id, platform_id, price, purchase_cost, purchase_at, start_at, end_at, slots_used, slot_type_code, subscription_term_id, reserve_key, notes, game_link, returned_at = row
            else:
                # Поддерживаем старый формат строки (без lock_version) в тестовых моках.
                current_type, status_code, flow_status_code, region_id, customer_id, total_amount, order_number, responsible_username, deal_item_id, \
                    account_id, platform_id, price, purchase_cost, purchase_at, start_at, end_at, slots_used, slot_type_code, notes, game_link, returned_at = row
                current_lock_version = 1
                subscription_term_id = None
                reserve_key = None
                current_messenger_id = None
            # Проверяем версию записи, чтобы не перезаписать чужие правки при одновременном редактировании.
            expected_lock_version = payload.lock_version
            # Для обратной совместимости допускаем старые клиенты без lock_version.
            if expected_lock_version is None:
                expected_lock_version = int(current_lock_version or 1)
            if int(expected_lock_version) != int(current_lock_version or 0):
                raise HTTPException(409, "deal was modified by another user")
            user_role = (getattr(user, "role", "") or "").strip().lower()
            can_edit_completed = has_completed_deal_access(user)
            # Завершенные сделки редактируют только admin/owner; для возврата есть отдельный endpoint.
            if str(flow_status_code or "").strip().lower() == "completed" and not can_edit_completed:
                raise HTTPException(403, "editing completed deal is allowed only for admin/owner")
            # Ручные правки системных дат разрешаем только для admin/owner у завершенной сделки.
            has_manual_system_dates = payload.created_at is not None or payload.completed_at is not None
            # Для admin/owner ручные даты теперь доступны в любом статусе сделки.
            if has_manual_system_dates and not can_edit_completed:
                raise HTTPException(403, "editing completed deal is allowed only for admin/owner")
            # Защищаем ручные системные даты от инверсии: завершение не может быть раньше создания.
            if payload.created_at is not None and payload.completed_at is not None and payload.completed_at < payload.created_at:
                raise HTTPException(400, "completed_at must be >= created_at")
    
            deal_type = (payload.deal_type_code or current_type or "").strip().lower()
            if deal_type not in ("sale", "rental"):
                raise HTTPException(400, "deal_type_code must be sale or rental")
            current_product_id = None
            if deal_type == "rental":
                # Для rental всегда читаем текущий product_id, чтобы отличать реальные изменения от сохранения без правок.
                product_row = q1(conn, "SELECT product_id FROM app.deal_items WHERE deal_item_id=%s", (deal_item_id,))
                current_product_id = int(product_row[0]) if product_row and product_row[0] is not None else None
            # Для update используем переданный product_id, а если его нет — сохраняем текущий.
            new_product_id = payload.product_id if payload.product_id is not None else current_product_id
            new_flow_status = payload.flow_status_code if payload.flow_status_code is not None else flow_status_code
            if payload.flow_status_code is not None:
                row = q1(conn, "SELECT 1 FROM app.deal_flow_statuses WHERE code=%s", (payload.flow_status_code,))
                if not row:
                    raise HTTPException(400, "Unknown flow_status_code")
            # Черновик нельзя переводить сразу в completed из формы редактирования.
            if str(flow_status_code or "").strip().lower() == "draft" and str(new_flow_status or "").strip().lower() == "completed":
                raise HTTPException(400, "draft deal cannot be completed directly")
            # Черновик допускаем и для продаж, и для шеринга.
            rental_is_draft = deal_type == "rental" and new_flow_status == "draft"

            new_account_id = payload.account_id if payload.account_id is not None else account_id
            # Источник теперь опциональный, поэтому валидируем только если значение передано.
            ensure_source_exists(conn, payload.source_id if payload.source_id is not None else None)
            # Для non-draft сделки мессенджер обязателен; в draft допускаем пустое значение.
            new_messenger_id = current_messenger_id if payload.messenger_id is None else payload.messenger_id
            if str(new_flow_status or "").strip().lower() != "draft" and not new_messenger_id:
                raise HTTPException(400, "messenger_id is required for non-draft deal")
            ensure_messenger_exists(conn, new_messenger_id)
            if new_product_id is not None and deal_type != "rental":
                # Для продажи валидируем только product_id.
                validate_deal_product_id(
                    conn,
                    product_id=new_product_id,
                    for_rental=False,
                    must_be_active=False,
                )
            if payload.region_code is not None:
                region_id = get_region_id(conn, payload.region_code)
    
            new_slot_type_code = payload.slot_type_code if payload.slot_type_code is not None else slot_type_code
            new_subscription_term_id = payload.subscription_term_id if payload.subscription_term_id is not None else subscription_term_id
            new_reserve_key = normalize_reserve_key(payload.reserve_key) if payload.reserve_key is not None else normalize_reserve_key(reserve_key)
            new_platform_id = platform_id
            if deal_type == "rental" and not rental_is_draft:
                if not new_slot_type_code:
                    raise HTTPException(400, "slot_type_code is required for rental")
                # Платформу пересчитываем только при фактической смене типа слота.
                slot_type_changed = payload.slot_type_code is not None and (new_slot_type_code or "") != (slot_type_code or "")
                if slot_type_changed:
                    slot_type = get_slot_type(conn, new_slot_type_code)
                    new_platform_id = get_platform_id(conn, slot_type[1])
                if new_subscription_term_id is not None:
                    validate_subscription_term_for_rental(
                        conn,
                        subscription_term_id=int(new_subscription_term_id),
                        product_id=new_product_id,
                        account_id=new_account_id,
                        exclude_deal_item_id=deal_item_id,
                    )
    
            # customer update
            cust_nickname = payload.customer_nickname
            cust_source = payload.source_id if payload.source_id is not None else None
            if cust_nickname:
                customer_id = ensure_customer(conn, cust_nickname, cust_source)
            # Если передали логин/пароль, обновляем их у текущего клиента сделки.
            update_customer_credentials(conn, customer_id, payload.login, payload.password)
    
            new_price = payload.price if payload.price is not None else price
            new_purchase_cost = payload.purchase_cost if payload.purchase_cost is not None else purchase_cost
            new_purchase_at = payload.purchase_at if payload.purchase_at is not None else purchase_at
            new_start_at = payload.start_at if payload.start_at is not None else start_at
            new_end_at = payload.end_at if payload.end_at is not None else end_at
            new_notes = payload.notes if payload.notes is not None else notes
            new_product_link = (
                payload.product_link
                if payload.product_link is not None
                else game_link
            )
            new_order_number = order_number if payload.order_number is None else ((payload.order_number or "").strip() or None)
            current_order_number = ((order_number or "").strip() or None)
            if payload.responsible_username is None:
                new_responsible_username = responsible_username
            else:
                normalized_responsible = (payload.responsible_username or "").strip()
                if normalized_responsible == "current_user":
                    normalized_responsible = user.username
                new_responsible_username = normalized_responsible or None
            # Для update проверяем уникальность market-заказа только если реально поменяли order_number.
            if new_order_number and new_order_number != current_order_number:
                customer_row = q1(conn, "SELECT source_id FROM app.customers WHERE customer_id=%s", (customer_id,))
                customer_source_id = int(customer_row[0]) if customer_row and customer_row[0] is not None else None
                validate_market_order_number_unique(conn, customer_source_id, new_order_number, exclude_deal_id=deal_id)
            new_slots_used = payload.slots_used if payload.slots_used is not None else slots_used
            current_is_refund = returned_at is not None
            new_is_refund = current_is_refund if payload.is_refund is None else bool(payload.is_refund)
            is_refund_changed = new_is_refund != current_is_refund
            # Признак возврата можно менять в pending для всех, а в completed только для admin/owner.
            allow_refund_change = flow_status_code == "pending" or (flow_status_code == "completed" and can_edit_completed)
            if is_refund_changed and not allow_refund_change:
                raise HTTPException(400, "is_refund can be changed only for pending deals")
            if payload.is_refund and deal_type not in {"sale", "rental"}:
                raise HTTPException(400, "is_refund is allowed only for sale or rental deals")
            # Проведение возврата в completed разрешено только владельцу или администратору.
            is_completing_now = flow_status_code != "completed" and new_flow_status == "completed"
            if is_completing_now and new_is_refund and user_role not in {"admin", "owner"}:
                raise HTTPException(403, "не достаточно прав для проведения возврата")
            # Храним признак возврата через returned_at: timestamp при включении и null при выключении.
            new_returned_at = returned_at
            if is_refund_changed:
                if new_is_refund:
                    new_returned_at = returned_at or now_utc()
                else:
                    new_returned_at = None
            if deal_type in {"sale", "rental"} and new_is_refund:
                # Для возвратной сделки назначаем owner ответственным.
                new_responsible_username = resolve_owner_responsible_name(conn)
            if deal_type == "sale":
                new_slots_used = 0
                new_account_id = None
                new_platform_id = None
                new_slot_type_code = None
                new_reserve_key = None
                # Для черновика продажи допускаем пустой регион.
                if new_flow_status != "draft" and region_id is None:
                    raise HTTPException(400, "region_code is required for sale")
                # Для не-черновика продажи покупатель обязателен, иначе сделку нельзя провести.
                if new_flow_status != "draft" and customer_id is None:
                    raise HTTPException(400, "customer_nickname is required for non-draft sale")
            if deal_type == "rental":
                new_slots_used = 0 if rental_is_draft else 1
            validate_date_range(new_start_at, new_end_at, "end_at")

            # Проверку доступности слотов запускаем только когда меняются слотные поля rental-сделки.
            should_recheck_rental_slot_capacity = False
            if deal_type == "rental" and not rental_is_draft:
                current_account_normalized = int(account_id) if account_id is not None else None
                new_account_normalized = int(new_account_id) if new_account_id is not None else None
                current_product_normalized = int(current_product_id) if current_product_id is not None else None
                new_product_normalized = int(new_product_id) if new_product_id is not None else None
                flow_from_draft = str(flow_status_code or "").strip().lower() == "draft"
                flow_to_non_draft = str(new_flow_status or "").strip().lower() != "draft"
                product_changed = payload.product_id is not None and new_product_normalized != current_product_normalized
                should_recheck_rental_slot_capacity = (
                    (payload.account_id is not None and new_account_normalized != current_account_normalized)
                    or (payload.slot_type_code is not None and (new_slot_type_code or "") != (slot_type_code or ""))
                    or product_changed
                    or (flow_from_draft and flow_to_non_draft)
                )
    
            # check slots for rental
            if deal_type == "rental" and not rental_is_draft and should_recheck_rental_slot_capacity:
                # Для rental валидируем продукт в product-first режиме.
                if new_product_id is None:
                    raise HTTPException(400, "product_id is required for rental")
                new_product_type_code = validate_deal_product_id(
                    conn,
                    product_id=new_product_id,
                    for_rental=True,
                    must_be_active=False,
                )
                if not new_account_id:
                    raise HTTPException(400, "account_id is required for rental")
                ensure_account_exists(conn, new_account_id)
                # Проверяем, что аккаунт действительно поддерживает выбранный тип слота.
                # Это универсальная проверка и для игр, и для подписок.
                ensure_account_allows_slot_type(conn, new_account_id, new_slot_type_code)
                row_assign = q1(
                    conn,
                    """
                    SELECT account_id, slot_type_code, subscription_term_id
                    FROM app.account_slot_assignments
                    WHERE deal_item_id=%s AND released_at IS NULL
                    """,
                    (deal_item_id,),
                )
                same_assignment = row_assign and int(row_assign[0]) == int(new_account_id) and row_assign[1] == new_slot_type_code
                if new_product_type_code == "subscription" and new_subscription_term_id is not None:
                    free = get_subscription_term_slot_free(
                        conn,
                        subscription_term_id=int(new_subscription_term_id),
                        slot_type_code=new_slot_type_code,
                    )
                    # Для текущего назначения учитываем один уже занятый слот этого же срока как доступный.
                    same_term = row_assign and row_assign[2] is not None and int(row_assign[2]) == int(new_subscription_term_id)
                    free_adjusted = free + (1 if (same_assignment and same_term) else 0)
                else:
                    free = get_account_slot_free(conn, new_account_id, new_slot_type_code)
                    free_adjusted = free + (1 if same_assignment else 0)
                if free_adjusted < 1:
                    raise HTTPException(409, "Not enough free slots for selected slot type")
                # Для rental резерв должен быть уникален в рамках аккаунта: выбираем первый свободный.
                used_keys = get_used_reserve_keys(conn, new_account_id, exclude_deal_id=deal_id)
                if new_reserve_key in used_keys:
                    new_reserve_key = None
                if not new_reserve_key:
                    new_reserve_key = pick_first_free_reserve_key(conn, new_account_id, exclude_deal_id=deal_id)
    
            completed_at_changed = flow_status_code != new_flow_status
            completed_at_value = None
            if completed_at_changed:
                completed_at_value = now_utc() if new_flow_status == "completed" else None
            created_at_override = payload.created_at is not None
            created_at_override_value = payload.created_at if created_at_override else None
            completed_at_override = payload.completed_at is not None
            completed_at_override_value = payload.completed_at if completed_at_override else None

            updated_rows = exec1(
                conn,
                """
                UPDATE app.deals
                SET deal_type_code=%s,
                    customer_id=%s,
                    messenger_id=%s,
                    total_amount=%s,
                    flow_status_code=%s,
                    region_id=%s,
                    order_number=%s,
                    responsible_username=%s,
                    created_at=CASE WHEN %s THEN %s ELSE created_at END,
                    completed_at=CASE
                        WHEN %s THEN %s
                        WHEN %s THEN %s
                        ELSE completed_at
                    END,
                    lock_version=lock_version + 1
                WHERE deal_id=%s
                  AND lock_version=%s
                """,
                (
                    deal_type,
                    customer_id,
                    new_messenger_id,
                    new_price,
                    new_flow_status,
                    region_id,
                    new_order_number,
                    new_responsible_username,
                    created_at_override,
                    created_at_override_value,
                    completed_at_override,
                    completed_at_override_value,
                    completed_at_changed,
                    completed_at_value,
                    deal_id,
                    expected_lock_version,
                ),
            )
            # Защищаемся от гонки: если версия уже изменилась между чтением и UPDATE, отклоняем сохранение.
            if updated_rows <= 0:
                raise HTTPException(409, "deal was modified by another user")
    
            # Для rental обновляем строку в product-first режиме через product_id.
            if deal_type == "rental":
                exec1(
                    conn,
                    """
                    UPDATE app.deal_items
                    SET account_id=%s,
                        product_id=%s,
                        platform_id=%s,
                        price=%s,
                        purchase_cost=%s,
                        purchase_at=%s,
                        start_at=%s,
                        end_at=%s,
                        returned_at=%s,
                        slots_used=%s,
                        slot_type_code=%s,
                        subscription_term_id=%s,
                        reserve_key=%s,
                        notes=%s,
                        game_link=%s
                    WHERE deal_item_id=%s
                    """,
                    (
                        new_account_id,
                        new_product_id,
                        new_platform_id,
                        new_price,
                        new_purchase_cost,
                        new_purchase_at,
                        new_start_at,
                        new_end_at,
                        new_returned_at,
                        new_slots_used,
                        new_slot_type_code,
                        new_subscription_term_id,
                        new_reserve_key,
                        new_notes,
                        new_product_link,
                        deal_item_id,
                    ),
                )
            else:
                exec1(
                    conn,
                    """
                    UPDATE app.deal_items
                    SET account_id=%s,
                        product_id=COALESCE(%s, product_id),
                        platform_id=%s,
                        price=%s,
                        purchase_cost=%s,
                        purchase_at=%s,
                        start_at=%s,
                        end_at=%s,
                        returned_at=%s,
                        slots_used=%s,
                        slot_type_code=%s,
                        subscription_term_id=%s,
                        reserve_key=%s,
                        notes=%s,
                        game_link=%s
                    WHERE deal_item_id=%s
                    """,
                    (
                        new_account_id,
                        new_product_id,
                        new_platform_id,
                        new_price,
                        new_purchase_cost,
                        new_purchase_at,
                        new_start_at,
                        new_end_at,
                        new_returned_at,
                        new_slots_used,
                        new_slot_type_code,
                        new_subscription_term_id,
                        new_reserve_key,
                        new_notes,
                        new_product_link,
                        deal_item_id,
                    ),
                )
            if deal_type == "rental":
                if rental_is_draft:
                    # Подписочные назначения нельзя снимать через перевод сделки в draft.
                    # Лишний запрос не делаем, если в текущей сделке срока подписки нет.
                    if subscription_term_id is not None or new_subscription_term_id is not None:
                        row_assign = q1(
                            conn,
                            """
                            SELECT subscription_term_id
                            FROM app.account_slot_assignments
                            WHERE deal_item_id=%s AND released_at IS NULL
                            LIMIT 1
                            """,
                            (deal_item_id,),
                        )
                        if row_assign and row_assign[0] is not None:
                            raise HTTPException(409, "subscription slot release is not allowed")
                    # При переводе шеринга в черновик снимаем активное назначение слота.
                    release_slot_assignment(conn, deal_item_id, user.username)
                else:
                    row_assign = q1(
                        conn,
                        """
                        SELECT assignment_id, account_id, slot_type_code, customer_id, product_id
                             , subscription_term_id
                        FROM app.account_slot_assignments
                        WHERE deal_item_id=%s AND released_at IS NULL
                        """,
                        (deal_item_id,),
                    )
                    current_assign = row_assign[0] if row_assign else None
                    # Сравниваем назначение только по product_id.
                    assigned_product_id = int(row_assign[4]) if row_assign and len(row_assign) > 4 and row_assign[4] is not None else None
                    # Поддерживаем старые тестовые моки без поля subscription_term_id.
                    assigned_subscription_term_id = (
                        int(row_assign[5]) if row_assign and len(row_assign) > 5 and row_assign[5] is not None else None
                    )
                    new_subscription_term_id_normalized = int(new_subscription_term_id) if new_subscription_term_id is not None else None
                    assigned_customer_id = int(row_assign[3]) if row_assign and row_assign[3] is not None else None
                    new_customer_id = int(customer_id) if customer_id is not None else None
                    need_new_assign = (
                        (not row_assign)
                        or int(row_assign[1]) != int(new_account_id)
                        or row_assign[2] != new_slot_type_code
                        or (assigned_product_id != int(new_product_id))
                        or (assigned_subscription_term_id != new_subscription_term_id_normalized)
                    )
                    # Для подписок не разрешаем снятие/переназначение активного слота.
                    is_subscription_assignment = assigned_subscription_term_id is not None or new_subscription_term_id_normalized is not None
                    if need_new_assign and current_assign and is_subscription_assignment:
                        raise HTTPException(409, "subscription slot reassignment is not allowed")
                    if need_new_assign and current_assign:
                        release_slot_assignment(conn, deal_item_id, user.username)
                    if need_new_assign:
                        exec1(
                            conn,
                            """
                            INSERT INTO app.account_slot_assignments(
                              account_id, slot_type_code, customer_id, product_id, subscription_term_id, deal_id, deal_item_id, assigned_by
                            )
                            VALUES (
                              %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            """,
                            (
                                new_account_id,
                                new_slot_type_code,
                                customer_id,
                                new_product_id,
                                new_subscription_term_id,
                                deal_id,
                                deal_item_id,
                                user.username,
                            ),
                        )
                    elif row_assign and new_customer_id != assigned_customer_id:
                        # При простом переименовании покупателя обновляем клиента в активном назначении без "снятия" слота.
                        exec1(
                            conn,
                            """
                            UPDATE app.account_slot_assignments
                            SET customer_id=%s
                            WHERE assignment_id=%s
                            """,
                            (new_customer_id, current_assign),
                        )
            conn.commit()
            # После успешного update отправляем событие об изменении сделки.
            if publish_deal_event:
                try:
                    publish_deal_event("deal_updated", deal_id, user.username)
                except Exception:
                    # Ошибка нотификации не должна ломать update сделки.
                    pass
    
        return {"ok": True}

    @app.post("/deals/{deal_id}/return")
    def return_completed_deal_to_pending(deal_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.user', %s, true)", (user.username,))
            # Берем текущее состояние сделки, чтобы безопасно выполнить возврат только для нужного кейса.
            row = q1(
                conn,
                """
                SELECT d.deal_type_code, d.flow_status_code, di.returned_at
                FROM app.deals d
                JOIN app.deal_items di ON di.deal_id = d.deal_id
                WHERE d.deal_id=%s
                ORDER BY di.deal_item_id ASC
                LIMIT 1
                """,
                (deal_id,),
            )
            if not row:
                raise HTTPException(404, "Deal not found")
            deal_type_code, flow_status_code, returned_at = row
            normalized_deal_type = str(deal_type_code or "").strip().lower()
            if normalized_deal_type not in {"sale", "rental"}:
                raise HTTPException(400, "return is allowed only for sale or rental deals")
            if str(flow_status_code or "").strip().lower() != "completed":
                raise HTTPException(400, "return is allowed only for completed deals")
            if returned_at is not None:
                raise HTTPException(400, "deal is already marked as refund")

            owner_responsible = resolve_owner_responsible_name(conn)
            returned_at_value = now_utc()
            # Переводим сделку обратно в pending, очищаем дату завершения и назначаем owner ответственным.
            exec1(
                conn,
                """
                UPDATE app.deals
                SET flow_status_code='pending',
                    responsible_username=%s,
                    completed_at=NULL
                WHERE deal_id=%s
                """,
                (owner_responsible, deal_id),
            )
            # Признак возврата храним в returned_at: ставим timestamp для всех позиций сделки.
            exec1(
                conn,
                "UPDATE app.deal_items SET returned_at=%s WHERE deal_id=%s",
                (returned_at_value, deal_id),
            )
            # Для шеринга при возврате снимаем все активные назначения слотов по сделке.
            if normalized_deal_type == "rental":
                exec1(
                    conn,
                    """
                    UPDATE app.account_slot_assignments
                    SET released_at=now(),
                        released_by=%s
                    WHERE deal_id=%s
                      AND released_at IS NULL
                    """,
                    (user.username, deal_id),
                )
            conn.commit()
            if publish_deal_event:
                try:
                    publish_deal_event("deal_updated", deal_id, user.username)
                except Exception:
                    # Ошибка нотификации не должна ломать успешный возврат.
                    pass
        return {"ok": True}

    @app.delete("/deals/{deal_id}")
    def delete_deal(deal_id: int, user=Depends(get_current_user)):
        # Мягкое удаление: оставляем запись в БД, меняем только статус.
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT flow_status_code FROM app.deals WHERE deal_id=%s", (deal_id,))
            if not row:
                raise HTTPException(404, "Deal not found")
            if row[0] != "draft":
                raise HTTPException(400, "delete is allowed only for draft deals")
            exec1(conn, "UPDATE app.deals SET status_code='cancelled' WHERE deal_id=%s", (deal_id,))
            conn.commit()
            if publish_deal_event:
                try:
                    publish_deal_event("deal_deleted", deal_id, user.username)
                except Exception:
                    # Ошибка нотификации не должна ломать удаление сделки.
                    pass
        return {"ok": True}
    
    @app.get("/deals", response_model=DealListOut)
    def list_deals(
        account_id: Optional[int] = None,
        platform_code: Optional[str] = None,
        q: Optional[str] = None,
        deal_type_code: Optional[str] = None,
        status_code: Optional[str] = None,
        flow_status_code: Optional[str] = None,
        customer_q: Optional[str] = None,
        responsible_q: Optional[str] = None,
        source_id: Optional[int] = None,
        purchase_from: Optional[date] = None,
        purchase_to: Optional[date] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        notes_q: Optional[str] = None,
        account_q: Optional[str] = None,
        region_q: Optional[str] = None,
        product_q: Optional[str] = None,
        platform_q: Optional[str] = None,
        type_q: Optional[str] = None,
        status_q: Optional[str] = None,
        flow_status_q: Optional[str] = None,
        source_q: Optional[str] = None,
        date_q: Optional[str] = None,
        price_q: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_key: str = "date",
        sort_dir: str = "asc",
        user=Depends(get_current_user),
    ):
        if page < 1:
            raise HTTPException(400, "page must be >= 1")
        if page_size < 1 or page_size > 200:
            raise HTTPException(400, "page_size must be between 1 and 200")
        offset = (page - 1) * page_size
        sort_dir = "desc" if str(sort_dir).lower() == "desc" else "asc"
        sort_map = {
            # Сортировки сделок приводим к тем же ключам, что использует фронт в таблице.
            "type": "COALESCE(dt.name, '')",
            "customer": "COALESCE(c.nickname, '')",
            "responsible": "COALESCE(d.responsible_username, '')",
            # В UI колонка называется "Товар", но ключ исторически остался region.
            "region": "COALESCE(pr.title, '')",
            "status": "COALESCE(fs.name, '')",
            "date": "COALESCE(di.purchase_at, d.created_at)",
        }
        sort_expr = sort_map.get(sort_key, sort_map["date"])
    
        with psycopg.connect(DB_DSN) as conn:
            where_sql, params = build_deals_filters(
                account_id,
                platform_code,
                q,
                deal_type_code,
                status_code,
                flow_status_code,
                customer_q,
                responsible_q,
                source_id,
                purchase_from,
                purchase_to,
                price_min,
                price_max,
                notes_q,
                account_q,
                region_q,
                product_q,
                platform_q,
                type_q,
                status_q,
                flow_status_q,
                source_q,
                date_q,
                price_q,
            )
            # Удаленные (cancelled) сделки скрываем из рабочего списка.
            if where_sql:
                where_sql = f"{where_sql} AND d.status_code <> 'cancelled'"
            else:
                where_sql = "WHERE d.status_code <> 'cancelled'"
            # Возвратные сделки в списке видят только admin/owner.
            can_view_refunds = has_completed_deal_access(user)
            if not can_view_refunds:
                if where_sql:
                    where_sql = f"{where_sql} AND di.returned_at IS NULL"
                else:
                    where_sql = "WHERE di.returned_at IS NULL"
            # Ограничение completed за 24 часа применяем только к общему рабочему списку.
            # Для карточки конкретного аккаунта (account_id) показываем полную историю привязанных сделок.
            if account_id is None:
                completed_recent_from = now_utc() - timedelta(days=1)
                completed_recent_clause = "(d.flow_status_code <> 'completed' OR COALESCE(d.completed_at, di.purchase_at, d.created_at) >= %s)"
                if where_sql:
                    where_sql = f"{where_sql} AND {completed_recent_clause}"
                else:
                    where_sql = f"WHERE {completed_recent_clause}"
                params.append(completed_recent_from)

            total_row = q1(conn, f"""
                SELECT COUNT(*)
                FROM app.deal_items di
                JOIN app.deals d ON d.deal_id = di.deal_id
                LEFT JOIN app.accounts a ON a.account_id = di.account_id
                LEFT JOIN app.domains dm ON dm.domain_id = a.domain_id
                LEFT JOIN app.regions ra ON ra.region_id = a.region_id
                LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                LEFT JOIN app.products pr ON pr.product_id = di.product_id
                LEFT JOIN app.platforms p ON p.platform_id = di.platform_id
                LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                LEFT JOIN app.sources src ON src.source_id = c.source_id
                LEFT JOIN app.deal_flow_statuses fs ON fs.code = d.flow_status_code
                LEFT JOIN app.deal_statuses ds ON ds.code = d.status_code
                LEFT JOIN app.deal_types dt ON dt.code = d.deal_type_code
                {where_sql}
            """, params)
            total = int(total_row[0]) if total_row else 0
    
            rows = qall(conn, f"""
                SELECT
                  d.deal_id,
                  dt.name as deal_type_name,
                  dt.code as deal_type_code,
                  ds.name as status_name,
                  d.flow_status_code,
                  fs.name as flow_status_name,
                  d.order_number,
                  COALESCE(
                    (
                      SELECT NULLIF(btrim(u.name), '')
                      FROM app.users u
                      WHERE lower(u.username) = lower(d.responsible_username)
                      ORDER BY u.user_id ASC
                      LIMIT 1
                    ),
                    d.responsible_username
                  ) as responsible_username,
                  COALESCE(rd.code, ra.code) as region_code,
                  di.account_id,
                  a.login_name,
                  dm.name as domain_name,
                  di.product_id,
                  pr.title as product_title,
                  pr.short_title as product_short_title,
                  p.code as platform_code,
                  c.nickname,
                  c.customer_login,
                  c.customer_password,
                  c.source_id,
                  di.price,
                  di.purchase_cost,
                  di.purchase_at,
                  d.created_at,
                  d.completed_at,
                  di.slots_used,
                  di.slot_type_code,
                  di.subscription_term_id,
                  st.valid_until AS subscription_valid_until,
                  di.reserve_key,
                  di.notes,
                  di.game_link as product_link,
                  (di.returned_at IS NOT NULL) as is_refund,
                  d.lock_version,
                  d.messenger_id
                FROM app.deal_items di
                JOIN app.deals d ON d.deal_id = di.deal_id
                LEFT JOIN app.deal_types dt ON dt.code = d.deal_type_code
                LEFT JOIN app.deal_statuses ds ON ds.code = d.status_code
                LEFT JOIN app.deal_flow_statuses fs ON fs.code = d.flow_status_code
                LEFT JOIN app.accounts a ON a.account_id = di.account_id
                LEFT JOIN app.domains dm ON dm.domain_id = a.domain_id
                LEFT JOIN app.regions ra ON ra.region_id = a.region_id
                LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                LEFT JOIN app.products pr ON pr.product_id = di.product_id
                LEFT JOIN app.subscription_terms st ON st.term_id = di.subscription_term_id
                LEFT JOIN app.platforms p ON p.platform_id = di.platform_id
                LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                LEFT JOIN app.sources src ON src.source_id = c.source_id
                {where_sql}
                ORDER BY {sort_expr} {sort_dir}, d.deal_id ASC
                LIMIT %s OFFSET %s
            """, params + [page_size, offset])
    
        items = []
        for r in rows:
            login_full = f"{r[10]}@{r[11]}" if r[10] and r[11] else None
            # Разбираем единый product-first формат строки из SQL списка сделок.
            product_id = r[12]
            product_title = r[13]
            product_short_title = r[14]
            platform_code = r[15]
            customer_nickname = r[16]
            login = r[17]
            password = r[18]
            source_id = r[19]
            price_value = r[20]
            purchase_cost_value = r[21]
            purchase_at = r[22]
            created_at = r[23]
            completed_at = r[24]
            slots_used = r[25]
            slot_type_code = r[26]
            # Срок подписки обязателен для корректного открытия шеринга в режиме редактирования.
            if len(r) > 34:
                subscription_term_id = r[27]
                subscription_valid_until = r[28]
                reserve_key = r[29]
                notes = r[30]
                product_link = r[31]
                is_refund = bool(r[32])
                lock_version = int((r[33] if len(r) > 33 else 1) or 1)
                messenger_id = r[34]
            elif len(r) > 33:
                # Поддерживаем переходный формат строки без даты срока подписки.
                subscription_term_id = r[27]
                subscription_valid_until = None
                reserve_key = r[28]
                notes = r[29]
                product_link = r[30]
                is_refund = bool(r[31])
                lock_version = int((r[32] if len(r) > 32 else 1) or 1)
                messenger_id = r[33]
            else:
                # Поддерживаем старые тестовые строки без reserve_key.
                subscription_term_id = None
                subscription_valid_until = None
                reserve_key = None
                notes = r[27]
                product_link = r[28]
                is_refund = bool(r[29])
                lock_version = int((r[30] if len(r) > 30 else 1) or 1)
                messenger_id = None
            items.append(
                DealListItem(
                    deal_id=r[0],
                    lock_version=lock_version,
                    deal_type=r[1],
                    deal_type_code=r[2],
                    status=r[3],
                    flow_status_code=r[4],
                    flow_status=r[5],
                    order_number=r[6],
                    responsible_username=r[7],
                    region_code=r[8],
                    account_id=r[9],
                    account_login=login_full,
                    product_id=product_id,
                    product_title=product_title,
                    product_short_title=product_short_title,
                    platform_code=platform_code,
                    customer_nickname=customer_nickname,
                    login=login,
                    password=password,
                    source_id=source_id,
                    messenger_id=messenger_id,
                    price=float(price_value or 0),
                    purchase_cost=float(purchase_cost_value or 0),
                    purchase_at=purchase_at,
                    created_at=created_at,
                    completed_at=completed_at,
                    slots_used=slots_used,
                    slot_type_code=slot_type_code,
                    subscription_term_id=subscription_term_id,
                    subscription_valid_until=subscription_valid_until,
                    reserve_key=reserve_key,
                    notes=notes,
                    product_link=product_link,
                    is_refund=is_refund,
                )
            )
    
        return DealListOut(total=total, items=items)
    
