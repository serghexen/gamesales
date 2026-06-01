from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional
import json

from fastapi import Depends, HTTPException

from .finance_models import (
    FinanceBootstrapOut,
    FinanceCatalogSyncOut,
    FinanceEntryBulkErrorOut,
    FinanceEntryBulkIn,
    FinanceEntryBulkOut,
    FinanceEntryCreateIn,
    FinanceEntryListOut,
    FinanceEntryOut,
    FinanceFormulaCreateIn,
    FinanceFormulaOut,
    FinanceOperationOut,
    FinanceOperationCreateIn,
    FinanceOperationUpdateIn,
    FinancePnlBucketOut,
    FinancePnlOut,
    FinancePnlTotalsOut,
    FinanceProjectsReportOut,
    FinanceProjectsReportRowOut,
    FinanceProjectOut,
    FinanceProjectCreateIn,
    FinanceProjectUpdateIn,
    FinanceRegionOut,
    FinanceSectionOut,
    FinanceSectionCreateIn,
    FinanceSectionUpdateIn,
    FinanceSeedDefaultsOut,
    FinanceSourceOut,
    FinanceStatusOut,
    FinanceTypeOut,
    FinanceTypeCreateIn,
    FinanceTypeUpdateIn,
)


def mount_finance_routes(
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
    def _normalize_code(value: Optional[str], *, upper: bool = False) -> str:
        # Нормализуем кодовые поля, чтобы избежать лишних дублей из-за регистра и пробелов.
        text = (value or "").strip()
        return text.upper() if upper else text.lower()

    def _normalize_channel(value: Optional[str]) -> str:
        # Приводим канал ввода к допустимому значению по умолчанию.
        normalized = _normalize_code(value)
        if normalized in {"manual", "api", "bot", "import", "formula"}:
            return normalized
        return "manual"

    def _metric_from_section_kind(kind: str) -> str:
        # Преобразуем тип раздела в базовую метрику для P&L.
        mapping = {
            "revenue": "revenue",
            "direct_expense": "direct_expense",
            "indirect_expense": "indirect_expense",
            "other": "other",
        }
        return mapping.get((kind or "").strip(), "other")

    def _round_money(value: Decimal) -> Decimal:
        # Округляем денежные значения единообразно до двух знаков.
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _round_ratio(value: Decimal) -> Decimal:
        # Округляем долю/маржу до четырех знаков для отчетов.
        return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    def _normalize_section_kind(value: Optional[str]) -> str:
        # Нормализуем тип раздела и проверяем, что он поддерживается в v1.
        normalized = _normalize_code(value)
        allowed = {"revenue", "direct_expense", "indirect_expense", "other"}
        if normalized not in allowed:
            raise HTTPException(400, "kind must be one of: revenue, direct_expense, indirect_expense, other")
        return normalized

    def _resolve_section_type(conn, *, type_id: Optional[int], kind: Optional[str]) -> tuple[int, str]:
        # Определяем тип раздела по type_id (новый формат) или kind (обратная совместимость).
        if type_id is not None:
            row = q1(
                conn,
                "SELECT type_id, code FROM finance.section_types WHERE type_id=%s AND is_active IS TRUE",
                (int(type_id),),
            )
            if not row:
                raise HTTPException(400, f"Unknown type_id: {type_id}")
            return int(row[0]), str(row[1])
        normalized_kind = _normalize_section_kind(kind)
        row = q1(
            conn,
            "SELECT type_id, code FROM finance.section_types WHERE code=%s AND is_active IS TRUE",
            (normalized_kind,),
        )
        if not row:
            raise HTTPException(400, f"Unknown section type code: {normalized_kind}")
        return int(row[0]), str(row[1])

    def _normalize_operation_mode(value: Optional[str]) -> str:
        # Нормализуем режим ввода операции и ограничиваем его белым списком.
        normalized = _normalize_code(value)
        allowed = {"manual", "api", "bot", "formula", "mixed"}
        if normalized not in allowed:
            raise HTTPException(400, "input_mode must be one of: manual, api, bot, formula, mixed")
        return normalized

    def _ensure_lookup_exists(conn, table: str, id_name: str, id_value: Optional[int], field_name: str):
        # Проверяем, что переданный справочник существует и активен.
        if id_value is None:
            return
        row = q1(conn, f"SELECT 1 FROM finance.{table} WHERE {id_name}=%s AND is_active IS TRUE", (id_value,))
        if not row:
            raise HTTPException(400, f"Unknown {field_name}: {id_value}")

    def _to_section_out(row) -> FinanceSectionOut:
        # Приводим запись раздела к response-модели.
        return FinanceSectionOut(
            section_id=int(row[0]),
            parent_section_id=int(row[1]) if row[1] is not None else None,
            type_id=int(row[2]) if row[2] is not None else None,
            type_code=row[3],
            type_name=row[4],
            code=row[5],
            name=row[6],
            kind=row[7],
            sort_order=int(row[8] or 0),
            is_active=bool(row[9]),
        )

    def _to_type_out(row) -> FinanceTypeOut:
        # Приводим запись типа к response-модели.
        return FinanceTypeOut(
            type_id=int(row[0]),
            code=row[1],
            name=row[2],
            sort_order=int(row[3] or 0),
            is_active=bool(row[4]),
        )

    def _fetch_section_row(conn, section_id: int):
        # Загружаем раздел вместе с его типом для единого формата ответа.
        return q1(
            conn,
            """
            SELECT
              s.section_id,
              s.parent_section_id,
              s.type_id,
              t.code AS type_code,
              t.name AS type_name,
              s.code,
              s.name,
              s.kind,
              s.sort_order,
              s.is_active
            FROM finance.sections s
            JOIN finance.section_types t ON t.type_id = s.type_id
            WHERE s.section_id=%s
            """,
            (section_id,),
        )

    def _to_operation_out(row) -> FinanceOperationOut:
        # Приводим запись операции к response-модели.
        return FinanceOperationOut(
            operation_id=int(row[0]),
            type_id=int(row[1]),
            code=row[2],
            name=row[3],
            input_mode=row[4],
            requires_region=bool(row[5]),
            requires_source=bool(row[6]),
            requires_project=bool(row[7]),
            requires_qty=bool(row[8]),
            allows_negative=bool(row[9]),
            sort_order=int(row[10] or 0),
            is_active=bool(row[11]),
        )

    def _to_project_out(row) -> FinanceProjectOut:
        # Приводим запись проекта к response-модели.
        return FinanceProjectOut(
            project_id=int(row[0]),
            code=row[1],
            name=row[2],
            is_active=bool(row[3]),
        )

    def _to_formula_out(row) -> FinanceFormulaOut:
        # Приводим запись формулы к response-модели.
        return FinanceFormulaOut(
            formula_id=int(row[0]),
            operation_id=int(row[1]),
            version=int(row[2]),
            expression_json=row[3] or {},
            rounding_mode=row[4],
            scale=int(row[5]),
            effective_from=row[6],
            effective_to=row[7],
            is_active=bool(row[8]),
            comment=row[9],
            created_by=row[10] or "",
            created_at=row[11],
        )

    def _load_operation(conn, operation_id: int):
        # Загружаем операцию с типом, чтобы валидировать запись и выбрать метрику.
        row = q1(
            conn,
            """
            SELECT
              o.operation_id,
              o.type_id,
              o.code,
              o.name,
              o.input_mode,
              o.requires_region,
              o.requires_source,
              o.requires_project,
              o.requires_qty,
              o.allows_negative,
              o.sort_order,
              o.is_active,
              t.code AS type_code
            FROM finance.operations o
            JOIN finance.section_types t ON t.type_id = o.type_id
            WHERE o.operation_id=%s
            """,
            (operation_id,),
        )
        if not row:
            raise HTTPException(400, f"Unknown operation_id: {operation_id}")
        if row[11] is not True:
            raise HTTPException(400, f"Inactive operation_id: {operation_id}")
        return {
            "operation_id": int(row[0]),
            "type_id": int(row[1]),
            "code": row[2],
            "name": row[3],
            "input_mode": row[4],
            "requires_region": bool(row[5]),
            "requires_source": bool(row[6]),
            "requires_project": bool(row[7]),
            "requires_qty": bool(row[8]),
            "allows_negative": bool(row[9]),
            "sort_order": int(row[10] or 0),
            "is_active": bool(row[11]),
            "type_code": row[12],
        }

    def _validate_entry_payload(conn, payload: FinanceEntryCreateIn, operation: dict[str, Any]):
        # Проверяем обязательные измерения по правилам операции.
        if operation["requires_region"] and payload.region_id is None:
            raise HTTPException(400, "region_id is required for operation")
        if operation["requires_source"] and payload.source_id is None:
            raise HTTPException(400, "source_id is required for operation")
        # Поле проекта убрано из UI, поэтому проект больше не блокирует ввод записи.
        if operation["requires_qty"] and payload.qty == 0:
            raise HTTPException(400, "qty must be non-zero for operation")
        if operation["allows_negative"] is not True and payload.amount < 0:
            raise HTTPException(400, "amount must be >= 0 for operation")

        # Проверяем справочники, чтобы не записывать «битые» измерения.
        _ensure_lookup_exists(conn, "dim_regions", "region_id", payload.region_id, "region_id")
        _ensure_lookup_exists(conn, "dim_sources", "source_id", payload.source_id, "source_id")
        _ensure_lookup_exists(conn, "projects", "project_id", payload.project_id, "project_id")

        status_code = _normalize_code(payload.status_code)
        status_row = q1(conn, "SELECT 1 FROM finance.entry_statuses WHERE code=%s", (status_code,))
        if not status_row:
            raise HTTPException(400, f"Unknown status_code: {payload.status_code}")

    def _to_entry_out(row) -> FinanceEntryOut:
        # Преобразуем строку SQL в модель ответа API.
        return FinanceEntryOut(
            entry_id=int(row[0]),
            biz_date=row[1],
            operation_id=int(row[2]),
            region_id=int(row[3]) if row[3] is not None else None,
            source_id=int(row[4]) if row[4] is not None else None,
            project_id=int(row[5]) if row[5] is not None else None,
            qty=Decimal(row[6] or 0),
            amount=Decimal(row[7] or 0),
            currency=row[8],
            input_channel=row[9],
            external_key=row[10],
            status_code=row[11],
            comment=row[12],
            created_by=row[13] or "",
            created_at=row[14],
            updated_at=row[15],
        )

    def _create_entry_in_tx(conn, payload: FinanceEntryCreateIn, created_by: str) -> tuple[FinanceEntryOut, bool]:
        # Создаем запись в открытой транзакции; возвращаем запись и флаг "создана новая".
        if payload.biz_date > date.today():
            raise HTTPException(400, f"biz_date must be <= {date.today().isoformat()}")
        if str(payload.currency or "").strip().upper() == "":
            raise HTTPException(400, "currency is required")

        operation = _load_operation(conn, payload.operation_id)
        _validate_entry_payload(conn, payload, operation)

        channel = _normalize_channel(payload.input_channel)
        external_key = (payload.external_key or "").strip() or None
        status_code = _normalize_code(payload.status_code)

        # Если ключ уже встречался, возвращаем существующую запись для идемпотентности.
        if external_key:
            existing = q1(
                conn,
                """
                SELECT e.entry_id, e.biz_date, e.operation_id, e.region_id, e.source_id, e.project_id,
                       e.qty, e.amount, e.currency, e.input_channel, e.external_key, e.status_code,
                       e.comment, e.created_by, e.created_at, e.updated_at
                FROM finance.entry_dedupe_keys d
                JOIN finance.entries e
                  ON e.entry_id = d.entry_id
                 AND e.biz_date = d.entry_biz_date
                WHERE d.input_channel=%s AND d.external_key=%s
                """,
                (channel, external_key),
            )
            if existing:
                return _to_entry_out(existing), False

        entry_row = q1(
            conn,
            """
            INSERT INTO finance.entries(
              biz_date, operation_id, region_id, source_id, project_id,
              qty, amount, currency, input_channel, external_key, status_code,
              comment, payload_json, app_deal_id, app_deal_item_id, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
            RETURNING entry_id, biz_date, operation_id, region_id, source_id, project_id,
                      qty, amount, currency, input_channel, external_key, status_code,
                      comment, created_by, created_at, updated_at
            """,
            (
                payload.biz_date,
                payload.operation_id,
                payload.region_id,
                payload.source_id,
                payload.project_id,
                payload.qty,
                _round_money(payload.amount),
                _normalize_code(payload.currency, upper=True),
                channel,
                external_key,
                status_code,
                (payload.comment or "").strip() or None,
                json.dumps(payload.payload_json or {}),
                payload.app_deal_id,
                payload.app_deal_item_id,
                created_by,
            ),
        )
        if not entry_row:
            raise HTTPException(500, "Failed to create finance entry")

        # Сохраняем реестр идемпотентности после успешной вставки записи.
        if external_key:
            exec1(
                conn,
                """
                INSERT INTO finance.entry_dedupe_keys(input_channel, external_key, entry_id, entry_biz_date)
                VALUES (%s, %s, %s, %s)
                """,
                (channel, external_key, entry_row[0], entry_row[1]),
            )

        # Сохраняем базовую проводку, чтобы отчет сразу увидел сумму.
        metric_code = _metric_from_section_kind(operation["type_code"])
        exec1(
            conn,
            """
            INSERT INTO finance.entry_postings(entry_id, entry_biz_date, metric_code, amount)
            VALUES (%s, %s, %s, %s)
            """,
            (entry_row[0], entry_row[1], metric_code, _round_money(payload.amount)),
        )

        # Пишем аудит, чтобы было видно кто и что внес.
        exec1(
            conn,
            """
            INSERT INTO finance.entry_audit(entry_id, entry_biz_date, action, changed_by, new_data)
            VALUES (%s, %s, 'insert', %s, %s::jsonb)
            """,
            (
                entry_row[0],
                entry_row[1],
                created_by,
                json.dumps(
                    {
                        "biz_date": str(payload.biz_date),
                        "operation_id": payload.operation_id,
                        "region_id": payload.region_id,
                        "source_id": payload.source_id,
                        "project_id": payload.project_id,
                        "qty": str(payload.qty),
                        "amount": str(_round_money(payload.amount)),
                        "status_code": status_code,
                    }
                ),
            ),
        )
        return _to_entry_out(entry_row), True

    @app.get("/finance/catalogs/bootstrap", response_model=FinanceBootstrapOut)
    def finance_catalogs_bootstrap(user=Depends(get_current_user)):
        # Отдаем набор справочников одним запросом, чтобы фронт быстро строил формы.
        with psycopg.connect(DB_DSN) as conn:
            type_rows = qall(
                conn,
                """
                SELECT type_id, code, name, sort_order, is_active
                FROM finance.section_types
                WHERE is_active IS TRUE
                ORDER BY sort_order, type_id
                """,
            )
            section_rows = qall(
                conn,
                """
                SELECT
                  s.section_id,
                  s.parent_section_id,
                  s.type_id,
                  t.code AS type_code,
                  t.name AS type_name,
                  s.code,
                  s.name,
                  s.kind,
                  s.sort_order,
                  s.is_active
                FROM finance.sections s
                JOIN finance.section_types t ON t.type_id = s.type_id
                WHERE s.is_active IS TRUE
                ORDER BY s.sort_order, s.section_id
                """,
            )
            operation_rows = qall(
                conn,
                """
                SELECT
                  operation_id, type_id, code, name, input_mode,
                  requires_region, requires_source, requires_project, requires_qty,
                  allows_negative, sort_order, is_active
                FROM finance.operations
                WHERE is_active IS TRUE
                ORDER BY sort_order, operation_id
                """,
            )
            project_rows = qall(
                conn,
                """
                SELECT project_id, code, name, is_active
                FROM finance.projects
                WHERE is_active IS TRUE
                ORDER BY code
                """,
            )
            region_rows = qall(
                conn,
                """
                SELECT region_id, code, name, is_active
                FROM finance.dim_regions
                WHERE is_active IS TRUE
                ORDER BY code
                """,
            )
            source_rows = qall(
                conn,
                """
                SELECT source_id, code, name, is_active
                FROM finance.dim_sources
                WHERE is_active IS TRUE
                ORDER BY code
                """,
            )
            status_rows = qall(conn, "SELECT code, name FROM finance.entry_statuses ORDER BY code")

        return FinanceBootstrapOut(
            types=[_to_type_out(r) for r in type_rows],
            sections=[
                _to_section_out(r)
                for r in section_rows
            ],
            operations=[
                FinanceOperationOut(
                    operation_id=int(r[0]),
                    type_id=int(r[1]),
                    code=r[2],
                    name=r[3],
                    input_mode=r[4],
                    requires_region=bool(r[5]),
                    requires_source=bool(r[6]),
                    requires_project=bool(r[7]),
                    requires_qty=bool(r[8]),
                    allows_negative=bool(r[9]),
                    sort_order=int(r[10] or 0),
                    is_active=bool(r[11]),
                )
                for r in operation_rows
            ],
            projects=[
                FinanceProjectOut(
                    project_id=int(r[0]),
                    code=r[1],
                    name=r[2],
                    is_active=bool(r[3]),
                )
                for r in project_rows
            ],
            regions=[
                FinanceRegionOut(
                    region_id=int(r[0]),
                    code=r[1],
                    name=r[2],
                    is_active=bool(r[3]),
                )
                for r in region_rows
            ],
            sources=[
                FinanceSourceOut(
                    source_id=int(r[0]),
                    code=r[1],
                    name=r[2],
                    is_active=bool(r[3]),
                )
                for r in source_rows
            ],
            statuses=[FinanceStatusOut(code=r[0], name=r[1]) for r in status_rows],
        )

    @app.post("/finance/catalogs/sync-from-app", response_model=FinanceCatalogSyncOut)
    def finance_sync_catalogs_from_app(user=Depends(require_role("admin", "owner"))):
        # Синхронизируем измерения из app, чтобы справочники finance не расходились с операционным контуром.
        synced_regions = 0
        synced_sources = 0
        with psycopg.connect(DB_DSN) as conn:
            region_rows = qall(
                conn,
                """
                SELECT region_id, code, name
                FROM app.regions
                WHERE is_archived IS NOT TRUE
                ORDER BY region_id
                """,
            )
            for app_region_id, code, name in region_rows:
                exec1(
                    conn,
                    """
                    INSERT INTO finance.dim_regions(code, name, app_region_id, is_active)
                    VALUES (%s, %s, %s, true)
                    ON CONFLICT (code) DO UPDATE
                    SET name=excluded.name,
                        app_region_id=excluded.app_region_id,
                        is_active=true,
                        updated_at=now()
                    """,
                    (_normalize_code(code, upper=True), str(name or "").strip(), int(app_region_id)),
                )
                synced_regions += 1

            source_rows = qall(
                conn,
                """
                SELECT source_id, code, name
                FROM app.sources
                WHERE is_archived IS NOT TRUE
                ORDER BY source_id
                """,
            )
            for app_source_id, code, name in source_rows:
                exec1(
                    conn,
                    """
                    INSERT INTO finance.dim_sources(code, name, app_source_id, is_active)
                    VALUES (%s, %s, %s, true)
                    ON CONFLICT (app_source_id) DO UPDATE
                    SET name=excluded.name,
                        code=excluded.code,
                        is_active=true,
                        updated_at=now()
                    """,
                    (_normalize_code(code), str(name or "").strip(), int(app_source_id)),
                )
                synced_sources += 1
            conn.commit()
        return FinanceCatalogSyncOut(regions_synced=synced_regions, sources_synced=synced_sources)

    @app.post("/finance/catalogs/seed-defaults", response_model=FinanceSeedDefaultsOut)
    def finance_seed_defaults(user=Depends(require_role("admin", "owner"))):
        # Заполняем базовый набор разделов/операций/проектов для быстрого старта аналитики.
        sections_seeded = 0
        operations_seeded = 0
        projects_seeded = 0
        with psycopg.connect(DB_DSN) as conn:
            type_specs = [
                {"code": "revenue", "name": "Выручка", "sort_order": 10},
                {"code": "direct_expense", "name": "Прямые расходы", "sort_order": 20},
                {"code": "indirect_expense", "name": "Косвенные расходы", "sort_order": 30},
            ]
            for spec in type_specs:
                exec1(
                    conn,
                    """
                    INSERT INTO finance.section_types(code, name, sort_order, is_active)
                    VALUES (%s, %s, %s, true)
                    ON CONFLICT (code) DO UPDATE
                    SET name=excluded.name,
                        sort_order=excluded.sort_order,
                        is_active=true,
                        updated_at=now()
                    """,
                    (spec["code"], spec["name"], spec["sort_order"]),
                )

            type_rows = qall(conn, "SELECT type_id, code FROM finance.section_types WHERE is_active IS TRUE")
            type_map = {str(code): int(type_id) for type_id, code in type_rows}
            section_specs = [
                {"code": "revenue", "name": "Выручка", "type_code": "revenue", "sort_order": 10},
                {"code": "direct_expense", "name": "Прямые расходы", "type_code": "direct_expense", "sort_order": 20},
                {"code": "indirect_expense", "name": "Косвенные расходы", "type_code": "indirect_expense", "sort_order": 30},
            ]
            for spec in section_specs:
                type_id = type_map.get(spec["type_code"])
                if not type_id:
                    continue
                exec1(
                    conn,
                    """
                    INSERT INTO finance.sections(parent_section_id, type_id, code, name, kind, sort_order, is_active)
                    VALUES (NULL, %s, %s, %s, %s, %s, true)
                    ON CONFLICT (code) DO UPDATE
                    SET type_id=excluded.type_id,
                        parent_section_id=excluded.parent_section_id,
                        name=excluded.name,
                        kind=excluded.kind,
                        sort_order=excluded.sort_order,
                        is_active=true,
                        updated_at=now()
                    """,
                    (type_id, spec["code"], spec["name"], spec["type_code"], spec["sort_order"]),
                )
                sections_seeded += 1

            operation_specs = [
                {"code": "revenue_sales_manual", "name": "Продажи (ручной ввод)", "type_code": "revenue"},
                {"code": "revenue_marketplace_api", "name": "Продажи маркетплейсов (API)", "type_code": "revenue"},
                {"code": "direct_purchase", "name": "Закуп", "type_code": "direct_expense"},
                {"code": "direct_salary_piece", "name": "Сдельные выплаты", "type_code": "direct_expense"},
                {"code": "indirect_marketing", "name": "Маркетинг", "type_code": "indirect_expense"},
                {"code": "indirect_office", "name": "Офис и сервисы", "type_code": "indirect_expense"},
            ]
            for idx, spec in enumerate(operation_specs, start=1):
                type_id = type_map.get(spec["type_code"])
                if not type_id:
                    continue
                exec1(
                    conn,
                    """
                    INSERT INTO finance.operations(
                      type_id, code, name, input_mode,
                      requires_region, requires_source, requires_project, requires_qty, allows_negative,
                      sort_order, is_active
                    )
                    VALUES (%s, %s, %s, 'mixed', false, false, true, false, false, %s, true)
                    ON CONFLICT (code) DO UPDATE
                    SET name=excluded.name,
                        type_id=excluded.type_id,
                        input_mode=excluded.input_mode,
                        requires_region=excluded.requires_region,
                        requires_source=excluded.requires_source,
                        requires_project=excluded.requires_project,
                        requires_qty=excluded.requires_qty,
                        allows_negative=excluded.allows_negative,
                        sort_order=excluded.sort_order,
                        is_active=true,
                        updated_at=now()
                    """,
                    (type_id, spec["code"], spec["name"], idx * 10),
                )
                operations_seeded += 1

            project_specs = [
                {"code": "core", "name": "Core"},
                {"code": "marketplace", "name": "Marketplace"},
                {"code": "operations", "name": "Operations"},
            ]
            for spec in project_specs:
                exec1(
                    conn,
                    """
                    INSERT INTO finance.projects(code, name, is_active)
                    VALUES (%s, %s, true)
                    ON CONFLICT (code) DO UPDATE
                    SET name=excluded.name,
                        is_active=true,
                        updated_at=now()
                    """,
                    (spec["code"], spec["name"]),
                )
                projects_seeded += 1
            conn.commit()
        return FinanceSeedDefaultsOut(
            sections_seeded=sections_seeded,
            operations_seeded=operations_seeded,
            projects_seeded=projects_seeded,
        )

    @app.post("/finance/catalogs/types", response_model=FinanceTypeOut)
    def finance_create_type(payload: FinanceTypeCreateIn, user=Depends(require_role("admin", "owner"))):
        # Создаем новый тип верхнего уровня для классификации P&L.
        code = _normalize_code(payload.code)
        name = (payload.name or "").strip()
        if not code or not name:
            raise HTTPException(400, "code and name are required")
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                INSERT INTO finance.section_types(code, name, sort_order, is_active)
                VALUES (%s, %s, %s, true)
                RETURNING type_id, code, name, sort_order, is_active
                """,
                (code, name, int(payload.sort_order or 0)),
            )
            conn.commit()
        if not row:
            raise HTTPException(500, "Failed to create type")
        return _to_type_out(row)

    @app.put("/finance/catalogs/types/{type_id}", response_model=FinanceTypeOut)
    def finance_update_type(type_id: int, payload: FinanceTypeUpdateIn, user=Depends(require_role("admin", "owner"))):
        # Обновляем тип с защитой системных кодов от случайного переименования.
        with psycopg.connect(DB_DSN) as conn:
            current = q1(
                conn,
                "SELECT type_id, code, name, sort_order, is_active FROM finance.section_types WHERE type_id=%s",
                (type_id,),
            )
            if not current:
                raise HTTPException(404, "Type not found")
            protected_codes = {"revenue", "direct_expense", "indirect_expense"}
            next_code = _normalize_code(payload.code) if payload.code is not None else current[1]
            if current[1] in protected_codes and next_code != current[1]:
                raise HTTPException(400, "System type code cannot be changed")
            next_name = (payload.name or "").strip() if payload.name is not None else current[2]
            next_sort = int(payload.sort_order) if payload.sort_order is not None else int(current[3] or 0)
            next_active = bool(payload.is_active) if payload.is_active is not None else bool(current[4])
            row = q1(
                conn,
                """
                UPDATE finance.section_types
                SET code=%s, name=%s, sort_order=%s, is_active=%s, updated_at=now()
                WHERE type_id=%s
                RETURNING type_id, code, name, sort_order, is_active
                """,
                (next_code, next_name, next_sort, next_active, type_id),
            )
            conn.commit()
        if not row:
            raise HTTPException(500, "Failed to update type")
        return _to_type_out(row)

    @app.delete("/finance/catalogs/types/{type_id}")
    def finance_delete_type(type_id: int, user=Depends(require_role("admin", "owner"))):
        # Архивируем тип, если к нему не привязаны активные разделы.
        with psycopg.connect(DB_DSN) as conn:
            current = q1(conn, "SELECT code FROM finance.section_types WHERE type_id=%s", (type_id,))
            if not current:
                raise HTTPException(404, "Type not found")
            if current[0] in {"revenue", "direct_expense", "indirect_expense"}:
                raise HTTPException(400, "System type cannot be deleted")
            has_sections = q1(
                conn,
                "SELECT 1 FROM finance.sections WHERE type_id=%s AND is_active IS TRUE LIMIT 1",
                (type_id,),
            )
            if has_sections:
                raise HTTPException(409, "Type has active sections")
            exec1(conn, "UPDATE finance.section_types SET is_active=false, updated_at=now() WHERE type_id=%s", (type_id,))
            conn.commit()
        return {"ok": True}

    @app.post("/finance/catalogs/sections", response_model=FinanceSectionOut)
    def finance_create_section(payload: FinanceSectionCreateIn, user=Depends(require_role("admin", "owner"))):
        # Создаем раздел-категорию и связываем его с типом P&L.
        code = _normalize_code(payload.code)
        name = (payload.name or "").strip()
        if not code or not name:
            raise HTTPException(400, "code and name are required")
        with psycopg.connect(DB_DSN) as conn:
            type_id, type_code = _resolve_section_type(conn, type_id=payload.type_id, kind=payload.kind)
            if payload.parent_section_id is not None:
                _ensure_lookup_exists(conn, "sections", "section_id", payload.parent_section_id, "parent_section_id")
            row = q1(
                conn,
                """
                INSERT INTO finance.sections(parent_section_id, type_id, code, name, kind, sort_order, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, true)
                RETURNING section_id
                """,
                (
                    payload.parent_section_id,
                    type_id,
                    code,
                    name,
                    payload.kind or type_code,
                    payload.sort_order,
                ),
            )
            full_row = _fetch_section_row(conn, int((row or [0])[0] or 0)) if row else None
            conn.commit()
        if not full_row:
            raise HTTPException(500, "Failed to create section")
        return _to_section_out(full_row)

    @app.put("/finance/catalogs/sections/{section_id}", response_model=FinanceSectionOut)
    def finance_update_section(section_id: int, payload: FinanceSectionUpdateIn, user=Depends(require_role("admin", "owner"))):
        # Обновляем раздел и сохраняем текущее значение полей, если новое не передано.
        with psycopg.connect(DB_DSN) as conn:
            current = q1(
                conn,
                """
                SELECT
                  s.section_id,
                  s.parent_section_id,
                  s.type_id,
                  t.code AS type_code,
                  s.code,
                  s.name,
                  s.kind,
                  s.sort_order,
                  s.is_active
                FROM finance.sections s
                JOIN finance.section_types t ON t.type_id = s.type_id
                WHERE s.section_id=%s
                """,
                (section_id,),
            )
            if not current:
                raise HTTPException(404, "Section not found")
            next_parent = payload.parent_section_id if payload.parent_section_id is not None else current[1]
            if next_parent == section_id:
                raise HTTPException(400, "parent_section_id cannot be self")
            if payload.parent_section_id is not None:
                _ensure_lookup_exists(conn, "sections", "section_id", payload.parent_section_id, "parent_section_id")
            if payload.type_id is not None or payload.kind is not None:
                next_type_id, next_type_code = _resolve_section_type(conn, type_id=payload.type_id, kind=payload.kind)
            else:
                next_type_id = int(current[2])
                next_type_code = str(current[3])
            next_code = _normalize_code(payload.code) if payload.code is not None else current[4]
            next_name = (payload.name or "").strip() if payload.name is not None else current[5]
            next_kind = _normalize_section_kind(payload.kind) if payload.kind is not None else next_type_code
            next_sort = int(payload.sort_order) if payload.sort_order is not None else int(current[7] or 0)
            next_active = bool(payload.is_active) if payload.is_active is not None else bool(current[8])
            row = q1(
                conn,
                """
                UPDATE finance.sections
                SET parent_section_id=%s, type_id=%s, code=%s, name=%s, kind=%s, sort_order=%s, is_active=%s, updated_at=now()
                WHERE section_id=%s
                RETURNING section_id
                """,
                (
                    next_parent,
                    next_type_id,
                    next_code,
                    next_name,
                    next_kind,
                    next_sort,
                    next_active,
                    section_id,
                ),
            )
            full_row = _fetch_section_row(conn, int((row or [0])[0] or 0)) if row else None
            conn.commit()
        if not full_row:
            raise HTTPException(500, "Failed to update section")
        return _to_section_out(full_row)

    @app.delete("/finance/catalogs/sections/{section_id}")
    def finance_delete_section(section_id: int, user=Depends(require_role("admin", "owner"))):
        # Архивируем раздел только если нет активных дочерних сущностей.
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT 1 FROM finance.sections WHERE section_id=%s", (section_id,))
            if not row:
                raise HTTPException(404, "Section not found")
            child = q1(conn, "SELECT 1 FROM finance.sections WHERE parent_section_id=%s AND is_active IS TRUE", (section_id,))
            if child:
                raise HTTPException(409, "Section has active child sections")
            op = q1(conn, "SELECT 1 FROM finance.operations WHERE section_id=%s AND is_active IS TRUE", (section_id,))
            if op:
                raise HTTPException(409, "Section has active operations")
            exec1(conn, "UPDATE finance.sections SET is_active=false, updated_at=now() WHERE section_id=%s", (section_id,))
            conn.commit()
        return {"ok": True}

    @app.post("/finance/catalogs/operations", response_model=FinanceOperationOut)
    def finance_create_operation(payload: FinanceOperationCreateIn, user=Depends(require_role("admin", "owner"))):
        # Создаем операцию и фиксируем правила обязательных полей.
        code = _normalize_code(payload.code)
        name = (payload.name or "").strip()
        if not code or not name:
            raise HTTPException(400, "code and name are required")
        input_mode = _normalize_operation_mode(payload.input_mode)
        with psycopg.connect(DB_DSN) as conn:
            _ensure_lookup_exists(conn, "section_types", "type_id", payload.type_id, "type_id")
            row = q1(
                conn,
                """
                INSERT INTO finance.operations(
                  type_id, code, name, input_mode,
                  requires_region, requires_source, requires_project, requires_qty, allows_negative,
                  sort_order, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)
                RETURNING operation_id, type_id, code, name, input_mode,
                          requires_region, requires_source, requires_project, requires_qty,
                          allows_negative, sort_order, is_active
                """,
                (
                    payload.type_id,
                    code,
                    name,
                    input_mode,
                    payload.requires_region,
                    payload.requires_source,
                    payload.requires_project,
                    payload.requires_qty,
                    payload.allows_negative,
                    payload.sort_order,
                ),
            )
            conn.commit()
        if not row:
            raise HTTPException(500, "Failed to create operation")
        return _to_operation_out(row)

    @app.put("/finance/catalogs/operations/{operation_id}", response_model=FinanceOperationOut)
    def finance_update_operation(operation_id: int, payload: FinanceOperationUpdateIn, user=Depends(require_role("admin", "owner"))):
        # Обновляем операцию, сохраняя текущие значения для неуказанных полей.
        with psycopg.connect(DB_DSN) as conn:
            current = q1(
                conn,
                """
                SELECT operation_id, type_id, code, name, input_mode,
                       requires_region, requires_source, requires_project, requires_qty,
                       allows_negative, sort_order, is_active
                FROM finance.operations
                WHERE operation_id=%s
                """,
                (operation_id,),
            )
            if not current:
                raise HTTPException(404, "Operation not found")
            next_type_id = int(payload.type_id) if payload.type_id is not None else int(current[1])
            _ensure_lookup_exists(conn, "section_types", "type_id", next_type_id, "type_id")
            next_code = _normalize_code(payload.code) if payload.code is not None else current[2]
            next_name = (payload.name or "").strip() if payload.name is not None else current[3]
            next_mode = _normalize_operation_mode(payload.input_mode) if payload.input_mode is not None else current[4]
            next_requires_region = bool(payload.requires_region) if payload.requires_region is not None else bool(current[5])
            next_requires_source = bool(payload.requires_source) if payload.requires_source is not None else bool(current[6])
            next_requires_project = bool(payload.requires_project) if payload.requires_project is not None else bool(current[7])
            next_requires_qty = bool(payload.requires_qty) if payload.requires_qty is not None else bool(current[8])
            next_allows_negative = bool(payload.allows_negative) if payload.allows_negative is not None else bool(current[9])
            next_sort = int(payload.sort_order) if payload.sort_order is not None else int(current[10] or 0)
            next_active = bool(payload.is_active) if payload.is_active is not None else bool(current[11])
            row = q1(
                conn,
                """
                UPDATE finance.operations
                SET type_id=%s, code=%s, name=%s, input_mode=%s,
                    requires_region=%s, requires_source=%s, requires_project=%s, requires_qty=%s,
                    allows_negative=%s, sort_order=%s, is_active=%s, updated_at=now()
                WHERE operation_id=%s
                RETURNING operation_id, type_id, code, name, input_mode,
                          requires_region, requires_source, requires_project, requires_qty,
                          allows_negative, sort_order, is_active
                """,
                (
                    next_type_id,
                    next_code,
                    next_name,
                    next_mode,
                    next_requires_region,
                    next_requires_source,
                    next_requires_project,
                    next_requires_qty,
                    next_allows_negative,
                    next_sort,
                    next_active,
                    operation_id,
                ),
            )
            conn.commit()
        if not row:
            raise HTTPException(500, "Failed to update operation")
        return _to_operation_out(row)

    @app.delete("/finance/catalogs/operations/{operation_id}")
    def finance_delete_operation(operation_id: int, user=Depends(require_role("admin", "owner"))):
        # Архивируем операцию только если на нее нет записей в учете.
        with psycopg.connect(DB_DSN) as conn:
            current = q1(conn, "SELECT 1 FROM finance.operations WHERE operation_id=%s", (operation_id,))
            if not current:
                raise HTTPException(404, "Operation not found")
            has_entries = q1(conn, "SELECT 1 FROM finance.entries WHERE operation_id=%s LIMIT 1", (operation_id,))
            if has_entries:
                raise HTTPException(409, "Operation has entries and cannot be deleted")
            exec1(conn, "UPDATE finance.operations SET is_active=false, updated_at=now() WHERE operation_id=%s", (operation_id,))
            conn.commit()
        return {"ok": True}

    @app.post("/finance/catalogs/projects", response_model=FinanceProjectOut)
    def finance_create_project(payload: FinanceProjectCreateIn, user=Depends(require_role("admin", "owner"))):
        # Создаем проект для отчетной группировки.
        code = _normalize_code(payload.code)
        name = (payload.name or "").strip()
        if not code or not name:
            raise HTTPException(400, "code and name are required")
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                INSERT INTO finance.projects(code, name, is_active)
                VALUES (%s, %s, true)
                RETURNING project_id, code, name, is_active
                """,
                (code, name),
            )
            conn.commit()
        if not row:
            raise HTTPException(500, "Failed to create project")
        return _to_project_out(row)

    @app.put("/finance/catalogs/projects/{project_id}", response_model=FinanceProjectOut)
    def finance_update_project(project_id: int, payload: FinanceProjectUpdateIn, user=Depends(require_role("admin", "owner"))):
        # Обновляем проект с сохранением старых значений по неуказанным полям.
        with psycopg.connect(DB_DSN) as conn:
            current = q1(conn, "SELECT project_id, code, name, is_active FROM finance.projects WHERE project_id=%s", (project_id,))
            if not current:
                raise HTTPException(404, "Project not found")
            next_code = _normalize_code(payload.code) if payload.code is not None else current[1]
            next_name = (payload.name or "").strip() if payload.name is not None else current[2]
            next_active = bool(payload.is_active) if payload.is_active is not None else bool(current[3])
            row = q1(
                conn,
                """
                UPDATE finance.projects
                SET code=%s, name=%s, is_active=%s, updated_at=now()
                WHERE project_id=%s
                RETURNING project_id, code, name, is_active
                """,
                (next_code, next_name, next_active, project_id),
            )
            conn.commit()
        if not row:
            raise HTTPException(500, "Failed to update project")
        return _to_project_out(row)

    @app.delete("/finance/catalogs/projects/{project_id}")
    def finance_delete_project(project_id: int, user=Depends(require_role("admin", "owner"))):
        # Архивируем проект только если не найдено связанных записей.
        with psycopg.connect(DB_DSN) as conn:
            current = q1(conn, "SELECT 1 FROM finance.projects WHERE project_id=%s", (project_id,))
            if not current:
                raise HTTPException(404, "Project not found")
            has_entries = q1(conn, "SELECT 1 FROM finance.entries WHERE project_id=%s LIMIT 1", (project_id,))
            if has_entries:
                raise HTTPException(409, "Project has entries and cannot be deleted")
            exec1(conn, "UPDATE finance.projects SET is_active=false, updated_at=now() WHERE project_id=%s", (project_id,))
            conn.commit()
        return {"ok": True}

    @app.get("/finance/formulas", response_model=list[FinanceFormulaOut])
    def finance_list_formulas(operation_id: Optional[int] = None, user=Depends(get_current_user)):
        # Отдаем формулы с фильтром по операции для настройки расчетов.
        params: list[Any] = []
        where_sql = "1=1"
        if operation_id is not None:
            where_sql = "operation_id=%s"
            params.append(operation_id)
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                f"""
                SELECT formula_id, operation_id, version, expression_json, rounding_mode,
                       scale, effective_from, effective_to, is_active, comment, created_by, created_at
                FROM finance.operation_formulas
                WHERE {where_sql}
                ORDER BY operation_id, version DESC
                """,
                tuple(params),
            )
        return [_to_formula_out(row) for row in rows]

    @app.post("/finance/formulas", response_model=FinanceFormulaOut)
    def finance_create_formula(payload: FinanceFormulaCreateIn, user=Depends(require_role("admin", "owner"))):
        # Создаем версию формулы для операции на выбранный период действия.
        if payload.effective_to is not None and payload.effective_to < payload.effective_from:
            raise HTTPException(400, "effective_to must be >= effective_from")
        with psycopg.connect(DB_DSN) as conn:
            _load_operation(conn, payload.operation_id)
            row = q1(
                conn,
                """
                INSERT INTO finance.operation_formulas(
                  operation_id, version, expression_json, rounding_mode, scale,
                  effective_from, effective_to, is_active, comment, created_by
                )
                VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s)
                RETURNING formula_id, operation_id, version, expression_json, rounding_mode,
                          scale, effective_from, effective_to, is_active, comment, created_by, created_at
                """,
                (
                    payload.operation_id,
                    payload.version,
                    json.dumps(payload.expression_json or {}),
                    (payload.rounding_mode or "half_up").strip(),
                    payload.scale,
                    payload.effective_from,
                    payload.effective_to,
                    payload.is_active,
                    (payload.comment or "").strip() or None,
                    str(getattr(user, "username", "") or ""),
                ),
            )
            conn.commit()
        if not row:
            raise HTTPException(500, "Failed to create formula")
        return _to_formula_out(row)

    @app.post("/finance/entries", response_model=FinanceEntryOut)
    def finance_create_entry(payload: FinanceEntryCreateIn, user=Depends(require_role("admin", "owner"))):
        # Создаем одну запись через общий helper, чтобы логика совпадала с bulk.
        with psycopg.connect(DB_DSN) as conn:
            created_by = str(getattr(user, "username", "") or "")
            item, _ = _create_entry_in_tx(conn, payload, created_by)
            conn.commit()
        return item

    @app.post("/finance/entries/bulk", response_model=FinanceEntryBulkOut)
    def finance_create_entries_bulk(payload: FinanceEntryBulkIn, user=Depends(require_role("admin", "owner"))):
        # Пакетно создаем записи и сохраняем протокол ошибок построчно.
        items = payload.items or []
        if not items:
            raise HTTPException(400, "items must not be empty")
        created_by = str(getattr(user, "username", "") or "")
        errors: list[FinanceEntryBulkErrorOut] = []
        success_rows = 0
        failed_rows = 0
        status = "done"
        with psycopg.connect(DB_DSN) as conn:
            batch_row = q1(
                conn,
                """
                INSERT INTO finance.import_batches(input_channel, file_name, total_rows, status, started_by)
                VALUES ('import', %s, %s, 'running', %s)
                RETURNING batch_id
                """,
                ((payload.file_name or "").strip() or None, len(items), created_by),
            )
            if not batch_row:
                raise HTTPException(500, "Failed to create import batch")
            batch_id = int(batch_row[0])

            for idx, item in enumerate(items, start=1):
                ext_key = (item.external_key or "").strip() or None
                try:
                    out, created_new = _create_entry_in_tx(conn, item, created_by)
                    success_rows += 1
                    exec1(
                        conn,
                        """
                        INSERT INTO finance.import_batch_rows(
                          batch_id, row_no, external_key, raw_payload, status, created_entry_id, created_entry_biz_date
                        )
                        VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s)
                        """,
                        (
                            batch_id,
                            idx,
                            ext_key,
                            json.dumps(item.model_dump(mode="json")),
                            "ok" if created_new else "skipped",
                            out.entry_id,
                            out.biz_date,
                        ),
                    )
                except Exception as exc:
                    failed_rows += 1
                    status = "failed"
                    error_message = str(exc)
                    errors.append(FinanceEntryBulkErrorOut(row_no=idx, error=error_message, external_key=ext_key))
                    exec1(
                        conn,
                        """
                        INSERT INTO finance.import_batch_rows(
                          batch_id, row_no, external_key, raw_payload, status, error_message
                        )
                        VALUES (%s, %s, %s, %s::jsonb, 'failed', %s)
                        """,
                        (batch_id, idx, ext_key, json.dumps(item.model_dump(mode="json")), error_message[:2000]),
                    )
                    if payload.stop_on_error:
                        break

            exec1(
                conn,
                """
                UPDATE finance.import_batches
                SET success_rows=%s, failed_rows=%s, status=%s, finished_at=now()
                WHERE batch_id=%s
                """,
                (success_rows, failed_rows, status, batch_id),
            )
            conn.commit()

        return FinanceEntryBulkOut(
            batch_id=batch_id,
            total_rows=len(items),
            success_rows=success_rows,
            failed_rows=failed_rows,
            status=status,
            errors=errors,
        )

    @app.get("/finance/entries", response_model=FinanceEntryListOut)
    def finance_list_entries(
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        operation_id: Optional[int] = None,
        region_id: Optional[int] = None,
        source_id: Optional[int] = None,
        project_id: Optional[int] = None,
        status_code: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        user=Depends(get_current_user),
    ):
        # Собираем фильтры списка, чтобы журнал работал с теми же разрезами, что и отчеты.
        params: list[Any] = []
        filters = ["1=1"]
        if date_from is not None:
            filters.append("e.biz_date >= %s")
            params.append(date_from)
        if date_to is not None:
            filters.append("e.biz_date <= %s")
            params.append(date_to)
        if operation_id is not None:
            filters.append("e.operation_id = %s")
            params.append(operation_id)
        if region_id is not None:
            filters.append("e.region_id = %s")
            params.append(region_id)
        if source_id is not None:
            filters.append("e.source_id = %s")
            params.append(source_id)
        if project_id is not None:
            filters.append("e.project_id = %s")
            params.append(project_id)
        if status_code:
            filters.append("e.status_code = %s")
            params.append(_normalize_code(status_code))

        where_sql = " AND ".join(filters)
        safe_limit = max(1, min(limit, 500))
        safe_offset = max(0, offset)

        with psycopg.connect(DB_DSN) as conn:
            total_row = q1(conn, f"SELECT COUNT(*) FROM finance.entries e WHERE {where_sql}", tuple(params))
            rows = qall(
                conn,
                f"""
                SELECT
                  e.entry_id, e.biz_date, e.operation_id, e.region_id, e.source_id, e.project_id,
                  e.qty, e.amount, e.currency, e.input_channel, e.external_key, e.status_code,
                  e.comment, e.created_by, e.created_at, e.updated_at
                FROM finance.entries e
                WHERE {where_sql}
                ORDER BY e.biz_date DESC, e.entry_id DESC
                LIMIT %s OFFSET %s
                """,
                tuple([*params, safe_limit, safe_offset]),
            )

        return FinanceEntryListOut(
            total=int((total_row or [0])[0] or 0),
            items=[_to_entry_out(row) for row in rows],
        )

    @app.get("/finance/reports/pnl", response_model=FinancePnlOut)
    def finance_report_pnl(
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        region_id: Optional[int] = None,
        source_id: Optional[int] = None,
        project_id: Optional[int] = None,
        operation_id: Optional[int] = None,
        group_by: str = "month",
        user=Depends(get_current_user),
    ):
        # Формируем P&L по фильтрам и выбранной группировке.
        params: list[Any] = []
        filters = ["e.status_code = 'confirmed'"]
        if date_from is not None:
            filters.append("e.biz_date >= %s")
            params.append(date_from)
        if date_to is not None:
            filters.append("e.biz_date <= %s")
            params.append(date_to)
        if region_id is not None:
            filters.append("e.region_id = %s")
            params.append(region_id)
        if source_id is not None:
            filters.append("e.source_id = %s")
            params.append(source_id)
        if project_id is not None:
            filters.append("e.project_id = %s")
            params.append(project_id)
        if operation_id is not None:
            filters.append("e.operation_id = %s")
            params.append(operation_id)
        where_sql = " AND ".join(filters)

        group_key = _normalize_code(group_by)
        bucket_sql = {
            "day": "to_char(e.biz_date, 'YYYY-MM-DD')",
            "month": "to_char(date_trunc('month', e.biz_date), 'YYYY-MM')",
            "project": "COALESCE(pr.code, 'no_project')",
            "source": "COALESCE(src.code, 'no_source')",
            "region": "COALESCE(r.code, 'no_region')",
            "operation": "COALESCE(op.code, 'no_operation')",
        }.get(group_key)
        if not bucket_sql:
            raise HTTPException(400, "group_by must be one of: day, month, project, source, region, operation")

        with psycopg.connect(DB_DSN) as conn:
            totals_row = q1(
                conn,
                f"""
                SELECT
                  COALESCE(SUM(CASE WHEN p.metric_code='revenue' THEN p.amount ELSE 0 END), 0) AS revenue,
                  COALESCE(SUM(CASE WHEN p.metric_code='direct_expense' THEN p.amount ELSE 0 END), 0) AS direct_expense,
                  COALESCE(SUM(CASE WHEN p.metric_code='indirect_expense' THEN p.amount ELSE 0 END), 0) AS indirect_expense
                FROM finance.entry_postings p
                JOIN finance.entries e
                  ON e.entry_id = p.entry_id
                 AND e.biz_date = p.entry_biz_date
                LEFT JOIN finance.projects pr ON pr.project_id = e.project_id
                LEFT JOIN finance.dim_sources src ON src.source_id = e.source_id
                LEFT JOIN finance.dim_regions r ON r.region_id = e.region_id
                LEFT JOIN finance.operations op ON op.operation_id = e.operation_id
                WHERE {where_sql}
                """,
                tuple(params),
            )

            series_rows = qall(
                conn,
                f"""
                SELECT
                  {bucket_sql} AS bucket,
                  COALESCE(SUM(CASE WHEN p.metric_code='revenue' THEN p.amount ELSE 0 END), 0) AS revenue,
                  COALESCE(SUM(CASE WHEN p.metric_code='direct_expense' THEN p.amount ELSE 0 END), 0) AS direct_expense,
                  COALESCE(SUM(CASE WHEN p.metric_code='indirect_expense' THEN p.amount ELSE 0 END), 0) AS indirect_expense
                FROM finance.entry_postings p
                JOIN finance.entries e
                  ON e.entry_id = p.entry_id
                 AND e.biz_date = p.entry_biz_date
                LEFT JOIN finance.projects pr ON pr.project_id = e.project_id
                LEFT JOIN finance.dim_sources src ON src.source_id = e.source_id
                LEFT JOIN finance.dim_regions r ON r.region_id = e.region_id
                LEFT JOIN finance.operations op ON op.operation_id = e.operation_id
                WHERE {where_sql}
                GROUP BY bucket
                ORDER BY bucket
                """,
                tuple(params),
            )

        revenue = _round_money(Decimal((totals_row or [0])[0] or 0))
        direct_expense = _round_money(Decimal((totals_row or [0, 0])[1] or 0))
        indirect_expense = _round_money(Decimal((totals_row or [0, 0, 0])[2] or 0))
        gross_profit = _round_money(revenue - direct_expense)
        operating_profit = _round_money(gross_profit - indirect_expense)
        margin = _round_ratio((operating_profit / revenue) if revenue != 0 else Decimal("0"))

        series = []
        for row in series_rows:
            row_revenue = _round_money(Decimal(row[1] or 0))
            row_direct = _round_money(Decimal(row[2] or 0))
            row_indirect = _round_money(Decimal(row[3] or 0))
            row_gross = _round_money(row_revenue - row_direct)
            row_operating = _round_money(row_gross - row_indirect)
            row_margin = _round_ratio((row_operating / row_revenue) if row_revenue != 0 else Decimal("0"))
            series.append(
                FinancePnlBucketOut(
                    bucket=str(row[0]),
                    revenue=row_revenue,
                    direct_expense=row_direct,
                    indirect_expense=row_indirect,
                    gross_profit=row_gross,
                    operating_profit=row_operating,
                    margin=row_margin,
                )
            )

        return FinancePnlOut(
            totals=FinancePnlTotalsOut(
                revenue=revenue,
                direct_expense=direct_expense,
                indirect_expense=indirect_expense,
                gross_profit=gross_profit,
                operating_profit=operating_profit,
                margin=margin,
            ),
            series=series,
        )

    @app.get("/finance/reports/projects", response_model=FinanceProjectsReportOut)
    def finance_report_projects(
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        region_id: Optional[int] = None,
        source_id: Optional[int] = None,
        project_id: Optional[int] = None,
        operation_id: Optional[int] = None,
        split_by_source: bool = False,
        user=Depends(get_current_user),
    ):
        # Собираем отчет по проектам с возможным разрезом по источнику.
        params: list[Any] = []
        filters = ["e.status_code = 'confirmed'"]
        if date_from is not None:
            filters.append("e.biz_date >= %s")
            params.append(date_from)
        if date_to is not None:
            filters.append("e.biz_date <= %s")
            params.append(date_to)
        if region_id is not None:
            filters.append("e.region_id = %s")
            params.append(region_id)
        if source_id is not None:
            filters.append("e.source_id = %s")
            params.append(source_id)
        if project_id is not None:
            filters.append("e.project_id = %s")
            params.append(project_id)
        if operation_id is not None:
            filters.append("e.operation_id = %s")
            params.append(operation_id)
        where_sql = " AND ".join(filters)

        if split_by_source:
            source_select = "e.source_id, src.code AS source_code, src.name AS source_name"
            source_group = "e.source_id, src.code, src.name"
            source_order = "source_code NULLS FIRST,"
        else:
            source_select = "NULL::bigint AS source_id, NULL::text AS source_code, NULL::text AS source_name"
            source_group = "NULL::bigint, NULL::text, NULL::text"
            source_order = ""

        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                f"""
                SELECT
                  e.project_id,
                  COALESCE(pr.code, 'no_project') AS project_code,
                  COALESCE(pr.name, 'Без проекта') AS project_name,
                  {source_select},
                  COALESCE(SUM(CASE WHEN p.metric_code='revenue' THEN p.amount ELSE 0 END), 0) AS revenue,
                  COALESCE(SUM(CASE WHEN p.metric_code='direct_expense' THEN p.amount ELSE 0 END), 0) AS direct_expense,
                  COALESCE(SUM(CASE WHEN p.metric_code='indirect_expense' THEN p.amount ELSE 0 END), 0) AS indirect_expense
                FROM finance.entry_postings p
                JOIN finance.entries e
                  ON e.entry_id = p.entry_id
                 AND e.biz_date = p.entry_biz_date
                LEFT JOIN finance.projects pr ON pr.project_id = e.project_id
                LEFT JOIN finance.dim_sources src ON src.source_id = e.source_id
                WHERE {where_sql}
                GROUP BY e.project_id, pr.code, pr.name, {source_group}
                ORDER BY project_code, {source_order} project_name
                """,
                tuple(params),
            )

        items: list[FinanceProjectsReportRowOut] = []
        revenue_total = Decimal("0")
        direct_total = Decimal("0")
        indirect_total = Decimal("0")
        for row in rows:
            row_revenue = _round_money(Decimal(row[6] or 0))
            row_direct = _round_money(Decimal(row[7] or 0))
            row_indirect = _round_money(Decimal(row[8] or 0))
            row_gross = _round_money(row_revenue - row_direct)
            row_operating = _round_money(row_gross - row_indirect)
            row_margin = _round_ratio((row_operating / row_revenue) if row_revenue != 0 else Decimal("0"))
            revenue_total += row_revenue
            direct_total += row_direct
            indirect_total += row_indirect
            items.append(
                FinanceProjectsReportRowOut(
                    project_id=int(row[0]) if row[0] is not None else None,
                    project_code=str(row[1]),
                    project_name=str(row[2]),
                    source_id=int(row[3]) if row[3] is not None else None,
                    source_code=str(row[4]) if row[4] is not None else None,
                    source_name=str(row[5]) if row[5] is not None else None,
                    revenue=row_revenue,
                    direct_expense=row_direct,
                    indirect_expense=row_indirect,
                    gross_profit=row_gross,
                    operating_profit=row_operating,
                    margin=row_margin,
                )
            )

        revenue_total = _round_money(revenue_total)
        direct_total = _round_money(direct_total)
        indirect_total = _round_money(indirect_total)
        gross_total = _round_money(revenue_total - direct_total)
        operating_total = _round_money(gross_total - indirect_total)
        margin_total = _round_ratio((operating_total / revenue_total) if revenue_total != 0 else Decimal("0"))

        return FinanceProjectsReportOut(
            totals=FinancePnlTotalsOut(
                revenue=revenue_total,
                direct_expense=direct_total,
                indirect_expense=indirect_total,
                gross_profit=gross_total,
                operating_profit=operating_total,
                margin=margin_total,
            ),
            items=items,
        )
