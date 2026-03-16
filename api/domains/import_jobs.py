from dataclasses import dataclass
from datetime import datetime, timezone
import os
import threading
from typing import Callable, Optional


@dataclass
class ImportJobs:
    run_games_import_job: Callable[[str, bytes, str], None]
    run_accounts_import_job: Callable[[str, bytes, str], None]
    run_slots_validate_job: Callable[[str, bytes, str, Optional[int]], None]
    run_slots_import_job: Callable[[str, bytes, str], None]


_MAX_IMPORT_JOBS = max(1, int(os.getenv("IMPORT_MAX_CONCURRENT_JOBS", "1") or "1"))
_IMPORT_JOBS_SEMAPHORE = threading.BoundedSemaphore(_MAX_IMPORT_JOBS)


def build_import_jobs(
    *,
    DB_DSN,
    psycopg,
    q1,
    exec1,
    read_games_from_excel,
    validate_game_import_rows,
    parse_import_platforms,
    get_platform_id,
    read_accounts_from_excel,
    validate_account_import_rows,
    split_account,
    b64_encode,
    get_platform_info,
    read_slots_from_excel,
    validate_slot_import_rows,
    normalize_cell_text,
    normalize_slot_file_value,
    SLOT_FILE_TO_TYPE,
    normalize_slot_date_to_dt,
    resolve_source_id,
    ensure_account_allows_slot_type,
    ensure_customer,
    is_import_cancelled,
    set_import_progress,
    MIN_DATE,
):
    # Ищет game-товар по названию и точному набору платформ.
    def find_game_product_by_title_platforms(conn, title: str, platform_codes: list[str]):
        if not title or not platform_codes:
            return None
        normalized_codes = sorted({str(code or "").strip().lower() for code in platform_codes if str(code or "").strip()})
        if not normalized_codes:
            return None
        # Сначала ищем точное совпадение по продукту и набору платформ.
        row = q1(
            conn,
            """
            SELECT p.product_id
            FROM app.products p
            JOIN app.product_platforms pp ON pp.product_id = p.product_id
            JOIN app.platforms pl ON pl.platform_id = pp.platform_id
            WHERE lower(p.title) = lower(%s)
              AND lower(p.type_code) = 'game'
              AND p.is_archived IS NOT TRUE
            GROUP BY p.product_id
            HAVING count(DISTINCT lower(pl.code)) = %s
               AND bool_and(lower(pl.code) = ANY(%s))
            ORDER BY p.product_id
            LIMIT 1
            """,
            (title, len(normalized_codes), normalized_codes),
        )
        if not row:
            # Если платформы еще не заполнены, избегаем дублей: берем единственный game-product по title.
            # Этот fallback безопасен только при единственном совпадении.
            row = q1(
                conn,
                """
                SELECT p.product_id
                FROM app.products p
                WHERE lower(p.title) = lower(%s)
                  AND lower(p.type_code) = 'game'
                  AND p.is_archived IS NOT TRUE
                ORDER BY p.product_id
                LIMIT 2
                """,
                (title,),
            )
            if not row:
                return None
            row2 = q1(
                conn,
                """
                SELECT p.product_id
                FROM app.products p
                WHERE lower(p.title) = lower(%s)
                  AND lower(p.type_code) = 'game'
                  AND p.is_archived IS NOT TRUE
                ORDER BY p.product_id
                OFFSET 1
                LIMIT 1
                """,
                (title,),
            )
            if row2:
                return None
        return int(row[0])

    # Резолвит игровой товар по названию для импорта только через product_id.
    def find_game_link_by_title(conn, title: str):
        if not title:
            return None
        row = q1(
            conn,
            """
            SELECT p.product_id
            FROM app.products p
            WHERE lower(p.title) = lower(%s)
              AND lower(p.type_code) = 'game'
              AND p.is_archived IS NOT TRUE
            ORDER BY p.product_id
            LIMIT 1
            """,
            (title,),
        )
        if not row:
            return None
        return int(row[0])

    def get_or_create_domain_id(conn, domain_name: str) -> int:
        row = q1(conn, "SELECT domain_id FROM app.domains WHERE name=%s", (domain_name,))
        if row:
            return int(row[0])
        row = q1(conn, "INSERT INTO app.domains(name) VALUES (%s) RETURNING domain_id", (domain_name,))
        return int(row[0])

    def ensure_account_platforms(conn, account_id: int):
        ps4_id, ps4_slots = get_platform_info(conn, "ps4")
        ps5_id, ps5_slots = get_platform_info(conn, "ps5")
        exec1(
            conn,
            """
            INSERT INTO app.account_platforms(account_id, platform_id, slot_capacity)
            VALUES (%s, %s, %s), (%s, %s, %s)
            ON CONFLICT (account_id, platform_id) DO UPDATE SET slot_capacity=excluded.slot_capacity
            """,
            (account_id, ps4_id, ps4_slots, account_id, ps5_id, ps5_slots),
        )

    def run_games_import_job(job_id: str, content: bytes, owner: str):
        acquired = _IMPORT_JOBS_SEMAPHORE.acquire(blocking=False)
        if not acquired:
            set_import_progress(
                job_id,
                owner,
                {
                    "phase": "error",
                    "current": 0,
                    "total": 0,
                    "done": True,
                    "result": {
                        "ok": False,
                        "errors": [{"row": 0, "field": "Импорт", "message": "Слишком много задач импорта. Повторите чуть позже."}],
                    },
                },
            )
            return
        try:
            with psycopg.connect(DB_DSN) as conn:
                rows = read_games_from_excel(content)
                errors, warnings = validate_game_import_rows(conn, rows)
                if errors:
                    set_import_progress(job_id, owner, {
                        "phase": "validate",
                        "current": len(rows),
                        "total": len(rows),
                        "done": True,
                        "result": {"ok": False, "total": len(rows), "errors": errors, "warnings": warnings},
                    })
                    return
                if is_import_cancelled(job_id):
                    set_import_progress(job_id, owner, {
                        "phase": "cancelled",
                        "current": 0,
                        "total": len(rows),
                        "done": True,
                        "cancelled": True,
                        "result": {"ok": False, "cancelled": True},
                    })
                    return
                total = len(rows)
                set_import_progress(job_id, owner, {"phase": "upload", "current": 0, "total": total, "done": False})
                created = 0
                updated = 0
                skipped = 0
                failed = 0
                last_success_row = None
                row_errors = []
                upload_done = 0
                existing_product_by_row = {}
                for idx, item in enumerate(rows, start=2):
                    # Подписки и "плюс" в листе игр намеренно не импортируем.
                    if bool(item.get("skip_for_import")):
                        continue
                    title = (item.get("title") or "").strip()
                    platform_codes = parse_import_platforms(item.get("platform_codes") or "")
                    existing_product = find_game_product_by_title_platforms(conn, title, platform_codes)
                    if existing_product:
                        existing_product_by_row[idx] = existing_product

                for idx, item in enumerate(rows, start=2):
                    if is_import_cancelled(job_id):
                        set_import_progress(job_id, owner, {
                            "phase": "cancelled",
                            "current": upload_done,
                            "total": total,
                            "done": True,
                            "cancelled": True,
                            "result": {"ok": False, "cancelled": True},
                        })
                        return
                    try:
                        title = (item.get("title") or "").strip()
                        # Подписки и "плюс" считаем пропущенными строками без ошибки.
                        if bool(item.get("skip_for_import")):
                            skipped += 1
                            upload_done += 1
                            set_import_progress(job_id, owner, {"phase": "upload", "current": upload_done, "total": total, "done": False})
                            continue
                        platform_codes = parse_import_platforms(item.get("platform_codes") or "")
                        if not platform_codes:
                            skipped += 1
                            upload_done += 1
                            set_import_progress(job_id, owner, {"phase": "upload", "current": upload_done, "total": total, "done": False})
                            continue
                        existing_product = existing_product_by_row.get(idx) or find_game_product_by_title_platforms(conn, title, platform_codes)
                        if existing_product:
                            product_id = int(existing_product)
                            updated += 1
                        else:
                            # Создаем товар в product-first режиме.
                            row = q1(
                                conn,
                                """
                                INSERT INTO app.products(type_code, title)
                                VALUES ('game', %s)
                                RETURNING product_id
                                """,
                                (title,),
                            )
                            product_id = int(row[0])
                            exec1(
                                conn,
                                "INSERT INTO app.game_products(product_id) VALUES (%s) ON CONFLICT (product_id) DO NOTHING",
                                (product_id,),
                            )
                            created += 1
                        # Синхронизируем title товара, чтобы импорт был идемпотентным.
                        exec1(conn, "UPDATE app.products SET title=%s WHERE product_id=%s", (title, product_id))
                        if platform_codes:
                            platform_ids = [get_platform_id(conn, code) for code in platform_codes]
                            with conn.cursor() as cur:
                                cur.executemany(
                                    "INSERT INTO app.product_platforms(product_id, platform_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                    [(product_id, pid) for pid in platform_ids],
                                )
                        conn.commit()
                        upload_done += 1
                        last_success_row = idx
                        set_import_progress(job_id, owner, {"phase": "upload", "current": upload_done, "total": total, "done": False})
                    except Exception as exc:
                        conn.rollback()
                        failed += 1
                        row_errors.append({"row": idx, "field": "Импорт", "message": str(exc)})
                        upload_done += 1
                        set_import_progress(job_id, owner, {"phase": "upload", "current": upload_done, "total": total, "done": False})
                        continue

                result = {
                    "ok": len(row_errors) == 0,
                    "total": len(rows),
                    "created": created,
                    "updated": updated,
                    "skipped": skipped,
                    "failed": failed,
                    "errors": row_errors,
                    "warnings": warnings,
                    "success_until_row": last_success_row,
                }
                set_import_progress(job_id, owner, {"phase": "upload", "current": total, "total": total, "done": True, "result": result})
        except Exception as exc:
            set_import_progress(job_id, owner, {"phase": "error", "current": 0, "total": 0, "done": True, "result": {"ok": False, "errors": [{"row": 0, "field": "Импорт", "message": str(exc)}]}})
        finally:
            _IMPORT_JOBS_SEMAPHORE.release()

    def run_accounts_import_job(job_id: str, content: bytes, owner: str):
        acquired = _IMPORT_JOBS_SEMAPHORE.acquire(blocking=False)
        if not acquired:
            set_import_progress(
                job_id,
                owner,
                {
                    "phase": "error",
                    "current": 0,
                    "total": 0,
                    "done": True,
                    "result": {
                        "ok": False,
                        "errors": [{"row": 0, "field": "Импорт", "message": "Слишком много задач импорта. Повторите чуть позже."}],
                    },
                },
            )
            return
        try:
            with psycopg.connect(DB_DSN) as conn:
                rows = read_accounts_from_excel(content)
                errors, warnings = validate_account_import_rows(conn, rows)
                if errors:
                    set_import_progress(job_id, owner, {"phase": "error", "current": 0, "total": 0, "done": True, "result": {"ok": False, "errors": errors, "warnings": warnings}})
                    return
                total = len(rows)
                set_import_progress(job_id, owner, {"phase": "upload", "current": 0, "total": total, "done": False})
                created = 0
                updated = 0
                skipped = 0
                failed = 0
                upload_done = 0
                last_success_row = None
                row_errors = []
                for idx, item in enumerate(rows, start=2):
                    if is_import_cancelled(job_id):
                        set_import_progress(job_id, owner, {"phase": "cancelled", "current": upload_done, "total": total, "done": True, "result": {"ok": False, "cancelled": True}})
                        return
                    report_sheet = str(item.get("_sheet_name") or "").strip() or None
                    report_row = int(item.get("_sheet_row") or idx)
                    try:
                        account_val = (item.get("account") or "").strip()
                        password = (item.get("password") or "").strip()
                        login, domain = split_account(account_val)
                        if not login or not domain:
                            skipped += 1
                            upload_done += 1
                            set_import_progress(job_id, owner, {"phase": "upload", "current": upload_done, "total": total, "done": False})
                            continue
                        domain_id = get_or_create_domain_id(conn, domain)
                        account_row = q1(
                            conn,
                            """
                            SELECT account_id
                            FROM app.accounts
                            WHERE login_name=%s AND domain_id=%s
                            """,
                            (login, domain_id),
                        )
                        if account_row:
                            account_id = int(account_row[0])
                            updated += 1
                        else:
                            row = q1(
                                conn,
                                """
                                INSERT INTO app.accounts(login_name, domain_id, status_code)
                                VALUES (%s, %s, 'active')
                                RETURNING account_id
                                """,
                                (login, domain_id),
                            )
                            account_id = int(row[0])
                            ensure_account_platforms(conn, account_id)
                            created += 1
                        if password:
                            exec1(
                                conn,
                                """
                                INSERT INTO app.account_secrets(account_id, secret_key, secret_value)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (account_id, secret_key)
                                DO UPDATE SET secret_value=excluded.secret_value
                                """,
                                (account_id, "account_password", b64_encode(password)),
                            )
                        # Сохраняем резервы как reserve1..reserve10, чтобы их можно было сразу использовать в сделках.
                        reserve_values = item.get("reserve_values") or {}
                        for reserve_idx in range(1, 11):
                            reserve_key = f"reserve{reserve_idx}"
                            reserve_raw = reserve_values.get(reserve_key, item.get(reserve_key))
                            reserve_val = str(reserve_raw or "").strip()
                            if not reserve_val:
                                continue
                            exec1(
                                conn,
                                """
                                INSERT INTO app.account_secrets(account_id, secret_key, secret_value)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (account_id, secret_key)
                                DO UPDATE SET secret_value=excluded.secret_value
                                """,
                                (account_id, reserve_key, b64_encode(reserve_val)),
                            )
                        conn.commit()
                        upload_done += 1
                        last_success_row = idx
                        set_import_progress(job_id, owner, {"phase": "upload", "current": upload_done, "total": total, "done": False})
                    except Exception as exc:
                        conn.rollback()
                        failed += 1
                        row_errors.append({"sheet": report_sheet, "row": report_row, "field": "Импорт", "message": str(exc)})
                        upload_done += 1
                        set_import_progress(job_id, owner, {"phase": "upload", "current": upload_done, "total": total, "done": False})
                result = {
                    "ok": len(row_errors) == 0,
                    "created": created,
                    "updated": updated,
                    "skipped": skipped,
                    "failed": failed,
                    "total": total,
                    "errors": row_errors,
                    "warnings": warnings,
                    "success_until_row": last_success_row,
                }
                set_import_progress(job_id, owner, {"phase": "upload", "current": total, "total": total, "done": True, "result": result})
        except Exception as exc:
            set_import_progress(job_id, owner, {"phase": "error", "current": 0, "total": 0, "done": True, "result": {"ok": False, "errors": [{"row": 0, "field": "Импорт", "message": str(exc)}]}})
        finally:
            _IMPORT_JOBS_SEMAPHORE.release()

    def run_slots_validate_job(job_id: str, content: bytes, owner: str, limit: Optional[int]):
        acquired = _IMPORT_JOBS_SEMAPHORE.acquire(blocking=False)
        if not acquired:
            set_import_progress(
                job_id,
                owner,
                {
                    "phase": "error",
                    "current": 0,
                    "total": 0,
                    "done": True,
                    "result": {
                        "ok": False,
                        "errors": [{"row": 0, "field": "Проверка", "message": "Слишком много задач импорта. Повторите чуть позже."}],
                    },
                },
            )
            return
        try:
            set_import_progress(job_id, owner, {"phase": "validate", "current": 0, "total": 0, "done": False})
            rows = read_slots_from_excel(content)
            if limit and limit > 0:
                rows = rows[:limit]
            total_rows = len(rows)
            set_import_progress(job_id, owner, {"phase": "validate", "current": 0, "total": total_rows, "done": False})
            with psycopg.connect(DB_DSN) as conn:
                errors, warnings, total = validate_slot_import_rows(
                    conn,
                    rows,
                    progress_cb=lambda current: set_import_progress(
                        job_id,
                        owner,
                        {"phase": "validate", "current": current, "total": total_rows, "done": False},
                    ),
                )
            result = {"ok": len(errors) == 0, "errors": errors, "warnings": warnings, "total": total}
            set_import_progress(job_id, owner, {"phase": "validate", "current": total_rows, "total": total_rows, "done": True, "result": result})
        except Exception as exc:
            set_import_progress(
                job_id,
                owner,
                {"phase": "error", "current": 0, "total": 0, "done": True, "result": {"ok": False, "errors": [{"row": 0, "field": "Проверка", "message": str(exc)}]}},
            )
        finally:
            _IMPORT_JOBS_SEMAPHORE.release()

    def run_slots_import_job(job_id: str, content: bytes, owner: str):
        acquired = _IMPORT_JOBS_SEMAPHORE.acquire(blocking=False)
        if not acquired:
            set_import_progress(
                job_id,
                owner,
                {
                    "phase": "error",
                    "current": 0,
                    "total": 0,
                    "done": True,
                    "result": {
                        "ok": False,
                        "errors": [{"row": 0, "field": "Импорт", "message": "Слишком много задач импорта. Повторите чуть позже."}],
                    },
                },
            )
            return
        try:
            with psycopg.connect(DB_DSN) as conn:
                rows = read_slots_from_excel(content)
                errors, warnings, total_valid = validate_slot_import_rows(conn, rows, progress_cb=None)
                if errors:
                    set_import_progress(job_id, owner, {"phase": "error", "current": 0, "total": 0, "done": True, "result": {"ok": False, "errors": errors, "warnings": warnings}})
                    return
                total = len(rows)
                set_import_progress(job_id, owner, {"phase": "upload", "current": 0, "total": total, "done": False})

                created = 0
                released = 0
                skipped = 0
                failed = 0
                upload_done = 0
                row_errors = []

                default_old_dt = datetime(MIN_DATE.year, MIN_DATE.month, MIN_DATE.day, tzinfo=timezone.utc)

                prepared = []
                for idx, row in enumerate(rows, start=2):
                    status_raw = row.get("status")
                    status = "" if status_raw is None else str(status_raw).strip().lower()
                    if not status or status == "свободен":
                        skipped += 1
                        prepared.append({"skip": True})
                        continue

                    account_val = normalize_cell_text(row.get("account"))
                    slot_val = normalize_cell_text(row.get("slot"))
                    game_title = normalize_cell_text(row.get("game"))
                    customer = normalize_cell_text(row.get("customer"))
                    source_val = normalize_cell_text(row.get("source"))
                    date_val = row.get("date")

                    if not account_val or not slot_val or not game_title:
                        skipped += 1
                        prepared.append({"skip": True})
                        continue

                    login, domain = split_account(account_val)
                    if not login or not domain:
                        skipped += 1
                        prepared.append({"skip": True})
                        continue

                    account_row = q1(
                        conn,
                        """
                        SELECT a.account_id
                        FROM app.accounts a
                        JOIN app.domains d ON d.domain_id = a.domain_id
                        WHERE lower(a.login_name) = lower(%s) AND lower(d.name) = lower(%s)
                        """,
                        (login, domain),
                    )
                    if not account_row:
                        skipped += 1
                        prepared.append({"skip": True})
                        continue
                    account_id = int(account_row[0])

                    # Резолвим товар по названию и дальше работаем только через product_id.
                    game_link = find_game_link_by_title(conn, game_title)
                    if game_link is None:
                        skipped += 1
                        prepared.append({"skip": True})
                        continue
                    product_id = game_link

                    slot_key = normalize_slot_file_value(slot_val)
                    slot_mapping = SLOT_FILE_TO_TYPE.get(slot_key)
                    if not slot_mapping:
                        skipped += 1
                        prepared.append({"skip": True})
                        continue
                    slot_type_code, slot_instance = slot_mapping

                    date_dt = normalize_slot_date_to_dt(date_val)
                    assigned_at = date_dt or default_old_dt
                    source_id = resolve_source_id(conn, source_val) if source_val else None

                    prepared.append({
                        "skip": False,
                        "row_idx": idx,
                        "account_id": account_id,
                        "product_id": product_id,
                        "slot_type_code": slot_type_code,
                        "slot_instance": slot_instance,
                        "customer": customer,
                        "source_id": source_id,
                        "assigned_at": assigned_at,
                        "completed_at": date_dt,
                    })

                groups = {}
                for item in prepared:
                    if item.get("skip"):
                        continue
                    key = (item["account_id"], item["product_id"], item["slot_type_code"], item.get("slot_instance"))
                    groups.setdefault(key, []).append(item)

                for key in groups:
                    groups[key].sort(key=lambda x: (x["assigned_at"], x["row_idx"]))

                upload_done = skipped
                set_import_progress(job_id, owner, {"phase": "upload", "current": upload_done, "total": total, "done": False})

                for key, items in groups.items():
                    prev_assignment_id = None
                    prev_assigned_at = None
                    for item in items:
                        if is_import_cancelled(job_id):
                            set_import_progress(job_id, owner, {"phase": "cancelled", "current": upload_done, "total": total, "done": True, "result": {"ok": False, "cancelled": True}})
                            return
                        try:
                            account_id = item["account_id"]
                            product_id = item["product_id"]
                            slot_type_code = item["slot_type_code"]
                            assigned_at = item["assigned_at"]
                            completed_at = item["completed_at"]
                            customer_nickname = item["customer"]
                            source_id = item["source_id"]

                            slot_type = ensure_account_allows_slot_type(conn, account_id, slot_type_code)
                            platform_id = get_platform_id(conn, slot_type[1])

                            customer_id = None
                            if customer_nickname:
                                customer_id = ensure_customer(conn, customer_nickname, source_id)

                            region_row = q1(conn, "SELECT region_id FROM app.accounts WHERE account_id=%s", (account_id,))
                            region_id = int(region_row[0]) if region_row and region_row[0] is not None else None

                            deal_row = q1(conn, """
                                INSERT INTO app.deals(
                                  deal_type_code, status_code, flow_status_code, region_id, customer_id, currency, total_amount, completed_at
                                )
                                VALUES ('rental', 'confirmed', 'completed', %s, %s, 'RUB', 0, %s)
                                RETURNING deal_id
                            """, (region_id, customer_id, completed_at))
                            deal_id = int(deal_row[0])

                            row_item = q1(conn, """
                                INSERT INTO app.deal_items(
                                  deal_id, account_id, product_id, platform_id,
                                  qty, price, purchase_cost, fee, purchase_at, start_at, end_at, slots_used, slot_type_code, notes, game_link
                                )
                                VALUES (%s, %s, %s, %s, 1, 0, 0, 0, %s, %s, NULL, 1, %s, NULL, NULL)
                                RETURNING deal_item_id
                            """, (
                                deal_id, account_id, product_id, platform_id,
                                completed_at, completed_at, slot_type_code
                            ))
                            deal_item_id = int(row_item[0])

                            assignment_row = q1(
                                conn,
                                """
                                INSERT INTO app.account_slot_assignments(
                                  account_id, slot_type_code, customer_id, product_id, deal_id, deal_item_id, assigned_at, assigned_by
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING assignment_id
                                """,
                                (account_id, slot_type_code, customer_id, product_id, deal_id, deal_item_id, assigned_at, owner),
                            )
                            assignment_id = int(assignment_row[0])

                            if prev_assignment_id is not None and prev_assigned_at is not None:
                                exec1(
                                    conn,
                                    """
                                    UPDATE app.account_slot_assignments
                                    SET released_at=%s, released_by=%s
                                    WHERE assignment_id=%s
                                    """,
                                    (assigned_at, owner, prev_assignment_id),
                                )
                                released += 1

                            conn.commit()
                            created += 1
                            prev_assignment_id = assignment_id
                            prev_assigned_at = assigned_at
                        except Exception as exc:
                            conn.rollback()
                            failed += 1
                            row_errors.append({"row": item.get("row_idx"), "field": "Импорт", "message": str(exc)})
                        finally:
                            upload_done += 1
                            set_import_progress(job_id, owner, {"phase": "upload", "current": upload_done, "total": total, "done": False})

                result = {
                    "ok": len(row_errors) == 0,
                    "created": created,
                    "released": released,
                    "skipped": skipped,
                    "failed": failed,
                    "total": total,
                    "errors": row_errors,
                    "warnings": warnings,
                }
                set_import_progress(job_id, owner, {"phase": "upload", "current": total, "total": total, "done": True, "result": result})
        except Exception as exc:
            set_import_progress(job_id, owner, {"phase": "error", "current": 0, "total": 0, "done": True, "result": {"ok": False, "errors": [{"row": 0, "field": "Импорт", "message": str(exc)}]}})
        finally:
            _IMPORT_JOBS_SEMAPHORE.release()

    return ImportJobs(
        run_games_import_job=run_games_import_job,
        run_accounts_import_job=run_accounts_import_job,
        run_slots_validate_job=run_slots_validate_job,
        run_slots_import_job=run_slots_import_job,
    )
