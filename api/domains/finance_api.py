from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional
import json
import os
import re
import threading
import uuid

from fastapi import Depends, HTTPException, Query

from .yandex_market_service import fetch_yandex_market_order_economics, normalize_yandex_market_store_code
from .wildberries_service import aggregate_wildberries_report_rows, fetch_wildberries_sales_report, normalize_wildberries_store_code
from .ozon_service import aggregate_ozon_finance_transactions, fetch_ozon_finance_transactions, normalize_ozon_store_code
from .finance_models import (
    FinanceBootstrapOut,
    FinanceCardBalanceOut,
    FinanceCardBalanceSetIn,
    FinanceCashFlowDetailRowOut,
    FinanceCashFlowDetailsOut,
    FinanceCashFlowLineOut,
    FinanceCashFlowOpeningBalanceIn,
    FinanceCashFlowOpeningBalanceOut,
    FinanceCashFlowReportOut,
    FinanceCashFlowTotalsOut,
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
    FinanceOzonSyncIn,
    FinanceOzonSyncJobOut,
    FinanceOzonSyncOut,
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
    FinanceSourcesReportOut,
    FinanceSourcesReportDetailRowOut,
    FinanceSourcesReportDetailTotalsOut,
    FinanceSourcesReportDetailsOut,
    FinanceSourcesReportRowOut,
    FinanceStatusOut,
    FinanceTypeOut,
    FinanceTypeCreateIn,
    FinanceTypeUpdateIn,
    FinanceYandexSyncIn,
    FinanceYandexSyncJobOut,
    FinanceYandexSyncOut,
    FinanceWildberriesSyncIn,
    FinanceWildberriesSyncJobOut,
    FinanceWildberriesSyncOut,
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
    yandex_sync_jobs: dict[str, dict[str, Any]] = {}
    wildberries_sync_jobs: dict[str, dict[str, Any]] = {}
    ozon_sync_jobs: dict[str, dict[str, Any]] = {}

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

    def _append_multi_id_filter(filters: list[str], params: list[Any], column_name: str, values: Optional[list[int]]) -> None:
        # Добавляет фильтр по нескольким id без сборки динамического списка плейсхолдеров.
        ids = [int(value) for value in (values or []) if value is not None]
        if not ids:
            return
        filters.append(f"{column_name} = ANY(%s)")
        params.append(ids)

    def _append_nullable_id_filter(filters: list[str], params: list[Any], column_name: str, value: Optional[int], empty: bool) -> None:
        # Фильтруем точную строку отчета: конкретный id или явное отсутствие значения.
        if empty:
            filters.append(f"{column_name} IS NULL")
            return
        if value is not None:
            filters.append(f"{column_name} = %s")
            params.append(int(value))

    def _metric_from_section_kind(kind: str) -> str:
        # Преобразуем тип раздела в базовую метрику для P&L.
        mapping = {
            "revenue": "revenue",
            "direct_expense": "direct_expense",
            "indirect_expense": "indirect_expense",
            "other": "other",
        }
        return mapping.get((kind or "").strip(), "other")

    def _rebuild_entry_postings_for_operation(conn, operation_id: int) -> None:
        # Пересобираем базовые postings операции после смены типа, чтобы отчеты и справочник не расходились.
        row = q1(
            conn,
            """
            SELECT t.code
            FROM finance.operations o
            JOIN finance.section_types t ON t.type_id = o.type_id
            WHERE o.operation_id=%s
            """,
            (operation_id,),
        )
        if not row:
            return
        metric_code = _metric_from_section_kind(str(row[0] or ""))
        exec1(
            conn,
            """
            DELETE FROM finance.entry_postings p
            USING finance.entries e
            WHERE p.entry_id = e.entry_id
              AND p.entry_biz_date = e.biz_date
              AND e.operation_id = %s
              AND p.formula_id IS NULL
            """,
            (operation_id,),
        )
        exec1(
            conn,
            """
            INSERT INTO finance.entry_postings(entry_id, entry_biz_date, metric_code, amount)
            SELECT e.entry_id, e.biz_date, %s, e.amount
            FROM finance.entries e
            WHERE e.operation_id = %s
            """,
            (metric_code, operation_id),
        )

    def _round_money(value: Decimal) -> Decimal:
        # Округляем денежные значения единообразно до двух знаков.
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _round_ratio(value: Decimal) -> Decimal:
        # Округляем долю/маржу до четырех знаков для отчетов.
        return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    def _json_list_as_strings(value: Any) -> list[str]:
        # Приводим jsonb-массив из payload к списку строк для безопасной отдачи в API.
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if item not in (None, "")]

    def _parse_month(value: Optional[str]) -> date:
        # Превращаем строку YYYY-MM в первое число месяца для месячных отчетов.
        raw = (value or date.today().strftime("%Y-%m")).strip()
        try:
            year_text, month_text = raw.split("-", 1)
            year = int(year_text)
            month_num = int(month_text)
            if month_num < 1 or month_num > 12:
                raise ValueError("month out of range")
            return date(year, month_num, 1)
        except Exception:
            raise HTTPException(400, "month must be in YYYY-MM format")

    def _next_month_start(month_start: date) -> date:
        # Возвращает первое число следующего месяца для полуоткрытых date-фильтров.
        if month_start.month == 12:
            return date(month_start.year + 1, 1, 1)
        return date(month_start.year, month_start.month + 1, 1)

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
            source_id=int(row[2]) if row[2] is not None else None,
            code=row[3],
            name=row[4],
            input_mode=row[5],
            requires_region=bool(row[6]),
            requires_source=bool(row[7]),
            requires_project=bool(row[8]),
            requires_qty=bool(row[9]),
            allows_negative=bool(row[10]),
            sort_order=int(row[11] or 0),
            is_active=bool(row[12]),
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

    def _env_int(name: str) -> Optional[int]:
        # Читаем id из env; пустое значение значит, что будет поиск по коду.
        raw = str(os.getenv(name, "") or "").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            raise HTTPException(500, f"{name} must be integer")

    def _yandex_store_env(name: str, store_code: str, default: str = "") -> str:
        # Читаем настройку конкретного магазина; общий env используем только для старого ASAT.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        scoped = str(os.getenv(f"YANDEX_MARKET_{normalized_store_code.upper()}_{name}", "") or "").strip()
        if scoped:
            return scoped
        if normalized_store_code in {"asat", "default"}:
            return str(os.getenv(f"YANDEX_MARKET_{name}", default) or "").strip()
        return default

    def _yandex_store_env_int(name: str, store_code: str) -> Optional[int]:
        # Читает числовую настройку магазина, например source_id, без подмены SPS значением ASAT.
        raw = _yandex_store_env(name, store_code)
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            normalized_store_code = normalize_yandex_market_store_code(store_code)
            raise HTTPException(500, f"YANDEX_MARKET_{normalized_store_code.upper()}_{name} must be integer")

    def _resolve_yandex_source_id(conn, store_code: str) -> int:
        # Находим finance-источник выбранного магазина для привязки импортированных строк Яндекса.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        source_id = _yandex_store_env_int("FINANCE_SOURCE_ID", normalized_store_code)
        if source_id is not None:
            row = q1(conn, "SELECT source_id FROM finance.dim_sources WHERE source_id=%s AND is_active IS TRUE", (source_id,))
            if not row:
                raise HTTPException(400, f"Unknown YANDEX_MARKET_{normalized_store_code.upper()}_FINANCE_SOURCE_ID: {source_id}")
            return int(row[0])

        default_source_name = "ASAT" if normalized_store_code in {"asat", "default"} else normalized_store_code.upper()
        source_code = _normalize_code(_yandex_store_env("SOURCE_CODE", normalized_store_code, "ym"))
        source_name = _yandex_store_env("SOURCE_NAME", normalized_store_code, default_source_name).strip().lower()
        row = q1(
            conn,
            """
            SELECT source_id
            FROM finance.dim_sources
            WHERE lower(code)=%s
              AND lower(name)=%s
              AND is_active IS TRUE
            ORDER BY source_id
            LIMIT 1
            """,
            (source_code, source_name),
        )
        if row:
            return int(row[0])

        rows = qall(
            conn,
            """
            SELECT source_id
            FROM finance.dim_sources
            WHERE lower(code)=%s
              AND is_active IS TRUE
            ORDER BY source_id
            LIMIT 2
            """,
            (source_code,),
        )
        if len(rows) == 1:
            return int(rows[0][0])
        raise HTTPException(400, f"Yandex finance source is not configured for {normalized_store_code}; set YANDEX_MARKET_{normalized_store_code.upper()}_FINANCE_SOURCE_ID")

    def _resolve_yandex_project_id(conn) -> Optional[int]:
        # Подставляем проект marketplace, если он есть; это сохраняет совместимость с текущими справочниками.
        project_id = _env_int("YANDEX_MARKET_PROJECT_ID")
        if project_id is not None:
            row = q1(conn, "SELECT project_id FROM finance.projects WHERE project_id=%s AND is_active IS TRUE", (project_id,))
            if not row:
                raise HTTPException(400, f"Unknown YANDEX_MARKET_PROJECT_ID: {project_id}")
            return int(row[0])

        project_code = _normalize_code(os.getenv("YANDEX_MARKET_PROJECT_CODE", "marketplace"))
        row = q1(
            conn,
            "SELECT project_id FROM finance.projects WHERE lower(code)=%s AND is_active IS TRUE ORDER BY project_id LIMIT 1",
            (project_code,),
        )
        return int(row[0]) if row else None

    def _resolve_yandex_operation_id(conn) -> int:
        # Выбираем операцию выручки маркетплейса, которую будут использовать finance.entries.
        operation_id = _env_int("YANDEX_MARKET_REVENUE_OPERATION_ID")
        if operation_id is not None:
            row = q1(conn, "SELECT operation_id FROM finance.operations WHERE operation_id=%s AND is_active IS TRUE", (operation_id,))
            if not row:
                raise HTTPException(400, f"Unknown YANDEX_MARKET_REVENUE_OPERATION_ID: {operation_id}")
            return int(row[0])

        operation_code = _normalize_code(os.getenv("YANDEX_MARKET_REVENUE_OPERATION_CODE", "revenue_marketplace_api"))
        row = q1(
            conn,
            "SELECT operation_id FROM finance.operations WHERE lower(code)=%s AND is_active IS TRUE ORDER BY operation_id LIMIT 1",
            (operation_code,),
        )
        if not row:
            type_row = q1(
                conn,
                """
                INSERT INTO finance.section_types(code, name, sort_order, is_active)
                VALUES ('revenue', 'Выручка', 10, true)
                ON CONFLICT (code) DO UPDATE
                SET name=excluded.name,
                    sort_order=excluded.sort_order,
                    is_active=true,
                    updated_at=now()
                RETURNING type_id
                """,
            )
            type_id = int(type_row[0])
            # Создаем базовый раздел выручки, чтобы новая операция попала в P&L без ручной подготовки.
            exec1(
                conn,
                """
                INSERT INTO finance.sections(parent_section_id, type_id, code, name, kind, sort_order, is_active)
                VALUES (NULL, %s, 'revenue', 'Выручка', 'revenue', 10, true)
                ON CONFLICT (code) DO UPDATE
                SET type_id=excluded.type_id,
                    name=excluded.name,
                    kind=excluded.kind,
                    sort_order=excluded.sort_order,
                    is_active=true,
                    updated_at=now()
                """,
                (type_id,),
            )
            op_row = q1(
                conn,
                """
                INSERT INTO finance.operations(
                  type_id, code, name, input_mode,
                  requires_region, requires_source, requires_project, requires_qty, allows_negative,
                  sort_order, is_active
                )
                VALUES (%s, %s, 'Продажи маркетплейсов (API)', 'api', false, false, false, false, false, 20, true)
                ON CONFLICT (code) DO UPDATE
                SET type_id=excluded.type_id,
                    name=excluded.name,
                    input_mode=excluded.input_mode,
                    is_active=true,
                    updated_at=now()
                RETURNING operation_id
                """,
                (type_id, operation_code),
            )
            if not op_row:
                raise HTTPException(500, "Failed to create Yandex revenue operation")
            return int(op_row[0])
        return int(row[0])

    def _resolve_yandex_commission_operation_id(conn) -> int:
        # Выбираем операцию расходов маркетплейса для комиссий и услуг Яндекса.
        operation_id = _env_int("YANDEX_MARKET_COMMISSION_OPERATION_ID")
        if operation_id is not None:
            row = q1(conn, "SELECT operation_id FROM finance.operations WHERE operation_id=%s AND is_active IS TRUE", (operation_id,))
            if not row:
                raise HTTPException(400, f"Unknown YANDEX_MARKET_COMMISSION_OPERATION_ID: {operation_id}")
            return int(row[0])

        operation_code = _normalize_code(os.getenv("YANDEX_MARKET_COMMISSION_OPERATION_CODE", "direct_marketplace_commission_api"))
        row = q1(
            conn,
            "SELECT operation_id FROM finance.operations WHERE lower(code)=%s AND is_active IS TRUE ORDER BY operation_id LIMIT 1",
            (operation_code,),
        )
        if row:
            return int(row[0])

        type_row = q1(
            conn,
            """
            INSERT INTO finance.section_types(code, name, sort_order, is_active)
            VALUES ('direct_expense', 'Прямые расходы', 20, true)
            ON CONFLICT (code) DO UPDATE
            SET name=excluded.name,
                sort_order=excluded.sort_order,
                is_active=true,
                updated_at=now()
            RETURNING type_id
            """,
        )
        type_id = int(type_row[0])
        # Создаем раздел прямых расходов, чтобы комиссии Яндекса попадали в расходы отчета.
        exec1(
            conn,
            """
            INSERT INTO finance.sections(parent_section_id, type_id, code, name, kind, sort_order, is_active)
            VALUES (NULL, %s, 'direct_expense', 'Прямые расходы', 'direct_expense', 20, true)
            ON CONFLICT (code) DO UPDATE
            SET type_id=excluded.type_id,
                name=excluded.name,
                kind=excluded.kind,
                sort_order=excluded.sort_order,
                is_active=true,
                updated_at=now()
            """,
            (type_id,),
        )
        op_row = q1(
            conn,
            """
            INSERT INTO finance.operations(
              type_id, code, name, input_mode,
              requires_region, requires_source, requires_project, requires_qty, allows_negative,
              sort_order, is_active
            )
            VALUES (%s, %s, 'Комиссии маркетплейсов (API)', 'api', false, false, false, false, false, 25, true)
            ON CONFLICT (code) DO UPDATE
            SET type_id=excluded.type_id,
                name=excluded.name,
                input_mode=excluded.input_mode,
                is_active=true,
                updated_at=now()
            RETURNING operation_id
            """,
            (type_id, operation_code),
        )
        if not op_row:
            raise HTTPException(500, "Failed to create Yandex commission operation")
        return int(op_row[0])

    def _wildberries_store_env(store_code: str, name: str, default: str = "") -> str:
        # Читаем настройку выбранного WB-магазина, сохраняя fallback общих переменных для ASAT.
        normalized_store_code = normalize_wildberries_store_code(store_code)
        scoped = str(os.getenv(f"WILDBERRIES_{normalized_store_code.upper()}_{name}", "") or "").strip()
        if scoped:
            return scoped
        if normalized_store_code in {"asat", "default"}:
            return str(os.getenv(f"WILDBERRIES_{name}", default) or "").strip()
        return default

    def _wildberries_store_env_int(store_code: str, name: str) -> Optional[int]:
        # Читаем числовую настройку WB-магазина без подмены SPS значением ASAT.
        raw = _wildberries_store_env(store_code, name)
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            normalized_store_code = normalize_wildberries_store_code(store_code)
            raise HTTPException(500, f"WILDBERRIES_{normalized_store_code.upper()}_{name} must be integer")

    def _resolve_wildberries_source_id(conn, store_code: str) -> int:
        # Находим finance-источник выбранного WB-магазина по id или паре кода и названия.
        normalized_store_code = normalize_wildberries_store_code(store_code)
        source_id = _wildberries_store_env_int(normalized_store_code, "FINANCE_SOURCE_ID")
        if source_id is not None:
            row = q1(conn, "SELECT source_id FROM finance.dim_sources WHERE source_id=%s AND is_active IS TRUE", (source_id,))
            if not row:
                raise HTTPException(400, f"Unknown WILDBERRIES_{normalized_store_code.upper()}_FINANCE_SOURCE_ID: {source_id}")
            return int(row[0])

        source_code = _normalize_code(_wildberries_store_env(normalized_store_code, "SOURCE_CODE", "wb"))
        source_name_value = _wildberries_store_env(normalized_store_code, "SOURCE_NAME", normalized_store_code.upper())
        source_name = source_name_value.strip().lower()
        row = q1(
            conn,
            """
            SELECT source_id
            FROM finance.dim_sources
            WHERE lower(code)=%s AND lower(name)=%s AND is_active IS TRUE
            ORDER BY source_id
            LIMIT 1
            """,
            (source_code, source_name),
        )
        if row:
            return int(row[0])
        rows = qall(
            conn,
            "SELECT source_id FROM finance.dim_sources WHERE lower(code)=%s AND is_active IS TRUE ORDER BY source_id LIMIT 2",
            (source_code,),
        )
        if len(rows) == 1:
            return int(rows[0][0])
        if len(rows) > 1:
            raise HTTPException(400, f"Wildberries finance source is ambiguous for {normalized_store_code}; set WILDBERRIES_{normalized_store_code.upper()}_FINANCE_SOURCE_ID")
        source_row = q1(
            conn,
            """
            INSERT INTO finance.dim_sources(code, name, is_active)
            VALUES (%s, %s, true)
            ON CONFLICT (code, name) DO UPDATE
            SET is_active=true,
                updated_at=now()
            RETURNING source_id
            """,
            (source_code, source_name_value.strip()),
        )
        if not source_row:
            raise HTTPException(500, "Failed to create Wildberries finance source")
        return int(source_row[0])

    def _resolve_wildberries_project_id(conn) -> Optional[int]:
        # Подставляем общий проект marketplace, чтобы WB и Яндекс попадали в одну группу отчетов.
        project_id = _env_int("WILDBERRIES_PROJECT_ID")
        if project_id is not None:
            row = q1(conn, "SELECT project_id FROM finance.projects WHERE project_id=%s AND is_active IS TRUE", (project_id,))
            if not row:
                raise HTTPException(400, f"Unknown WILDBERRIES_PROJECT_ID: {project_id}")
            return int(row[0])
        project_code = _normalize_code(os.getenv("WILDBERRIES_PROJECT_CODE", "marketplace"))
        row = q1(
            conn,
            "SELECT project_id FROM finance.projects WHERE lower(code)=%s AND is_active IS TRUE ORDER BY project_id LIMIT 1",
            (project_code,),
        )
        return int(row[0]) if row else None

    def _resolve_wildberries_revenue_operation_id(conn) -> int:
        # Используем общую операцию продаж маркетплейсов или явно настроенную операцию WB.
        operation_id = _env_int("WILDBERRIES_REVENUE_OPERATION_ID")
        if operation_id is not None:
            row = q1(conn, "SELECT operation_id FROM finance.operations WHERE operation_id=%s AND is_active IS TRUE", (operation_id,))
            if not row:
                raise HTTPException(400, f"Unknown WILDBERRIES_REVENUE_OPERATION_ID: {operation_id}")
            return int(row[0])
        operation_code = _normalize_code(os.getenv("WILDBERRIES_REVENUE_OPERATION_CODE", "revenue_marketplace_api"))
        row = q1(conn, "SELECT operation_id FROM finance.operations WHERE lower(code)=%s AND is_active IS TRUE ORDER BY operation_id LIMIT 1", (operation_code,))
        if row:
            return int(row[0])
        if operation_code == _normalize_code(os.getenv("YANDEX_MARKET_REVENUE_OPERATION_CODE", "revenue_marketplace_api")):
            return _resolve_yandex_operation_id(conn)
        raise HTTPException(400, f"Wildberries revenue operation is not configured: {operation_code}")

    def _resolve_wildberries_expense_operation_id(conn) -> int:
        # Используем общую операцию комиссий маркетплейсов для всех удержаний WB.
        operation_id = _env_int("WILDBERRIES_EXPENSE_OPERATION_ID")
        if operation_id is not None:
            row = q1(conn, "SELECT operation_id FROM finance.operations WHERE operation_id=%s AND is_active IS TRUE", (operation_id,))
            if not row:
                raise HTTPException(400, f"Unknown WILDBERRIES_EXPENSE_OPERATION_ID: {operation_id}")
            return int(row[0])
        operation_code = _normalize_code(os.getenv("WILDBERRIES_EXPENSE_OPERATION_CODE", "direct_marketplace_commission_api"))
        row = q1(conn, "SELECT operation_id FROM finance.operations WHERE lower(code)=%s AND is_active IS TRUE ORDER BY operation_id LIMIT 1", (operation_code,))
        if row:
            return int(row[0])
        if operation_code == _normalize_code(os.getenv("YANDEX_MARKET_COMMISSION_OPERATION_CODE", "direct_marketplace_commission_api")):
            return _resolve_yandex_commission_operation_id(conn)
        raise HTTPException(400, f"Wildberries expense operation is not configured: {operation_code}")

    def _ozon_store_env(store_code: str, name: str, default: str = "") -> str:
        # Читаем настройку выбранного кабинета Ozon и сохраняем общий fallback для ASAT.
        normalized_store_code = normalize_ozon_store_code(store_code)
        scoped = str(os.getenv(f"OZON_{normalized_store_code.upper()}_{name}", "") or "").strip()
        if scoped:
            return scoped
        if normalized_store_code in {"asat", "default"}:
            return str(os.getenv(f"OZON_{name}", default) or "").strip()
        return default

    def _ozon_store_env_int(store_code: str, name: str) -> Optional[int]:
        # Читаем числовую настройку кабинета Ozon без подмены другого магазина.
        raw = _ozon_store_env(store_code, name)
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            normalized_store_code = normalize_ozon_store_code(store_code)
            raise HTTPException(500, f"OZON_{normalized_store_code.upper()}_{name} must be integer")

    def _resolve_ozon_source_id(conn, store_code: str) -> int:
        # Находим или создаем finance-источник конкретного кабинета Ozon.
        normalized_store_code = normalize_ozon_store_code(store_code)
        source_id = _ozon_store_env_int(normalized_store_code, "FINANCE_SOURCE_ID")
        if source_id is not None:
            row = q1(conn, "SELECT source_id FROM finance.dim_sources WHERE source_id=%s AND is_active IS TRUE", (source_id,))
            if not row:
                raise HTTPException(400, f"Unknown OZON_{normalized_store_code.upper()}_FINANCE_SOURCE_ID: {source_id}")
            return int(row[0])

        source_code = _normalize_code(_ozon_store_env(normalized_store_code, "SOURCE_CODE", "ozon"))
        source_name_value = _ozon_store_env(normalized_store_code, "SOURCE_NAME", normalized_store_code.upper()).strip()
        row = q1(
            conn,
            """
            SELECT source_id
            FROM finance.dim_sources
            WHERE lower(code)=%s AND lower(name)=%s AND is_active IS TRUE
            ORDER BY source_id
            LIMIT 1
            """,
            (source_code, source_name_value.lower()),
        )
        if row:
            return int(row[0])
        rows = qall(
            conn,
            "SELECT source_id FROM finance.dim_sources WHERE lower(code)=%s AND is_active IS TRUE ORDER BY source_id LIMIT 2",
            (source_code,),
        )
        if len(rows) == 1:
            return int(rows[0][0])
        if len(rows) > 1:
            raise HTTPException(400, f"Ozon finance source is ambiguous for {normalized_store_code}; set OZON_{normalized_store_code.upper()}_FINANCE_SOURCE_ID")
        source_row = q1(
            conn,
            """
            INSERT INTO finance.dim_sources(code, name, is_active)
            VALUES (%s, %s, true)
            ON CONFLICT (code, name) DO UPDATE
            SET is_active=true,
                updated_at=now()
            RETURNING source_id
            """,
            (source_code, source_name_value),
        )
        if not source_row:
            raise HTTPException(500, "Failed to create Ozon finance source")
        return int(source_row[0])

    def _resolve_ozon_project_id(conn) -> Optional[int]:
        # Подставляем общий проект marketplace для совместного отчета по маркетплейсам.
        project_id = _env_int("OZON_PROJECT_ID")
        if project_id is not None:
            row = q1(conn, "SELECT project_id FROM finance.projects WHERE project_id=%s AND is_active IS TRUE", (project_id,))
            if not row:
                raise HTTPException(400, f"Unknown OZON_PROJECT_ID: {project_id}")
            return int(row[0])
        project_code = _normalize_code(os.getenv("OZON_PROJECT_CODE", "marketplace"))
        row = q1(
            conn,
            "SELECT project_id FROM finance.projects WHERE lower(code)=%s AND is_active IS TRUE ORDER BY project_id LIMIT 1",
            (project_code,),
        )
        return int(row[0]) if row else None

    def _resolve_ozon_revenue_operation_id(conn) -> int:
        # Используем общую операцию продаж маркетплейсов или явную операцию Ozon.
        operation_id = _env_int("OZON_REVENUE_OPERATION_ID")
        if operation_id is not None:
            row = q1(conn, "SELECT operation_id FROM finance.operations WHERE operation_id=%s AND is_active IS TRUE", (operation_id,))
            if not row:
                raise HTTPException(400, f"Unknown OZON_REVENUE_OPERATION_ID: {operation_id}")
            return int(row[0])
        operation_code = _normalize_code(os.getenv("OZON_REVENUE_OPERATION_CODE", "revenue_marketplace_api"))
        row = q1(conn, "SELECT operation_id FROM finance.operations WHERE lower(code)=%s AND is_active IS TRUE ORDER BY operation_id LIMIT 1", (operation_code,))
        if row:
            return int(row[0])
        if operation_code == _normalize_code(os.getenv("YANDEX_MARKET_REVENUE_OPERATION_CODE", "revenue_marketplace_api")):
            return _resolve_yandex_operation_id(conn)
        raise HTTPException(400, f"Ozon revenue operation is not configured: {operation_code}")

    def _resolve_ozon_expense_operation_id(conn) -> int:
        # Используем общую операцию прямых расходов для удержаний и возвратов Ozon.
        operation_id = _env_int("OZON_EXPENSE_OPERATION_ID")
        if operation_id is not None:
            row = q1(conn, "SELECT operation_id FROM finance.operations WHERE operation_id=%s AND is_active IS TRUE", (operation_id,))
            if not row:
                raise HTTPException(400, f"Unknown OZON_EXPENSE_OPERATION_ID: {operation_id}")
            return int(row[0])
        operation_code = _normalize_code(os.getenv("OZON_EXPENSE_OPERATION_CODE", "direct_marketplace_commission_api"))
        row = q1(conn, "SELECT operation_id FROM finance.operations WHERE lower(code)=%s AND is_active IS TRUE ORDER BY operation_id LIMIT 1", (operation_code,))
        if row:
            return int(row[0])
        if operation_code == _normalize_code(os.getenv("YANDEX_MARKET_COMMISSION_OPERATION_CODE", "direct_marketplace_commission_api")):
            return _resolve_yandex_commission_operation_id(conn)
        raise HTTPException(400, f"Ozon expense operation is not configured: {operation_code}")

    def _money_from_yandex_raw(raw: dict[str, Any], keys: tuple[str, ...]) -> Decimal:
        # Достаем контрольные суммы из сырой строки Яндекса для дневного payload_json.
        for key in keys:
            value = raw.get(key)
            if value in (None, ""):
                continue
            try:
                return Decimal(str(value).replace(" ", "").replace(",", "."))
            except Exception:
                continue
        return Decimal("0")

    def _aggregate_yandex_market_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Сворачиваем строки заказов в один дневной итог, чтобы finance.entries не разрастался построчно.
        grouped: dict[date, dict[str, Any]] = {}
        for row in rows:
            biz_date = row.get("biz_date")
            if not isinstance(biz_date, date):
                continue
            payload_json = row.get("payload_json") if isinstance(row.get("payload_json"), dict) else {}
            raw = payload_json.get("raw") if isinstance(payload_json.get("raw"), dict) else {}
            amount_decimal = _round_money(Decimal(row.get("amount") or 0))
            if amount_decimal == 0:
                continue
            group = grouped.setdefault(
                biz_date,
                {
                    "biz_date": biz_date,
                    "amount": Decimal("0"),
                    "gross_amount": Decimal("0"),
                    "commission_amount": Decimal("0"),
                    "rows_count": 0,
                    "order_ids": [],
                    "shop_skus": [],
                    "source_files": set(),
                    "campaign_id": payload_json.get("campaign_id"),
                },
            )
            group["amount"] = _round_money(group["amount"] + amount_decimal)
            group["gross_amount"] = _round_money(
                group["gross_amount"] + _money_from_yandex_raw(raw, ("sumBillingPriceOfItems", "sum_billing_price_of_items"))
            )
            group["commission_amount"] = _round_money(
                group["commission_amount"] + _money_from_yandex_raw(raw, ("summaryCommission", "summary_commission"))
            )
            group["rows_count"] += 1
            if row.get("order_id"):
                group["order_ids"].append(str(row.get("order_id")))
            if row.get("shop_sku"):
                group["shop_skus"].append(str(row.get("shop_sku")))
            if payload_json.get("source_file"):
                group["source_files"].add(str(payload_json.get("source_file")))

        aggregates: list[dict[str, Any]] = []
        fallback_campaign_id = str(os.getenv("YANDEX_MARKET_CAMPAIGN_ID", "") or "").strip()
        for biz_date, group in sorted(grouped.items(), key=lambda item: item[0]):
            campaign_id = group.get("campaign_id") or fallback_campaign_id or "unknown"
            unique_order_ids = sorted(set(group["order_ids"]))
            unique_shop_skus = sorted(set(group["shop_skus"]))
            net_amount = _round_money(group["amount"])
            gross_amount = _round_money(group["gross_amount"])
            commission_amount = _round_money(group["commission_amount"])
            if gross_amount == 0:
                gross_amount = _round_money(net_amount + commission_amount)
            if commission_amount == 0 and gross_amount > net_amount:
                commission_amount = _round_money(gross_amount - net_amount)
            aggregates.append(
                {
                    "biz_date": biz_date,
                    "amount": net_amount,
                    "gross_amount": gross_amount,
                    "commission_amount": commission_amount,
                    "external_key_base": f"yandex-market:united-orders:{campaign_id}:daily:{biz_date.isoformat()}",
                    "comment": f"Yandex Market; доставленные за {biz_date.isoformat()}; строк {group['rows_count']}",
                    "payload_json": {
                        "provider": "yandex_market",
                        "report_type": "united_orders",
                        "aggregation": "daily",
                        "campaign_id": campaign_id,
                        "biz_date": biz_date.isoformat(),
                        "status_filter": "Доставлен",
                        "rows_count": group["rows_count"],
                        "orders_count": len(unique_order_ids),
                        "order_ids": unique_order_ids,
                        "shop_skus": unique_shop_skus,
                        "source_files": sorted(group["source_files"]),
                        "gross_amount": str(gross_amount),
                        "commission_amount": str(commission_amount),
                        "income_without_services": str(net_amount),
                    },
                }
            )
        return aggregates

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

    def _upsert_entry_in_tx(conn, payload: FinanceEntryCreateIn, created_by: str) -> tuple[FinanceEntryOut, str]:
        # Обновляет API-запись с тем же external_key, чтобы повторная синхронизация брала свежие суммы.
        item, created = _create_entry_in_tx(conn, payload, created_by)
        if created:
            return item, "created"
        if not (payload.external_key or "").strip():
            return item, "skipped"
        if item.biz_date != payload.biz_date:
            raise HTTPException(409, "Existing finance entry date does not match external_key date")

        operation = _load_operation(conn, payload.operation_id)
        metric_code = _metric_from_section_kind(operation["type_code"])
        status_code = _normalize_code(payload.status_code)
        rounded_amount = _round_money(payload.amount)
        entry_row = q1(
            conn,
            """
            UPDATE finance.entries
            SET operation_id=%s,
                region_id=%s,
                source_id=%s,
                project_id=%s,
                qty=%s,
                amount=%s,
                currency=%s,
                status_code=%s,
                comment=%s,
                payload_json=%s::jsonb,
                app_deal_id=%s,
                app_deal_item_id=%s,
                updated_at=now()
            WHERE entry_id=%s AND biz_date=%s
            RETURNING entry_id, biz_date, operation_id, region_id, source_id, project_id,
                      qty, amount, currency, input_channel, external_key, status_code,
                      comment, created_by, created_at, updated_at
            """,
            (
                payload.operation_id,
                payload.region_id,
                payload.source_id,
                payload.project_id,
                payload.qty,
                rounded_amount,
                _normalize_code(payload.currency, upper=True),
                status_code,
                (payload.comment or "").strip() or None,
                json.dumps(payload.payload_json or {}),
                payload.app_deal_id,
                payload.app_deal_item_id,
                item.entry_id,
                item.biz_date,
            ),
        )
        if not entry_row:
            raise HTTPException(500, "Failed to update finance entry")

        # Пересобираем проводку, потому что у существующей API-записи могла измениться сумма или операция.
        exec1(conn, "DELETE FROM finance.entry_postings WHERE entry_id=%s AND entry_biz_date=%s", (item.entry_id, item.biz_date))
        exec1(
            conn,
            """
            INSERT INTO finance.entry_postings(entry_id, entry_biz_date, metric_code, amount)
            VALUES (%s, %s, %s, %s)
            """,
            (item.entry_id, item.biz_date, metric_code, rounded_amount),
        )
        exec1(
            conn,
            """
            INSERT INTO finance.entry_audit(entry_id, entry_biz_date, action, changed_by, old_data, new_data)
            VALUES (%s, %s, 'update', %s, %s::jsonb, %s::jsonb)
            """,
            (
                item.entry_id,
                item.biz_date,
                created_by,
                json.dumps(
                    {
                        "amount": str(_round_money(item.amount)),
                        "operation_id": item.operation_id,
                        "status_code": item.status_code,
                        "comment": item.comment,
                    }
                ),
                json.dumps(
                    {
                        "amount": str(rounded_amount),
                        "operation_id": payload.operation_id,
                        "status_code": status_code,
                        "comment": (payload.comment or "").strip() or None,
                    }
                ),
            ),
        )
        return _to_entry_out(entry_row), "updated"

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
                  operation_id, type_id, source_id, code, name, input_mode,
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
                    source_id=int(r[2]) if r[2] is not None else None,
                    code=r[3],
                    name=r[4],
                    input_mode=r[5],
                    requires_region=bool(r[6]),
                    requires_source=bool(r[7]),
                    requires_project=bool(r[8]),
                    requires_qty=bool(r[9]),
                    allows_negative=bool(r[10]),
                    sort_order=int(r[11] or 0),
                    is_active=bool(r[12]),
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
    def finance_delete_type(
        type_id: int,
        cascade_entries: bool = False,
        user=Depends(require_role("admin", "owner")),
    ):
        # Архивируем тип; при cascade_entries=true удаляем проводки и деактивируем связанные сущности.
        with psycopg.connect(DB_DSN) as conn:
            current = q1(conn, "SELECT code FROM finance.section_types WHERE type_id=%s", (type_id,))
            if not current:
                raise HTTPException(404, "Type not found")
            if current[0] in {"revenue", "direct_expense", "indirect_expense"}:
                raise HTTPException(400, "System type cannot be deleted")
            if cascade_entries:
                exec1(
                    conn,
                    """
                    DELETE FROM finance.entries e
                    USING finance.operations o
                    WHERE e.operation_id = o.operation_id
                      AND o.type_id = %s
                    """,
                    (type_id,),
                )
                exec1(
                    conn,
                    "UPDATE finance.operations SET is_active=false, updated_at=now() WHERE type_id=%s",
                    (type_id,),
                )
                exec1(
                    conn,
                    "UPDATE finance.sections SET is_active=false, updated_at=now() WHERE type_id=%s",
                    (type_id,),
                )
            else:
                has_sections = q1(
                    conn,
                    "SELECT 1 FROM finance.sections WHERE type_id=%s AND is_active IS TRUE LIMIT 1",
                    (type_id,),
                )
                if has_sections:
                    raise HTTPException(409, "Type has active sections")
                has_operations = q1(
                    conn,
                    "SELECT 1 FROM finance.operations WHERE type_id=%s AND is_active IS TRUE LIMIT 1",
                    (type_id,),
                )
                if has_operations:
                    raise HTTPException(409, "Type has operations and cannot be deleted")
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
            _ensure_lookup_exists(conn, "dim_sources", "source_id", payload.source_id, "source_id")
            row = q1(
                conn,
                """
                INSERT INTO finance.operations(
                  type_id, source_id, code, name, input_mode,
                  requires_region, requires_source, requires_project, requires_qty, allows_negative,
                  sort_order, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)
                RETURNING operation_id, type_id, source_id, code, name, input_mode,
                          requires_region, requires_source, requires_project, requires_qty,
                          allows_negative, sort_order, is_active
                """,
                (
                    payload.type_id,
                    payload.source_id,
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
                SELECT operation_id, type_id, source_id, code, name, input_mode,
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
            next_source_id = int(payload.source_id) if payload.source_id is not None else (int(current[2]) if current[2] is not None else None)
            _ensure_lookup_exists(conn, "dim_sources", "source_id", next_source_id, "source_id")
            next_code = _normalize_code(payload.code) if payload.code is not None else current[3]
            next_name = (payload.name or "").strip() if payload.name is not None else current[4]
            next_mode = _normalize_operation_mode(payload.input_mode) if payload.input_mode is not None else current[5]
            next_requires_region = bool(payload.requires_region) if payload.requires_region is not None else bool(current[6])
            next_requires_source = bool(payload.requires_source) if payload.requires_source is not None else bool(current[7])
            next_requires_project = bool(payload.requires_project) if payload.requires_project is not None else bool(current[8])
            next_requires_qty = bool(payload.requires_qty) if payload.requires_qty is not None else bool(current[9])
            next_allows_negative = bool(payload.allows_negative) if payload.allows_negative is not None else bool(current[10])
            next_sort = int(payload.sort_order) if payload.sort_order is not None else int(current[11] or 0)
            next_active = bool(payload.is_active) if payload.is_active is not None else bool(current[12])
            row = q1(
                conn,
                """
                UPDATE finance.operations
                SET type_id=%s, source_id=%s, code=%s, name=%s, input_mode=%s,
                    requires_region=%s, requires_source=%s, requires_project=%s, requires_qty=%s,
                    allows_negative=%s, sort_order=%s, is_active=%s, updated_at=now()
                WHERE operation_id=%s
                RETURNING operation_id, type_id, source_id, code, name, input_mode,
                          requires_region, requires_source, requires_project, requires_qty,
                          allows_negative, sort_order, is_active
                """,
                (
                    next_type_id,
                    next_source_id,
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
            if next_type_id != int(current[1]):
                _rebuild_entry_postings_for_operation(conn, operation_id)
            conn.commit()
        if not row:
            raise HTTPException(500, "Failed to update operation")
        return _to_operation_out(row)

    @app.delete("/finance/catalogs/operations/{operation_id}")
    def finance_delete_operation(
        operation_id: int,
        cascade_entries: bool = False,
        user=Depends(require_role("admin", "owner")),
    ):
        # Архивируем операцию; при cascade_entries=true удаляем ее проводки.
        with psycopg.connect(DB_DSN) as conn:
            current = q1(conn, "SELECT 1 FROM finance.operations WHERE operation_id=%s", (operation_id,))
            if not current:
                raise HTTPException(404, "Operation not found")
            if cascade_entries:
                exec1(conn, "DELETE FROM finance.entries WHERE operation_id=%s", (operation_id,))
            else:
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

    def _sync_yandex_market_now(
        payload: FinanceYandexSyncIn,
        created_by: str,
        progress: Optional[Any] = None,
    ) -> FinanceYandexSyncOut:
        # Выполняем фактический импорт Яндекса; helper используют фоновые ручные задачи.
        if payload.date_to < payload.date_from:
            raise HTTPException(400, "date_to must be >= date_from")

        store_code = normalize_yandex_market_store_code(payload.store_code)
        rows = fetch_yandex_market_order_economics(payload.date_from, payload.date_to, store_code=store_code, progress=progress)
        daily_rows = _aggregate_yandex_market_rows(rows)
        created_rows = 0
        updated_rows = 0
        skipped_rows = 0
        failed_rows = 0
        errors: list[FinanceEntryBulkErrorOut] = []

        with psycopg.connect(DB_DSN) as conn:
            if progress:
                progress("Проверяем finance-справочники для Yandex Market")
            source_id = _resolve_yandex_source_id(conn, store_code)
            project_id = _resolve_yandex_project_id(conn)
            revenue_operation_id = _resolve_yandex_operation_id(conn)
            commission_operation_id: Optional[int] = None

            for idx, row in enumerate(daily_rows, start=1):
                if progress:
                    progress(f"Сохраняем дневной итог Yandex Market: {idx}/{len(daily_rows)}")
                amount = row.get("gross_amount")
                external_key_base = str(row.get("external_key_base") or "")
                try:
                    if amount is None:
                        skipped_rows += 1
                        continue
                    gross_amount = _round_money(Decimal(amount))
                    commission_amount = _round_money(Decimal(row.get("commission_amount") or 0))
                    if gross_amount == 0:
                        skipped_rows += 1
                        continue
                    payload_json = {**(row.get("payload_json") or {}), "store_code": store_code}
                    revenue_payload = FinanceEntryCreateIn(
                        biz_date=row["biz_date"],
                        operation_id=revenue_operation_id,
                        region_id=None,
                        source_id=source_id,
                        project_id=project_id,
                        qty=Decimal("1"),
                        amount=gross_amount,
                        currency="RUB",
                        input_channel="api",
                        external_key=f"{external_key_base}:gross",
                        status_code="confirmed",
                        comment=f"{row.get('comment') or 'Yandex Market'}; поступления gross",
                        payload_json={**payload_json, "amount_kind": "gross_revenue"},
                    )
                    _, revenue_state = _upsert_entry_in_tx(conn, revenue_payload, created_by)
                    day_created = revenue_state == "created"
                    day_updated = revenue_state == "updated"
                    if commission_amount > 0:
                        if commission_operation_id is None:
                            commission_operation_id = _resolve_yandex_commission_operation_id(conn)
                        commission_payload = FinanceEntryCreateIn(
                            biz_date=row["biz_date"],
                            operation_id=commission_operation_id,
                            region_id=None,
                            source_id=source_id,
                            project_id=project_id,
                            qty=Decimal("1"),
                            amount=commission_amount,
                            currency="RUB",
                            input_channel="api",
                            external_key=f"{external_key_base}:commission",
                            status_code="confirmed",
                            comment=f"{row.get('comment') or 'Yandex Market'}; комиссии и услуги",
                            payload_json={**payload_json, "amount_kind": "commission_expense"},
                        )
                        _, commission_state = _upsert_entry_in_tx(conn, commission_payload, created_by)
                        day_created = day_created or commission_state == "created"
                        day_updated = day_updated or commission_state == "updated"
                    if day_created:
                        created_rows += 1
                    elif day_updated:
                        updated_rows += 1
                    else:
                        skipped_rows += 1
                except Exception as exc:
                    failed_rows += 1
                    errors.append(FinanceEntryBulkErrorOut(row_no=idx, error=str(exc), external_key=external_key_base or None))
            conn.commit()

        return FinanceYandexSyncOut(
            store_code=store_code,
            date_from=payload.date_from,
            date_to=payload.date_to,
            total_rows=len(rows),
            created_rows=created_rows,
            updated_rows=updated_rows,
            skipped_rows=skipped_rows,
            failed_rows=failed_rows,
            errors=errors,
        )

    def _to_yandex_job_out(job_id: str, job: dict[str, Any]) -> FinanceYandexSyncJobOut:
        # Приводим внутреннее состояние фоновой синхронизации к API-ответу.
        return FinanceYandexSyncJobOut(
            job_id=job_id,
            status=str(job.get("status") or "unknown"),
            message=job.get("message"),
            result=job.get("result"),
            error=job.get("error"),
            created_at=job["created_at"],
            updated_at=job["updated_at"],
        )

    def _run_yandex_sync_job(job_id: str, payload: FinanceYandexSyncIn, created_by: str):
        # Фоновая задача не блокирует HTTP-запрос и обновляет статус для polling-а UI.
        now = datetime.now(timezone.utc)
        yandex_sync_jobs[job_id].update(status="running", message="Запрашиваем отчет Yandex Market", updated_at=now)
        def update_progress(message: str):
            # Обновляем человекочитаемый статус, чтобы UI показывал реальный этап синхронизации.
            yandex_sync_jobs[job_id].update(message=message, updated_at=datetime.now(timezone.utc))

        try:
            result = _sync_yandex_market_now(payload, created_by, progress=update_progress)
            yandex_sync_jobs[job_id].update(
                status="done",
                message="Синхронизация завершена",
                result=result,
                error=None,
                updated_at=datetime.now(timezone.utc),
            )
        except HTTPException as exc:
            yandex_sync_jobs[job_id].update(
                status="failed",
                message="Синхронизация завершилась ошибкой",
                error=str(exc.detail),
                updated_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            yandex_sync_jobs[job_id].update(
                status="failed",
                message="Синхронизация завершилась ошибкой",
                error=str(exc),
                updated_at=datetime.now(timezone.utc),
            )

    @app.post("/finance/integrations/yandex/sync", response_model=FinanceYandexSyncJobOut)
    def finance_sync_yandex_market(payload: FinanceYandexSyncIn, user=Depends(require_role("admin", "owner"))):
        # Стартуем ручную синхронизацию в фоне, чтобы кнопка не держала HTTP-запрос до готовности отчета.
        if payload.date_to < payload.date_from:
            raise HTTPException(400, "date_to must be >= date_from")
        store_code = normalize_yandex_market_store_code(payload.store_code)
        for existing_job_id, existing_job in list(yandex_sync_jobs.items()):
            if existing_job.get("store_code") == store_code and existing_job.get("status") in {"queued", "running"}:
                return _to_yandex_job_out(existing_job_id, existing_job)
        job_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        yandex_sync_jobs[job_id] = {
            "status": "queued",
            "message": "Синхронизация поставлена в очередь",
            "result": None,
            "error": None,
            "store_code": store_code,
            "date_from": payload.date_from.isoformat(),
            "date_to": payload.date_to.isoformat(),
            "created_at": now,
            "updated_at": now,
        }
        created_by = str(getattr(user, "username", "") or "")
        if str(os.getenv("FINANCE_YANDEX_SYNC_INLINE", "") or "").strip() == "1":
            _run_yandex_sync_job(job_id, payload, created_by)
        else:
            thread = threading.Thread(target=_run_yandex_sync_job, args=(job_id, payload, created_by), daemon=True)
            thread.start()
        return _to_yandex_job_out(job_id, yandex_sync_jobs[job_id])

    @app.get("/finance/integrations/yandex/sync/{job_id}", response_model=FinanceYandexSyncJobOut)
    def finance_get_yandex_sync_job(job_id: str, user=Depends(require_role("admin", "owner"))):
        # Отдаем текущий статус ручной синхронизации для polling-а UI.
        job = yandex_sync_jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Yandex sync job not found")
        return _to_yandex_job_out(job_id, job)

    def _sync_wildberries_now(
        payload: FinanceWildberriesSyncIn,
        created_by: str,
        progress: Optional[Any] = None,
    ) -> FinanceWildberriesSyncOut:
        # Загружает отчет WB и сохраняет дневные поступления и удержания в finance.entries.
        if payload.date_to < payload.date_from:
            raise HTTPException(400, "date_to must be >= date_from")
        store_code = normalize_wildberries_store_code(payload.store_code)
        rows = fetch_wildberries_sales_report(payload.date_from, payload.date_to, store_code=store_code, progress=progress)
        daily_rows = aggregate_wildberries_report_rows(rows, fallback_date=payload.date_from, store_code=store_code)
        created_rows = 0
        updated_rows = 0
        skipped_rows = 0
        failed_rows = 0
        errors: list[FinanceEntryBulkErrorOut] = []

        with psycopg.connect(DB_DSN) as conn:
            if progress:
                progress("Проверяем finance-справочники для Wildberries")
            source_id = _resolve_wildberries_source_id(conn, store_code)
            project_id = _resolve_wildberries_project_id(conn)
            revenue_operation_id = _resolve_wildberries_revenue_operation_id(conn)
            expense_operation_id = _resolve_wildberries_expense_operation_id(conn)

            for idx, row in enumerate(daily_rows, start=1):
                if progress:
                    progress(f"Сохраняем дневной итог Wildberries: {idx}/{len(daily_rows)}")
                external_key_base = str(row.get("external_key_base") or "")
                try:
                    gross_amount = _round_money(Decimal(row.get("gross_amount") or 0))
                    expense_amount = _round_money(Decimal(row.get("expense_amount") or 0))
                    if gross_amount <= 0 and expense_amount <= 0:
                        skipped_rows += 1
                        continue
                    payload_json = row.get("payload_json") if isinstance(row.get("payload_json"), dict) else {}
                    day_created = False
                    day_updated = False
                    if gross_amount > 0:
                        revenue_payload = FinanceEntryCreateIn(
                            biz_date=row["biz_date"],
                            operation_id=revenue_operation_id,
                            region_id=None,
                            source_id=source_id,
                            project_id=project_id,
                            qty=Decimal("1"),
                            amount=gross_amount,
                            currency="RUB",
                            input_channel="api",
                            external_key=f"{external_key_base}:gross",
                            status_code="confirmed",
                            comment=f"{row.get('comment') or 'Wildberries'}; продажи gross",
                            payload_json={**payload_json, "amount_kind": "gross_revenue"},
                        )
                        _, revenue_state = _upsert_entry_in_tx(conn, revenue_payload, created_by)
                        day_created = revenue_state == "created"
                        day_updated = revenue_state == "updated"
                    if expense_amount > 0:
                        expense_payload = FinanceEntryCreateIn(
                            biz_date=row["biz_date"],
                            operation_id=expense_operation_id,
                            region_id=None,
                            source_id=source_id,
                            project_id=project_id,
                            qty=Decimal("1"),
                            amount=expense_amount,
                            currency="RUB",
                            input_channel="api",
                            external_key=f"{external_key_base}:expense",
                            status_code="confirmed",
                            comment=f"{row.get('comment') or 'Wildberries'}; возвраты, комиссии и услуги",
                            payload_json={**payload_json, "amount_kind": "marketplace_expense"},
                        )
                        _, expense_state = _upsert_entry_in_tx(conn, expense_payload, created_by)
                        day_created = day_created or expense_state == "created"
                        day_updated = day_updated or expense_state == "updated"
                    if day_created:
                        created_rows += 1
                    elif day_updated:
                        updated_rows += 1
                    else:
                        skipped_rows += 1
                except Exception as exc:
                    failed_rows += 1
                    errors.append(FinanceEntryBulkErrorOut(row_no=idx, error=str(exc), external_key=external_key_base or None))
            conn.commit()

        return FinanceWildberriesSyncOut(
            store_code=store_code,
            date_from=payload.date_from,
            date_to=payload.date_to,
            total_rows=len(rows),
            created_rows=created_rows,
            updated_rows=updated_rows,
            skipped_rows=skipped_rows,
            failed_rows=failed_rows,
            errors=errors,
        )

    def _to_wildberries_job_out(job_id: str, job: dict[str, Any]) -> FinanceWildberriesSyncJobOut:
        # Преобразует внутренний статус фоновой задачи WB в публичную API-модель.
        return FinanceWildberriesSyncJobOut(
            job_id=job_id,
            status=str(job.get("status") or "unknown"),
            message=job.get("message"),
            result=job.get("result"),
            error=job.get("error"),
            retry_after_seconds=int(job.get("retry_after_seconds") or 0),
            created_at=job["created_at"],
            updated_at=job["updated_at"],
        )

    def _run_wildberries_sync_job(job_id: str, payload: FinanceWildberriesSyncIn, created_by: str):
        # Выполняет импорт WB в фоне и обновляет сообщение для polling-а интерфейса.
        wildberries_sync_jobs[job_id].update(status="running", message="Запрашиваем отчет Wildberries", updated_at=datetime.now(timezone.utc))

        def update_progress(message: str):
            # Передаем текущий этап загрузки в UI без раскрытия токена или содержимого строк.
            wildberries_sync_jobs[job_id].update(message=message, updated_at=datetime.now(timezone.utc))

        try:
            result = _sync_wildberries_now(payload, created_by, progress=update_progress)
            wildberries_sync_jobs[job_id].update(
                status="done",
                message="Синхронизация завершена",
                result=result,
                error=None,
                retry_after_seconds=0,
                updated_at=datetime.now(timezone.utc),
            )
        except HTTPException as exc:
            # Передаем UI точный остаток лимита, чтобы кнопка показывала обратный отсчет.
            error_text = str(exc.detail)
            retry_after_seconds = 0
            if exc.status_code == 429:
                match = re.search(r"через\s+(\d+)\s+сек", error_text, flags=re.IGNORECASE)
                retry_after_seconds = int(match.group(1)) if match else 60
            wildberries_sync_jobs[job_id].update(
                status="failed",
                message="Синхронизация завершилась ошибкой",
                error=error_text,
                retry_after_seconds=retry_after_seconds,
                updated_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            wildberries_sync_jobs[job_id].update(
                status="failed",
                message="Синхронизация завершилась ошибкой",
                error=str(exc),
                retry_after_seconds=0,
                updated_at=datetime.now(timezone.utc),
            )

    @app.post("/finance/integrations/wildberries/sync", response_model=FinanceWildberriesSyncJobOut)
    def finance_sync_wildberries(payload: FinanceWildberriesSyncIn, user=Depends(require_role("admin", "owner"))):
        # Ставит ручную синхронизацию WB в очередь и не запускает две задачи одновременно.
        if payload.date_to < payload.date_from:
            raise HTTPException(400, "date_to must be >= date_from")
        store_code = normalize_wildberries_store_code(payload.store_code)
        for existing_job_id, existing_job in list(wildberries_sync_jobs.items()):
            if existing_job.get("store_code") == store_code and existing_job.get("status") in {"queued", "running"}:
                return _to_wildberries_job_out(existing_job_id, existing_job)
        job_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        wildberries_sync_jobs[job_id] = {
            "status": "queued",
            "message": "Синхронизация поставлена в очередь",
            "result": None,
            "error": None,
            "retry_after_seconds": 0,
            "store_code": store_code,
            "date_from": payload.date_from.isoformat(),
            "date_to": payload.date_to.isoformat(),
            "created_at": now,
            "updated_at": now,
        }
        created_by = str(getattr(user, "username", "") or "")
        if str(os.getenv("FINANCE_WILDBERRIES_SYNC_INLINE", "") or "").strip() == "1":
            _run_wildberries_sync_job(job_id, payload, created_by)
        else:
            thread = threading.Thread(target=_run_wildberries_sync_job, args=(job_id, payload, created_by), daemon=True)
            thread.start()
        return _to_wildberries_job_out(job_id, wildberries_sync_jobs[job_id])

    @app.get("/finance/integrations/wildberries/sync/{job_id}", response_model=FinanceWildberriesSyncJobOut)
    def finance_get_wildberries_sync_job(job_id: str, user=Depends(require_role("admin", "owner"))):
        # Возвращает состояние синхронизации WB для периодического опроса интерфейсом.
        job = wildberries_sync_jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Wildberries sync job not found")
        return _to_wildberries_job_out(job_id, job)

    def _sync_ozon_now(
        payload: FinanceOzonSyncIn,
        created_by: str,
        progress: Optional[Any] = None,
    ) -> FinanceOzonSyncOut:
        # Загружает операции Ozon и сохраняет дневные поступления и расходы в finance.entries.
        if payload.date_to < payload.date_from:
            raise HTTPException(400, "date_to must be >= date_from")
        store_code = normalize_ozon_store_code(payload.store_code)
        rows = fetch_ozon_finance_transactions(payload.date_from, payload.date_to, store_code=store_code, progress=progress)
        daily_rows = aggregate_ozon_finance_transactions(rows, fallback_date=payload.date_from, store_code=store_code)
        created_rows = 0
        updated_rows = 0
        skipped_rows = 0
        failed_rows = 0
        errors: list[FinanceEntryBulkErrorOut] = []

        with psycopg.connect(DB_DSN) as conn:
            if progress:
                progress("Проверяем finance-справочники для Ozon")
            source_id = _resolve_ozon_source_id(conn, store_code)
            project_id = _resolve_ozon_project_id(conn)
            revenue_operation_id = _resolve_ozon_revenue_operation_id(conn)
            expense_operation_id = _resolve_ozon_expense_operation_id(conn)

            for idx, row in enumerate(daily_rows, start=1):
                if progress:
                    progress(f"Сохраняем дневной итог Ozon: {idx}/{len(daily_rows)}")
                external_key_base = str(row.get("external_key_base") or "")
                try:
                    gross_amount = _round_money(Decimal(row.get("gross_amount") or 0))
                    expense_amount = _round_money(Decimal(row.get("expense_amount") or 0))
                    if gross_amount <= 0 and expense_amount <= 0:
                        skipped_rows += 1
                        continue
                    payload_json = row.get("payload_json") if isinstance(row.get("payload_json"), dict) else {}
                    day_created = False
                    day_updated = False
                    if gross_amount > 0:
                        revenue_payload = FinanceEntryCreateIn(
                            biz_date=row["biz_date"],
                            operation_id=revenue_operation_id,
                            region_id=None,
                            source_id=source_id,
                            project_id=project_id,
                            qty=Decimal("1"),
                            amount=gross_amount,
                            currency="RUB",
                            input_channel="api",
                            external_key=f"{external_key_base}:gross",
                            status_code="confirmed",
                            comment=f"{row.get('comment') or 'Ozon'}; начисления и компенсации",
                            payload_json={**payload_json, "amount_kind": "gross_revenue"},
                        )
                        _, revenue_state = _upsert_entry_in_tx(conn, revenue_payload, created_by)
                        day_created = revenue_state == "created"
                        day_updated = revenue_state == "updated"
                    if expense_amount > 0:
                        expense_payload = FinanceEntryCreateIn(
                            biz_date=row["biz_date"],
                            operation_id=expense_operation_id,
                            region_id=None,
                            source_id=source_id,
                            project_id=project_id,
                            qty=Decimal("1"),
                            amount=expense_amount,
                            currency="RUB",
                            input_channel="api",
                            external_key=f"{external_key_base}:expense",
                            status_code="confirmed",
                            comment=f"{row.get('comment') or 'Ozon'}; возвраты, комиссии, логистика и услуги",
                            payload_json={**payload_json, "amount_kind": "marketplace_expense"},
                        )
                        _, expense_state = _upsert_entry_in_tx(conn, expense_payload, created_by)
                        day_created = day_created or expense_state == "created"
                        day_updated = day_updated or expense_state == "updated"
                    if day_created:
                        created_rows += 1
                    elif day_updated:
                        updated_rows += 1
                    else:
                        skipped_rows += 1
                except Exception as exc:
                    failed_rows += 1
                    errors.append(FinanceEntryBulkErrorOut(row_no=idx, error=str(exc), external_key=external_key_base or None))
            conn.commit()

        return FinanceOzonSyncOut(
            store_code=store_code,
            date_from=payload.date_from,
            date_to=payload.date_to,
            total_rows=len(rows),
            created_rows=created_rows,
            updated_rows=updated_rows,
            skipped_rows=skipped_rows,
            failed_rows=failed_rows,
            errors=errors,
        )

    def _to_ozon_job_out(job_id: str, job: dict[str, Any]) -> FinanceOzonSyncJobOut:
        # Преобразует внутренний статус задачи Ozon в публичную модель для polling-а.
        return FinanceOzonSyncJobOut(
            job_id=job_id,
            status=str(job.get("status") or "unknown"),
            message=job.get("message"),
            result=job.get("result"),
            error=job.get("error"),
            retry_after_seconds=int(job.get("retry_after_seconds") or 0),
            created_at=job["created_at"],
            updated_at=job["updated_at"],
        )

    def _run_ozon_sync_job(job_id: str, payload: FinanceOzonSyncIn, created_by: str):
        # Выполняет импорт Ozon в фоне и передает текущий этап в интерфейс.
        ozon_sync_jobs[job_id].update(status="running", message="Запрашиваем операции Ozon", updated_at=datetime.now(timezone.utc))

        def update_progress(message: str):
            # Обновляем статус без передачи ключей и содержимого финансовых строк.
            ozon_sync_jobs[job_id].update(message=message, updated_at=datetime.now(timezone.utc))

        try:
            result = _sync_ozon_now(payload, created_by, progress=update_progress)
            ozon_sync_jobs[job_id].update(
                status="done",
                message="Синхронизация завершена",
                result=result,
                error=None,
                retry_after_seconds=0,
                updated_at=datetime.now(timezone.utc),
            )
        except HTTPException as exc:
            error_text = str(exc.detail)
            retry_after_seconds = 0
            if exc.status_code == 429:
                match = re.search(r"через\s+(\d+)\s+сек", error_text, flags=re.IGNORECASE)
                retry_after_seconds = int(match.group(1)) if match else 60
            ozon_sync_jobs[job_id].update(
                status="failed",
                message="Синхронизация завершилась ошибкой",
                error=error_text,
                retry_after_seconds=retry_after_seconds,
                updated_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            ozon_sync_jobs[job_id].update(
                status="failed",
                message="Синхронизация завершилась ошибкой",
                error=str(exc),
                retry_after_seconds=0,
                updated_at=datetime.now(timezone.utc),
            )

    @app.post("/finance/integrations/ozon/sync", response_model=FinanceOzonSyncJobOut)
    def finance_sync_ozon(payload: FinanceOzonSyncIn, user=Depends(require_role("admin", "owner"))):
        # Ставит синхронизацию Ozon в очередь и не запускает две задачи одного кабинета одновременно.
        if payload.date_to < payload.date_from:
            raise HTTPException(400, "date_to must be >= date_from")
        store_code = normalize_ozon_store_code(payload.store_code)
        for existing_job_id, existing_job in list(ozon_sync_jobs.items()):
            if existing_job.get("store_code") == store_code and existing_job.get("status") in {"queued", "running"}:
                return _to_ozon_job_out(existing_job_id, existing_job)
        job_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        ozon_sync_jobs[job_id] = {
            "status": "queued",
            "message": "Синхронизация поставлена в очередь",
            "result": None,
            "error": None,
            "retry_after_seconds": 0,
            "store_code": store_code,
            "date_from": payload.date_from.isoformat(),
            "date_to": payload.date_to.isoformat(),
            "created_at": now,
            "updated_at": now,
        }
        created_by = str(getattr(user, "username", "") or "")
        if str(os.getenv("FINANCE_OZON_SYNC_INLINE", "") or "").strip() == "1":
            _run_ozon_sync_job(job_id, payload, created_by)
        else:
            thread = threading.Thread(target=_run_ozon_sync_job, args=(job_id, payload, created_by), daemon=True)
            thread.start()
        return _to_ozon_job_out(job_id, ozon_sync_jobs[job_id])

    @app.get("/finance/integrations/ozon/sync/{job_id}", response_model=FinanceOzonSyncJobOut)
    def finance_get_ozon_sync_job(job_id: str, user=Depends(require_role("admin", "owner"))):
        # Возвращает состояние синхронизации Ozon для периодического опроса интерфейсом.
        job = ozon_sync_jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Ozon sync job not found")
        return _to_ozon_job_out(job_id, job)

    @app.delete("/finance/entries/{entry_id}")
    def finance_delete_entry(entry_id: int, user=Depends(require_role("admin", "owner"))):
        # Удаляем проводку по id; связанные posting/dedupe записи удаляются каскадно по FK.
        with psycopg.connect(DB_DSN) as conn:
            current = q1(conn, "SELECT 1 FROM finance.entries WHERE entry_id=%s", (entry_id,))
            if not current:
                raise HTTPException(404, "Entry not found")
            exec1(conn, "DELETE FROM finance.entries WHERE entry_id=%s", (entry_id,))
            conn.commit()
        return {"ok": True}

    @app.get("/finance/entries", response_model=FinanceEntryListOut)
    def finance_list_entries(
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        operation_id: Optional[int] = None,
        region_id: Optional[int] = None,
        source_id: Optional[int] = None,
        project_id: Optional[int] = None,
        status_code: Optional[str] = None,
        input_channel: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        user=Depends(get_current_user),
    ):
        # Собираем фильтры списка, чтобы журнал мог отделять ручной ввод от интеграций.
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
        if input_channel:
            filters.append("e.input_channel = %s")
            params.append(_normalize_channel(input_channel))

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

    @app.get("/finance/reports/sources", response_model=FinanceSourcesReportOut)
    def finance_report_sources(
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        region_id: Optional[list[int]] = Query(None),
        source_id: Optional[list[int]] = Query(None),
        operation_code: Optional[str] = None,
        user=Depends(get_current_user),
    ):
        # Строим cash flow по источникам из сделок app и ручных finance-проводок.
        params: list[Any] = []
        filters = ["activity_date IS NOT NULL"]
        if date_from is not None:
            filters.append("activity_date >= %s")
            params.append(date_from)
        if date_to is not None:
            filters.append("activity_date <= %s")
            params.append(date_to)
        normalized_operation_code = _normalize_code(operation_code)
        if normalized_operation_code:
            if normalized_operation_code not in {"sale", "rental", "source"}:
                raise HTTPException(400, "operation_code must be sale, rental or source")
            filters.append("operation_code = %s")
            params.append(normalized_operation_code)
        region_ids = [int(value) for value in (region_id or []) if value is not None]
        if region_ids and normalized_operation_code in {"", "sale"}:
            # Регион применяем только к услугам, чтобы шеринг и маркетплейсы не пропадали из своих отдельных режимов.
            filters.append("region_id = ANY(%s)")
            params.append(region_ids)
            if not normalized_operation_code:
                filters.append("operation_code = 'sale'")
        _append_multi_id_filter(filters, params, "source_id", source_id)
        where_sql = " AND ".join(filters)

        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                f"""
                WITH report_rows AS (
                    SELECT
                      d.completed_at::date AS activity_date,
                      fds.source_id,
                      COALESCE(fds.code, src.code) AS source_code,
                      COALESCE(fds.name, src.name, 'Без источника') AS source_name,
                      CASE WHEN fds.source_id IS NOT NULL OR d.deal_type_code = 'rental' THEN NULL ELSE fdr.region_id END AS region_id,
                      CASE WHEN fds.source_id IS NOT NULL OR d.deal_type_code = 'rental' THEN NULL ELSE COALESCE(fdr.code, rd.code) END AS region_code,
                      CASE WHEN fds.source_id IS NOT NULL OR d.deal_type_code = 'rental' THEN NULL ELSE COALESCE(fdr.name, rd.name, 'Без региона') END AS region_name,
                      CASE
                        WHEN fds.source_id IS NOT NULL THEN 'source'
                        WHEN d.deal_type_code = 'rental' THEN 'rental'
                        ELSE 'sale'
                      END AS operation_code,
                      CASE
                        WHEN fds.source_id IS NOT NULL THEN COALESCE(fds.name, src.name, 'Без источника')
                        WHEN d.deal_type_code = 'rental' THEN 'Шеринг'
                        ELSE 'Услуга'
                      END AS operation_name,
                      (di.price * di.qty) AS revenue,
                      CASE
                        WHEN d.deal_type_code = 'sale'
                        THEN di.purchase_cost * di.qty * COALESCE(rd.purchase_cost_rate, 1.0)
                        WHEN d.deal_type_code = 'rental'
                        THEN di.purchase_cost * di.qty
                        ELSE 0
                      END AS direct_expense,
                      ('deal-' || d.deal_id::text) AS row_ref_key
                    FROM app.deal_items di
                    JOIN app.deals d ON d.deal_id = di.deal_id
                    LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                    LEFT JOIN finance.dim_regions fdr ON fdr.app_region_id = rd.region_id
                    LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                    LEFT JOIN app.sources src ON src.source_id = c.source_id
                    LEFT JOIN finance.dim_sources fds ON fds.app_source_id = src.source_id
                    WHERE (
                        d.deal_type_code = 'sale'
                        OR (d.deal_type_code = 'rental' AND COALESCE(di.price, 0) > 0)
                      )
                      AND d.flow_status_code = 'completed'
                      AND d.status_code = 'confirmed'
                      AND d.completed_at IS NOT NULL
                      AND di.returned_at IS NULL

                    UNION ALL

                    SELECT
                      e.biz_date AS activity_date,
                      src.source_id,
                      src.code AS source_code,
                      COALESCE(src.name, 'Без источника') AS source_name,
                      CASE WHEN src.source_id IS NOT NULL THEN NULL ELSE r.region_id END AS region_id,
                      CASE WHEN src.source_id IS NOT NULL THEN NULL ELSE r.code END AS region_code,
                      CASE WHEN src.source_id IS NOT NULL THEN NULL ELSE COALESCE(r.name, 'Без региона') END AS region_name,
                      CASE WHEN src.source_id IS NOT NULL THEN 'source' ELSE 'entry' END AS operation_code,
                      CASE WHEN src.source_id IS NOT NULL THEN COALESCE(src.name, 'Без источника') ELSE o.name END AS operation_name,
                      CASE WHEN p.metric_code = 'revenue' THEN p.amount ELSE 0 END AS revenue,
                      CASE WHEN p.metric_code = 'direct_expense' THEN p.amount ELSE 0 END AS direct_expense,
                      ('entry-' || e.entry_id::text) AS row_ref_key
                    FROM finance.entry_postings p
                    JOIN finance.entries e
                      ON e.entry_id = p.entry_id
                     AND e.biz_date = p.entry_biz_date
                    JOIN finance.operations o ON o.operation_id = e.operation_id
                    JOIN finance.section_types st ON st.type_id = o.type_id
                    LEFT JOIN finance.dim_sources src ON src.source_id = e.source_id
                    LEFT JOIN finance.dim_regions r ON r.region_id = e.region_id
                    WHERE e.status_code = 'confirmed'
                      AND e.input_channel IN ('manual', 'api', 'import')
                      AND (
                        (st.code = 'revenue' AND p.metric_code = 'revenue')
                        OR (st.code = 'direct_expense' AND p.metric_code = 'direct_expense')
                      )
                )
                SELECT
                  source_id,
                  source_code,
                  source_name,
                  region_id,
                  region_code,
                  region_name,
                  operation_code,
                  operation_name,
                  COALESCE(SUM(revenue), 0) AS revenue,
                  COALESCE(SUM(direct_expense), 0) AS direct_expense,
                  COUNT(DISTINCT row_ref_key) AS deals_count
                FROM report_rows
                WHERE {where_sql}
                GROUP BY source_id, source_code, source_name, region_id, region_code, region_name, operation_code, operation_name
                HAVING COALESCE(SUM(revenue), 0) <> 0
                    OR COALESCE(SUM(direct_expense), 0) <> 0
                ORDER BY source_name, region_code NULLS LAST
                """,
                tuple(params),
            )

        items: list[FinanceSourcesReportRowOut] = []
        revenue_total = Decimal("0")
        direct_total = Decimal("0")
        for row in rows:
            row_revenue = _round_money(Decimal(row[8] or 0))
            row_direct = _round_money(Decimal(row[9] or 0))
            row_cash_flow = _round_money(row_revenue - row_direct)
            revenue_total += row_revenue
            direct_total += row_direct
            items.append(
                FinanceSourcesReportRowOut(
                    source_id=int(row[0]) if row[0] is not None else None,
                    source_code=str(row[1]) if row[1] is not None else None,
                    source_name=str(row[2]) if row[2] is not None else None,
                    region_id=int(row[3]) if row[3] is not None else None,
                    region_code=str(row[4]) if row[4] is not None else None,
                    region_name=str(row[5]) if row[5] is not None else None,
                    operation_code=str(row[6]) if row[6] is not None else None,
                    operation_name=str(row[7]) if row[7] is not None else None,
                    revenue=row_revenue,
                    direct_expense=row_direct,
                    cash_flow=row_cash_flow,
                    deals_count=int(row[10] or 0),
                )
            )

        revenue_total = _round_money(revenue_total)
        direct_total = _round_money(direct_total)
        cash_flow_total = _round_money(revenue_total - direct_total)
        margin_total = _round_ratio((cash_flow_total / revenue_total) if revenue_total != 0 else Decimal("0"))
        return FinanceSourcesReportOut(
            totals=FinancePnlTotalsOut(
                revenue=revenue_total,
                direct_expense=direct_total,
                indirect_expense=Decimal("0"),
                gross_profit=cash_flow_total,
                operating_profit=cash_flow_total,
                margin=margin_total,
            ),
            items=items,
        )

    @app.get("/finance/reports/sources/details", response_model=FinanceSourcesReportDetailsOut)
    def finance_report_sources_details(
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        source_id: Optional[int] = None,
        source_empty: bool = False,
        source_code: Optional[str] = None,
        region_id: Optional[int] = None,
        region_empty: bool = False,
        region_code: Optional[str] = None,
        operation_code: Optional[str] = None,
        user=Depends(get_current_user),
    ):
        # Отдаем расшифровку выбранной строки отчета по источникам без ручных SQL-запросов.
        filters = ["activity_date IS NOT NULL"]
        params: list[Any] = []
        if date_from is not None:
            filters.append("activity_date >= %s")
            params.append(date_from)
        if date_to is not None:
            filters.append("activity_date <= %s")
            params.append(date_to)
        normalized_source_code = _normalize_code(source_code)
        if source_id is not None:
            _append_nullable_id_filter(filters, params, "source_id", source_id, False)
        elif normalized_source_code:
            filters.append("source_code = %s")
            params.append(normalized_source_code)
        else:
            _append_nullable_id_filter(filters, params, "source_id", source_id, source_empty)
        normalized_region_code = _normalize_code(region_code, upper=True)
        if region_id is not None:
            _append_nullable_id_filter(filters, params, "region_id", region_id, False)
        elif normalized_region_code:
            filters.append("region_code = %s")
            params.append(normalized_region_code)
        else:
            _append_nullable_id_filter(filters, params, "region_id", region_id, region_empty)
            if region_empty:
                filters.append("NULLIF(region_code, '') IS NULL")
        normalized_operation_code = _normalize_code(operation_code)
        if normalized_operation_code:
            filters.append("operation_code = %s")
            params.append(normalized_operation_code)
        where_sql = " AND ".join(filters)

        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                f"""
                WITH detail_rows AS (
                  SELECT
                    'deal'::text AS row_type,
                    d.deal_id,
                    NULL::bigint AS entry_id,
                    d.completed_at::date AS activity_date,
                    NULLIF(d.order_number, '') AS order_number,
                    COALESCE(NULLIF(c.nickname, ''), NULLIF(c.customer_login, ''), '—') AS customer_name,
                    fds.source_id,
                    COALESCE(fds.code, src.code) AS source_code,
                    COALESCE(fds.name, src.name, 'Без источника') AS source_name,
                    CASE WHEN fds.source_id IS NOT NULL OR d.deal_type_code = 'rental' THEN NULL ELSE fdr.region_id END AS region_id,
                    CASE WHEN fds.source_id IS NOT NULL OR d.deal_type_code = 'rental' THEN NULL ELSE COALESCE(fdr.code, rd.code) END AS region_code,
                    CASE WHEN fds.source_id IS NOT NULL OR d.deal_type_code = 'rental' THEN NULL ELSE COALESCE(fdr.name, rd.name, 'Без региона') END AS region_name,
                    CASE
                      WHEN fds.source_id IS NOT NULL THEN 'source'
                      WHEN d.deal_type_code = 'rental' THEN 'rental'
                      ELSE 'sale'
                    END AS operation_code,
                    CASE
                      WHEN fds.source_id IS NOT NULL THEN COALESCE(fds.name, src.name, 'Без источника')
                      WHEN d.deal_type_code = 'rental' THEN 'Шеринг'
                      ELSE 'Услуга'
                    END AS operation_name,
                    STRING_AGG(COALESCE(NULLIF(p.title, ''), 'item-' || di.deal_item_id::text), '; ' ORDER BY di.deal_item_id) AS item_title,
                    COALESCE(SUM(di.qty), 0) AS qty,
                    COALESCE(SUM(di.price * di.qty), 0) AS revenue,
                    COALESCE(SUM(di.purchase_cost * di.qty), 0) AS purchase_cost,
                    CASE WHEN d.deal_type_code = 'sale' THEN COALESCE(MAX(rd.purchase_cost_rate), 1.0) ELSE NULL END AS purchase_cost_rate,
                    COALESCE(SUM(
                      CASE
                        WHEN d.deal_type_code = 'sale'
                        THEN di.purchase_cost * di.qty * COALESCE(rd.purchase_cost_rate, 1.0)
                        WHEN d.deal_type_code = 'rental'
                        THEN di.purchase_cost * di.qty
                        ELSE 0
                      END
                    ), 0) AS direct_expense,
                    NULL::text AS comment,
                    NULL::text AS external_key,
                    '[]'::jsonb AS order_ids,
                    '[]'::jsonb AS shop_skus,
                    0::integer AS orders_count,
                    0::integer AS rows_count,
                    CASE
                      WHEN d.deal_type_code = 'rental' THEN 'Шеринг считается без региона'
                      WHEN fds.source_id IS NULL THEN 'Источник клиента не привязан к finance source'
                      ELSE 'Источник клиента связан с finance source'
                    END AS reason
                  FROM app.deal_items di
                  JOIN app.deals d ON d.deal_id = di.deal_id
                  LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                  LEFT JOIN finance.dim_regions fdr ON fdr.app_region_id = rd.region_id
                  LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                  LEFT JOIN app.sources src ON src.source_id = c.source_id
                  LEFT JOIN finance.dim_sources fds ON fds.app_source_id = src.source_id
                  LEFT JOIN app.products p ON p.product_id = di.product_id
                  WHERE (
                      d.deal_type_code = 'sale'
                      OR (d.deal_type_code = 'rental' AND COALESCE(di.price, 0) > 0)
                    )
                    AND d.flow_status_code = 'completed'
                    AND d.status_code = 'confirmed'
                    AND d.completed_at IS NOT NULL
                    AND di.returned_at IS NULL
                  GROUP BY
                    d.deal_id, d.completed_at::date, d.order_number,
                    c.nickname, c.customer_login,
                    fds.source_id, fds.code, src.code, fds.name, src.name,
                    fdr.region_id, fdr.code, rd.code, fdr.name, rd.name,
                    d.deal_type_code

                  UNION ALL

                  SELECT
                    'entry'::text AS row_type,
                    NULL::bigint AS deal_id,
                    e.entry_id,
                    e.biz_date AS activity_date,
                    NULL::text AS order_number,
                    NULL::text AS customer_name,
                    src.source_id,
                    src.code AS source_code,
                    COALESCE(src.name, 'Без источника') AS source_name,
                    CASE WHEN src.source_id IS NOT NULL THEN NULL ELSE r.region_id END AS region_id,
                    CASE WHEN src.source_id IS NOT NULL THEN NULL ELSE r.code END AS region_code,
                    CASE WHEN src.source_id IS NOT NULL THEN NULL ELSE COALESCE(r.name, 'Без региона') END AS region_name,
                    CASE WHEN src.source_id IS NOT NULL THEN 'source' ELSE 'entry' END AS operation_code,
                    o.name AS operation_name,
                    COALESCE(NULLIF(e.comment, ''), o.name) AS item_title,
                    e.qty,
                    CASE WHEN p.metric_code = 'revenue' THEN p.amount ELSE 0 END AS revenue,
                    0::numeric AS purchase_cost,
                    NULL::numeric AS purchase_cost_rate,
                    CASE WHEN p.metric_code = 'direct_expense' THEN p.amount ELSE 0 END AS direct_expense,
                    e.comment,
                    e.external_key,
                    COALESCE(e.payload_json->'order_ids', '[]'::jsonb) AS order_ids,
                    COALESCE(e.payload_json->'shop_skus', '[]'::jsonb) AS shop_skus,
                    COALESCE((e.payload_json->>'orders_count')::integer, 0) AS orders_count,
                    COALESCE((e.payload_json->>'rows_count')::integer, 0) AS rows_count,
                    CASE
                      WHEN e.input_channel = 'api' THEN 'API-проводка finance'
                      WHEN e.input_channel = 'import' THEN 'Импортированная проводка finance'
                      ELSE 'Ручная проводка finance'
                    END AS reason
                  FROM finance.entry_postings p
                  JOIN finance.entries e
                    ON e.entry_id = p.entry_id
                   AND e.biz_date = p.entry_biz_date
                  JOIN finance.operations o ON o.operation_id = e.operation_id
                  JOIN finance.section_types st ON st.type_id = o.type_id
                  LEFT JOIN finance.dim_sources src ON src.source_id = e.source_id
                  LEFT JOIN finance.dim_regions r ON r.region_id = e.region_id
                  WHERE e.status_code = 'confirmed'
                    AND e.input_channel IN ('manual', 'api', 'import')
                    AND (
                      (st.code = 'revenue' AND p.metric_code = 'revenue')
                      OR (st.code = 'direct_expense' AND p.metric_code = 'direct_expense')
                    )
                )
                SELECT
                  row_type, deal_id, entry_id, activity_date, order_number, customer_name,
                  source_id, source_code, source_name,
                  region_id, region_code, region_name,
                  operation_name, item_title, qty, revenue, purchase_cost,
                  purchase_cost_rate, direct_expense, comment, external_key,
                  order_ids, shop_skus, orders_count, rows_count, reason
                FROM detail_rows
                WHERE {where_sql}
                  AND (
                    COALESCE(revenue, 0) <> 0
                    OR COALESCE(purchase_cost, 0) <> 0
                    OR COALESCE(direct_expense, 0) <> 0
                  )
                ORDER BY activity_date, COALESCE(deal_id, entry_id), row_type
                """,
                tuple(params),
            )

        items: list[FinanceSourcesReportDetailRowOut] = []
        revenue_total = Decimal("0")
        purchase_cost_total = Decimal("0")
        direct_total = Decimal("0")
        for row in rows:
            row_revenue = _round_money(Decimal(row[15] or 0))
            row_purchase_cost = _round_money(Decimal(row[16] or 0))
            row_direct = _round_money(Decimal(row[18] or 0))
            row_cash_flow = _round_money(row_revenue - row_direct)
            revenue_total += row_revenue
            purchase_cost_total += row_purchase_cost
            direct_total += row_direct
            items.append(
                FinanceSourcesReportDetailRowOut(
                    row_type=str(row[0] or ""),
                    deal_id=int(row[1]) if row[1] is not None else None,
                    entry_id=int(row[2]) if row[2] is not None else None,
                    activity_date=row[3],
                    customer_name=str(row[5]) if row[5] is not None else None,
                    source_id=int(row[6]) if row[6] is not None else None,
                    source_code=str(row[7]) if row[7] is not None else None,
                    source_name=str(row[8]) if row[8] is not None else None,
                    region_id=int(row[9]) if row[9] is not None else None,
                    region_code=str(row[10]) if row[10] is not None else None,
                    region_name=str(row[11]) if row[11] is not None else None,
                    operation_name=str(row[12]) if row[12] is not None else None,
                    item_title=str(row[13]) if row[13] is not None else None,
                    qty=Decimal(row[14] or 0),
                    revenue=row_revenue,
                    purchase_cost=row_purchase_cost,
                    purchase_cost_rate=Decimal(str(row[17])) if row[17] is not None else None,
                    direct_expense=row_direct,
                    cash_flow=row_cash_flow,
                    comment=str(row[19]) if row[19] is not None else None,
                    external_key=str(row[20]) if row[20] is not None else None,
                    order_ids=_json_list_as_strings(row[21]),
                    shop_skus=_json_list_as_strings(row[22]),
                    orders_count=int(row[23] or 0),
                    rows_count=int(row[24] or 0),
                    reason=str(row[25]) if row[25] is not None else None,
                )
            )

        revenue_total = _round_money(revenue_total)
        purchase_cost_total = _round_money(purchase_cost_total)
        direct_total = _round_money(direct_total)
        cash_flow_total = _round_money(revenue_total - direct_total)
        margin_total = _round_ratio((cash_flow_total / revenue_total) if revenue_total != 0 else Decimal("0"))
        title_source = "Без источника" if source_empty else (f"source_id={source_id}" if source_id is not None else "Все источники")
        title_region = "Без региона" if region_empty else (f"region_id={region_id}" if region_id is not None else "Все регионы")
        return FinanceSourcesReportDetailsOut(
            title=f"{title_source} / {title_region}",
            totals=FinanceSourcesReportDetailTotalsOut(
                revenue=revenue_total,
                purchase_cost=purchase_cost_total,
                direct_expense=direct_total,
                indirect_expense=Decimal("0"),
                gross_profit=cash_flow_total,
                operating_profit=cash_flow_total,
                margin=margin_total,
            ),
            items=items,
        )

    @app.put("/finance/cash-flow/opening-balance", response_model=FinanceCashFlowOpeningBalanceOut)
    def finance_upsert_cash_flow_opening_balance(
        payload: FinanceCashFlowOpeningBalanceIn,
        user=Depends(require_role("admin", "owner")),
    ):
        # Сохраняем ручной начальный остаток на первое число выбранного месяца.
        month_start = _parse_month(payload.month)
        amount = _round_money(Decimal(payload.amount or 0))
        comment = (payload.comment or "").strip() or None
        actor = getattr(user, "username", "") or ""
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                INSERT INTO finance.cash_flow_opening_balances(balance_month, amount, comment, created_by, updated_at)
                VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (balance_month) DO UPDATE
                SET amount=EXCLUDED.amount,
                    comment=EXCLUDED.comment,
                    updated_at=now()
                RETURNING balance_month, amount, comment, updated_at
                """,
                (month_start, amount, comment, actor),
            )
            conn.commit()
        if not row:
            raise HTTPException(500, "Failed to save opening balance")
        return FinanceCashFlowOpeningBalanceOut(
            month=row[0],
            amount=_round_money(Decimal(row[1] or 0)),
            comment=row[2],
            updated_at=row[3],
        )

    def _load_finance_card_balance(conn, card_code: str = "TR") -> FinanceCardBalanceOut:
        # Считаем баланс карты от последнего ручного снимка и завершенных TR-сделок после него.
        normalized_card_code = _normalize_code(card_code, upper=True) or "TR"
        region_code = "TR"
        currency = "TRY"
        snapshot_row = q1(
            conn,
            """
            SELECT card_code, region_code, currency, amount, comment, created_by, created_at
            FROM finance.card_balance_snapshots
            WHERE upper(card_code) = %s
            ORDER BY created_at DESC, snapshot_id DESC
            LIMIT 1
            """,
            (normalized_card_code,),
        )
        snapshot_at = snapshot_row[6] if snapshot_row else None
        snapshot_balance = _round_money(Decimal((snapshot_row or [None, None, None, 0])[3] or 0))
        filters = [
            "d.deal_type_code = 'sale'",
            "d.flow_status_code = 'completed'",
            "d.status_code = 'confirmed'",
            "d.completed_at IS NOT NULL",
            "di.returned_at IS NULL",
            "upper(COALESCE(rd.code, '')) = %s",
            "COALESCE(di.purchase_cost, 0) <> 0",
        ]
        params: list[Any] = [region_code]
        if snapshot_at is not None:
            filters.append("d.completed_at > %s")
            params.append(snapshot_at)
        spent_row = q1(
            conn,
            f"""
            SELECT COALESCE(SUM(di.purchase_cost * di.qty), 0) AS spent_after_snapshot
            FROM app.deal_items di
            JOIN app.deals d ON d.deal_id = di.deal_id
            LEFT JOIN app.regions rd ON rd.region_id = d.region_id
            WHERE {' AND '.join(filters)}
            """,
            tuple(params),
        )
        spent_after_snapshot = _round_money(Decimal((spent_row or [0])[0] or 0))
        return FinanceCardBalanceOut(
            card_code=normalized_card_code,
            region_code=region_code,
            currency=currency,
            snapshot_balance=snapshot_balance,
            spent_after_snapshot=spent_after_snapshot,
            current_balance=_round_money(snapshot_balance - spent_after_snapshot),
            snapshot_at=snapshot_at,
            snapshot_manual=bool(snapshot_row),
            comment=snapshot_row[4] if snapshot_row else None,
        )

    @app.get("/finance/card-balances/tr", response_model=FinanceCardBalanceOut)
    def finance_get_tr_card_balance(user=Depends(get_current_user)):
        # Возвращаем текущий баланс TR-карты для виджета в разделе Финансы.
        with psycopg.connect(DB_DSN) as conn:
            return _load_finance_card_balance(conn, "TR")

    @app.put("/finance/card-balances/tr", response_model=FinanceCardBalanceOut)
    def finance_set_tr_card_balance(
        payload: FinanceCardBalanceSetIn,
        user=Depends(require_role("admin", "owner")),
    ):
        # Фиксируем фактический баланс карты сейчас, чтобы будущие сделки списывались от нового снимка.
        amount = _round_money(Decimal(payload.amount or 0))
        comment = (payload.comment or "").strip() or None
        actor = getattr(user, "username", "") or ""
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                INSERT INTO finance.card_balance_snapshots(card_code, region_code, currency, amount, comment, created_by)
                VALUES ('TR', 'TR', 'TRY', %s, %s, %s)
                """,
                (amount, comment, actor),
            )
            conn.commit()
            return _load_finance_card_balance(conn, "TR")

    @app.get("/finance/reports/cash-flow", response_model=FinanceCashFlowReportOut)
    def finance_report_cash_flow(
        month: Optional[str] = None,
        user=Depends(get_current_user),
    ):
        # Строим месячный Cash Flow и остатки от ближайшего ручного начального баланса.
        month_start = _parse_month(month)
        next_month_start = _next_month_start(month_start)

        cash_flow_rows_sql = """
            SELECT
              d.completed_at::date AS activity_date,
              fds.source_id,
              CASE WHEN d.deal_type_code = 'rental' THEN NULL ELSE fdr.region_id END AS region_id,
              'revenue' AS line_type,
              CASE
                WHEN d.deal_type_code = 'rental' THEN 'Продажа Шеринг'
                ELSE CONCAT('Продажа ', COALESCE(fdr.code, rd.code, 'Без региона'))
              END AS line_name,
              (di.price * di.qty) AS amount
            FROM app.deal_items di
            JOIN app.deals d ON d.deal_id = di.deal_id
            LEFT JOIN app.regions rd ON rd.region_id = d.region_id
            LEFT JOIN finance.dim_regions fdr ON fdr.app_region_id = rd.region_id
            LEFT JOIN app.customers c ON c.customer_id = d.customer_id
            LEFT JOIN app.sources src ON src.source_id = c.source_id
            LEFT JOIN finance.dim_sources fds ON fds.app_source_id = src.source_id
            WHERE (
                d.deal_type_code = 'sale'
                OR (d.deal_type_code = 'rental' AND COALESCE(di.price, 0) > 0)
              )
              AND d.flow_status_code = 'completed'
              AND d.status_code = 'confirmed'
              AND d.completed_at IS NOT NULL
              AND di.returned_at IS NULL
              AND COALESCE(di.price, 0) > 0

            UNION ALL

            SELECT
              d.completed_at::date AS activity_date,
              fds.source_id,
              NULL AS region_id,
              'expense' AS line_type,
              'Закуп Шеринг' AS line_name,
              (di.purchase_cost * di.qty) AS amount
            FROM app.deal_items di
            JOIN app.deals d ON d.deal_id = di.deal_id
            LEFT JOIN app.regions rd ON rd.region_id = d.region_id
            LEFT JOIN app.customers c ON c.customer_id = d.customer_id
            LEFT JOIN app.sources src ON src.source_id = c.source_id
            LEFT JOIN finance.dim_sources fds ON fds.app_source_id = src.source_id
            WHERE d.deal_type_code = 'rental'
              AND d.flow_status_code = 'completed'
              AND d.status_code = 'confirmed'
              AND d.completed_at IS NOT NULL
              AND di.returned_at IS NULL
              AND COALESCE(di.purchase_cost, 0) <> 0

            UNION ALL

            SELECT
              d.completed_at::date AS activity_date,
              fds.source_id,
              fdr.region_id,
              'expense' AS line_type,
              CONCAT('Закуп ', COALESCE(fdr.code, rd.code, 'Без региона')) AS line_name,
              (di.purchase_cost * di.qty * COALESCE(rd.purchase_cost_rate, 1.0)) AS amount
            FROM app.deal_items di
            JOIN app.deals d ON d.deal_id = di.deal_id
            LEFT JOIN app.regions rd ON rd.region_id = d.region_id
            LEFT JOIN finance.dim_regions fdr ON fdr.app_region_id = rd.region_id
            LEFT JOIN app.customers c ON c.customer_id = d.customer_id
            LEFT JOIN app.sources src ON src.source_id = c.source_id
            LEFT JOIN finance.dim_sources fds ON fds.app_source_id = src.source_id
            WHERE d.deal_type_code = 'sale'
              AND d.flow_status_code = 'completed'
              AND d.status_code = 'confirmed'
              AND d.completed_at IS NOT NULL
              AND di.returned_at IS NULL
              AND COALESCE(di.purchase_cost, 0) <> 0

            UNION ALL

            SELECT
              e.biz_date AS activity_date,
              e.source_id,
              e.region_id,
              CASE WHEN p.metric_code = 'revenue' THEN 'revenue' ELSE 'expense' END AS line_type,
              COALESCE(op.name, 'Ручная операция') AS line_name,
              p.amount AS amount
            FROM finance.entry_postings p
            JOIN finance.entries e
              ON e.entry_id = p.entry_id
             AND e.biz_date = p.entry_biz_date
            LEFT JOIN finance.operations op ON op.operation_id = e.operation_id
            WHERE e.status_code = 'confirmed'
              AND e.input_channel IN ('manual', 'api', 'import')
              AND p.metric_code IN ('revenue', 'direct_expense', 'indirect_expense')
              AND COALESCE(p.amount, 0) <> 0
        """

        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                f"""
                WITH cash_flow_rows AS (
                    {cash_flow_rows_sql}
                )
                SELECT
                  line_type,
                  line_name,
                  COALESCE(SUM(amount), 0) AS amount
                FROM cash_flow_rows
                WHERE activity_date >= %s
                  AND activity_date < %s
                GROUP BY line_type, line_name
                HAVING COALESCE(SUM(amount), 0) <> 0
                ORDER BY line_type DESC, line_name
                """,
                (month_start, next_month_start),
            )
            manual_opening_row = q1(
                conn,
                """
                SELECT balance_month, amount
                FROM finance.cash_flow_opening_balances
                WHERE balance_month <= %s
                ORDER BY balance_month DESC
                LIMIT 1
                """,
                (month_start,),
            )
            opening_balance_month = manual_opening_row[0] if manual_opening_row else None
            opening_balance = _round_money(Decimal((manual_opening_row or [None, 0])[1] or 0))
            if opening_balance_month is not None and opening_balance_month < month_start:
                accumulated_row = q1(
                    conn,
                    f"""
                    WITH cash_flow_rows AS (
                        {cash_flow_rows_sql}
                    )
                    SELECT COALESCE(SUM(
                      CASE WHEN line_type = 'revenue' THEN amount ELSE -amount END
                    ), 0) AS accumulated_cash_flow
                    FROM cash_flow_rows
                    WHERE activity_date >= %s
                      AND activity_date < %s
                    """,
                    (opening_balance_month, month_start),
                ) or (Decimal("0"),)
                opening_balance = _round_money(opening_balance + Decimal(accumulated_row[0] or 0))

        revenues: list[FinanceCashFlowLineOut] = []
        expenses: list[FinanceCashFlowLineOut] = []
        revenue_total = Decimal("0")
        expense_total = Decimal("0")
        for row in rows:
            line_amount = _round_money(Decimal(row[2] or 0))
            line = FinanceCashFlowLineOut(name=str(row[1] or "Без названия"), amount=line_amount)
            if row[0] == "revenue":
                revenues.append(line)
                revenue_total += line_amount
            else:
                expenses.append(line)
                expense_total += line_amount

        revenue_total = _round_money(revenue_total)
        expense_total = _round_money(expense_total)
        cash_flow_total = _round_money(revenue_total - expense_total)
        current_balance = _round_money(opening_balance + cash_flow_total)

        return FinanceCashFlowReportOut(
            totals=FinanceCashFlowTotalsOut(
                revenue=revenue_total,
                expense=expense_total,
                cash_flow=cash_flow_total,
                opening_balance=opening_balance,
                current_balance=current_balance,
                opening_balance_month=opening_balance_month,
                opening_balance_manual=bool(opening_balance_month == month_start),
            ),
            revenues=revenues,
            expenses=expenses,
        )

    @app.get("/finance/reports/cash-flow/details", response_model=FinanceCashFlowDetailsOut)
    def finance_report_cash_flow_details(
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        line_type: Optional[str] = None,
        line_name: Optional[str] = None,
        user=Depends(get_current_user),
    ):
        # Отдаем строки Cash Flow на уровне сделок и finance-проводок для проверки суммы за период.
        month_start = date.today().replace(day=1)
        date_from_value = date_from or month_start
        date_to_value = date_to or (_next_month_start(month_start) - timedelta(days=1))
        if date_to_value < date_from_value:
            raise HTTPException(400, "date_to must be greater than or equal to date_from")

        filters = ["activity_date >= %s", "activity_date <= %s"]
        params: list[Any] = [date_from_value, date_to_value]
        normalized_line_type = (line_type or "").strip().lower()
        if normalized_line_type:
            if normalized_line_type not in {"revenue", "expense"}:
                raise HTTPException(400, "line_type must be revenue or expense")
            filters.append("line_type = %s")
            params.append(normalized_line_type)
        normalized_line_name = (line_name or "").strip()
        if normalized_line_name:
            filters.append("line_name = %s")
            params.append(normalized_line_name)
        where_sql = " AND ".join(filters)

        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                f"""
                WITH completed_deal_authors AS (
                  SELECT DISTINCT ON (a.deal_id)
                    a.deal_id,
                    COALESCE(NULLIF(u.name, ''), a.changed_by) AS created_by
                  FROM app.deal_audit a
                  LEFT JOIN app.users u ON lower(u.username) = lower(a.changed_by)
                  WHERE a.table_name = 'deals'
                    AND a.action = 'UPDATE'
                    AND a.new_data->>'flow_status_code' = 'completed'
                    AND COALESCE(a.old_data->>'flow_status_code', '') <> 'completed'
                  ORDER BY a.deal_id, a.changed_at DESC, a.audit_id DESC
                ), detail_rows AS (
                  SELECT
                    'deal'::text AS row_type,
                    'revenue'::text AS line_type,
                    CASE
                      WHEN d.deal_type_code = 'rental' THEN 'Продажа Шеринг'
                      ELSE CONCAT('Продажа ', COALESCE(fdr.code, rd.code, 'Без региона'))
                    END AS line_name,
                    d.completed_at::date AS activity_date,
                    d.deal_id,
                    NULL::bigint AS entry_id,
                    COALESCE(NULLIF(c.nickname, ''), NULLIF(c.customer_login, ''), '—') AS customer_name,
                    CASE WHEN d.deal_type_code = 'rental' THEN 'Шеринг' ELSE 'Услуга' END AS operation_name,
                    STRING_AGG(COALESCE(NULLIF(p.title, ''), 'item-' || di.deal_item_id::text), '; ' ORDER BY di.deal_item_id) AS item_title,
                    CASE WHEN d.deal_type_code = 'rental' THEN NULL ELSE fdr.region_id END AS region_id,
                    CASE WHEN d.deal_type_code = 'rental' THEN NULL ELSE COALESCE(fdr.code, rd.code) END AS region_code,
                    CASE WHEN d.deal_type_code = 'rental' THEN NULL ELSE COALESCE(fdr.name, rd.name, 'Без региона') END AS region_name,
                    fds.source_id,
                    COALESCE(fds.code, src.code) AS source_code,
                    COALESCE(fds.name, src.name, 'Без источника') AS source_name,
                    COALESCE(SUM(di.qty), 0) AS qty,
                    COALESCE(SUM(di.price * di.qty), 0) AS amount,
                    NULL::text AS comment,
                    NULL::text AS external_key,
                    '[]'::jsonb AS order_ids,
                    '[]'::jsonb AS shop_skus,
                    0::integer AS orders_count,
                    0::integer AS rows_count,
                    closer.created_by,
                    CASE
                      WHEN d.deal_type_code = 'rental' THEN 'Поступление по завершенной сделке шеринга'
                      ELSE 'Поступление по завершенной продаже'
                    END AS reason
                  FROM app.deal_items di
                  JOIN app.deals d ON d.deal_id = di.deal_id
                  LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                  LEFT JOIN finance.dim_regions fdr ON fdr.app_region_id = rd.region_id
                  LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                  LEFT JOIN app.sources src ON src.source_id = c.source_id
                  LEFT JOIN finance.dim_sources fds ON fds.app_source_id = src.source_id
                  LEFT JOIN app.products p ON p.product_id = di.product_id
                  LEFT JOIN completed_deal_authors closer ON closer.deal_id = d.deal_id
                  WHERE (
                      d.deal_type_code = 'sale'
                      OR (d.deal_type_code = 'rental' AND COALESCE(di.price, 0) > 0)
                    )
                    AND d.flow_status_code = 'completed'
                    AND d.status_code = 'confirmed'
                    AND d.completed_at IS NOT NULL
                    AND di.returned_at IS NULL
                    AND COALESCE(di.price, 0) > 0
                  GROUP BY
                    d.deal_id, d.completed_at::date, d.deal_type_code,
                    c.nickname, c.customer_login,
                    fdr.region_id, fdr.code, rd.code, fdr.name, rd.name,
                    fds.source_id, fds.code, src.code, fds.name, src.name,
                    closer.created_by

                  UNION ALL

                  SELECT
                    'deal'::text AS row_type,
                    'expense'::text AS line_type,
                    'Закуп Шеринг' AS line_name,
                    d.completed_at::date AS activity_date,
                    d.deal_id,
                    NULL::bigint AS entry_id,
                    COALESCE(NULLIF(c.nickname, ''), NULLIF(c.customer_login, ''), '—') AS customer_name,
                    'Шеринг' AS operation_name,
                    STRING_AGG(COALESCE(NULLIF(p.title, ''), 'item-' || di.deal_item_id::text), '; ' ORDER BY di.deal_item_id) AS item_title,
                    NULL::bigint AS region_id,
                    NULL::text AS region_code,
                    NULL::text AS region_name,
                    fds.source_id,
                    COALESCE(fds.code, src.code) AS source_code,
                    COALESCE(fds.name, src.name, 'Без источника') AS source_name,
                    COALESCE(SUM(di.qty), 0) AS qty,
                    COALESCE(SUM(di.purchase_cost * di.qty), 0) AS amount,
                    NULL::text AS comment,
                    NULL::text AS external_key,
                    '[]'::jsonb AS order_ids,
                    '[]'::jsonb AS shop_skus,
                    0::integer AS orders_count,
                    0::integer AS rows_count,
                    closer.created_by,
                    'Закупка по завершенной сделке шеринга' AS reason
                  FROM app.deal_items di
                  JOIN app.deals d ON d.deal_id = di.deal_id
                  LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                  LEFT JOIN app.sources src ON src.source_id = c.source_id
                  LEFT JOIN finance.dim_sources fds ON fds.app_source_id = src.source_id
                  LEFT JOIN app.products p ON p.product_id = di.product_id
                  LEFT JOIN completed_deal_authors closer ON closer.deal_id = d.deal_id
                  WHERE d.deal_type_code = 'rental'
                    AND d.flow_status_code = 'completed'
                    AND d.status_code = 'confirmed'
                    AND d.completed_at IS NOT NULL
                    AND di.returned_at IS NULL
                    AND COALESCE(di.purchase_cost, 0) <> 0
                  GROUP BY
                    d.deal_id, d.completed_at::date,
                    c.nickname, c.customer_login,
                    fds.source_id, fds.code, src.code, fds.name, src.name,
                    closer.created_by

                  UNION ALL

                  SELECT
                    'deal'::text AS row_type,
                    'expense'::text AS line_type,
                    CONCAT('Закуп ', COALESCE(fdr.code, rd.code, 'Без региона')) AS line_name,
                    d.completed_at::date AS activity_date,
                    d.deal_id,
                    NULL::bigint AS entry_id,
                    COALESCE(NULLIF(c.nickname, ''), NULLIF(c.customer_login, ''), '—') AS customer_name,
                    'Услуга' AS operation_name,
                    STRING_AGG(COALESCE(NULLIF(p.title, ''), 'item-' || di.deal_item_id::text), '; ' ORDER BY di.deal_item_id) AS item_title,
                    fdr.region_id,
                    COALESCE(fdr.code, rd.code) AS region_code,
                    COALESCE(fdr.name, rd.name, 'Без региона') AS region_name,
                    fds.source_id,
                    COALESCE(fds.code, src.code) AS source_code,
                    COALESCE(fds.name, src.name, 'Без источника') AS source_name,
                    COALESCE(SUM(di.qty), 0) AS qty,
                    COALESCE(SUM(di.purchase_cost * di.qty * COALESCE(rd.purchase_cost_rate, 1.0)), 0) AS amount,
                    NULL::text AS comment,
                    NULL::text AS external_key,
                    '[]'::jsonb AS order_ids,
                    '[]'::jsonb AS shop_skus,
                    0::integer AS orders_count,
                    0::integer AS rows_count,
                    closer.created_by,
                    'Закупка по завершенной продаже с коэффициентом региона' AS reason
                  FROM app.deal_items di
                  JOIN app.deals d ON d.deal_id = di.deal_id
                  LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                  LEFT JOIN finance.dim_regions fdr ON fdr.app_region_id = rd.region_id
                  LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                  LEFT JOIN app.sources src ON src.source_id = c.source_id
                  LEFT JOIN finance.dim_sources fds ON fds.app_source_id = src.source_id
                  LEFT JOIN app.products p ON p.product_id = di.product_id
                  LEFT JOIN completed_deal_authors closer ON closer.deal_id = d.deal_id
                  WHERE d.deal_type_code = 'sale'
                    AND d.flow_status_code = 'completed'
                    AND d.status_code = 'confirmed'
                    AND d.completed_at IS NOT NULL
                    AND di.returned_at IS NULL
                    AND COALESCE(di.purchase_cost, 0) <> 0
                  GROUP BY
                    d.deal_id, d.completed_at::date,
                    c.nickname, c.customer_login,
                    fdr.region_id, fdr.code, rd.code, fdr.name, rd.name,
                    fds.source_id, fds.code, src.code, fds.name, src.name,
                    closer.created_by

                  UNION ALL

                  SELECT
                    'entry'::text AS row_type,
                    CASE WHEN p.metric_code = 'revenue' THEN 'revenue' ELSE 'expense' END AS line_type,
                    COALESCE(op.name, 'Ручная операция') AS line_name,
                    e.biz_date AS activity_date,
                    e.app_deal_id AS deal_id,
                    e.entry_id,
                    NULL::text AS customer_name,
                    COALESCE(op.name, 'Ручная операция') AS operation_name,
                    COALESCE(NULLIF(e.comment, ''), op.name, 'Проводка finance') AS item_title,
                    r.region_id,
                    r.code AS region_code,
                    r.name AS region_name,
                    src.source_id,
                    src.code AS source_code,
                    src.name AS source_name,
                    e.qty,
                    p.amount,
                    e.comment,
                    e.external_key,
                    COALESCE(e.payload_json->'order_ids', '[]'::jsonb) AS order_ids,
                    COALESCE(e.payload_json->'shop_skus', '[]'::jsonb) AS shop_skus,
                    COALESCE((e.payload_json->>'orders_count')::integer, 0) AS orders_count,
                    COALESCE((e.payload_json->>'rows_count')::integer, 0) AS rows_count,
                    COALESCE(NULLIF(author.name, ''), e.created_by) AS created_by,
                    CASE
                      WHEN e.input_channel = 'api' THEN 'API-проводка finance'
                      WHEN e.input_channel = 'import' THEN 'Импортированная проводка finance'
                      ELSE 'Ручная проводка finance'
                    END AS reason
                  FROM finance.entry_postings p
                  JOIN finance.entries e
                    ON e.entry_id = p.entry_id
                   AND e.biz_date = p.entry_biz_date
                  LEFT JOIN finance.operations op ON op.operation_id = e.operation_id
                  LEFT JOIN finance.dim_regions r ON r.region_id = e.region_id
                  LEFT JOIN finance.dim_sources src ON src.source_id = e.source_id
                  LEFT JOIN app.users author ON lower(author.username) = lower(e.created_by)
                  WHERE e.status_code = 'confirmed'
                    AND e.input_channel IN ('manual', 'api', 'import')
                    AND p.metric_code IN ('revenue', 'direct_expense', 'indirect_expense')
                    AND COALESCE(p.amount, 0) <> 0
                )
                SELECT
                  row_type, line_type, line_name, activity_date, deal_id, entry_id,
                  customer_name, operation_name, item_title,
                  region_id, region_code, region_name,
                  source_id, source_code, source_name,
                  qty, amount, comment, external_key,
                  order_ids, shop_skus, orders_count, rows_count, created_by, reason
                FROM detail_rows
                WHERE {where_sql}
                  AND COALESCE(amount, 0) <> 0
                ORDER BY activity_date, line_type DESC, line_name, COALESCE(deal_id, entry_id)
                """,
                tuple(params),
            )

        items: list[FinanceCashFlowDetailRowOut] = []
        revenue_total = Decimal("0")
        expense_total = Decimal("0")
        for row in rows:
            row_line_type = str(row[1] or "")
            row_amount = _round_money(Decimal(row[16] or 0))
            if row_line_type == "revenue":
                revenue_total += row_amount
            else:
                expense_total += row_amount
            items.append(
                FinanceCashFlowDetailRowOut(
                    row_type=str(row[0] or ""),
                    line_type=row_line_type,
                    line_name=str(row[2] or "Без названия"),
                    activity_date=row[3],
                    deal_id=int(row[4]) if row[4] is not None else None,
                    entry_id=int(row[5]) if row[5] is not None else None,
                    customer_name=str(row[6]) if row[6] is not None else None,
                    operation_name=str(row[7]) if row[7] is not None else None,
                    item_title=str(row[8]) if row[8] is not None else None,
                    region_id=int(row[9]) if row[9] is not None else None,
                    region_code=str(row[10]) if row[10] is not None else None,
                    region_name=str(row[11]) if row[11] is not None else None,
                    source_id=int(row[12]) if row[12] is not None else None,
                    source_code=str(row[13]) if row[13] is not None else None,
                    source_name=str(row[14]) if row[14] is not None else None,
                    qty=Decimal(row[15] or 0),
                    amount=row_amount,
                    comment=str(row[17]) if row[17] is not None else None,
                    external_key=str(row[18]) if row[18] is not None else None,
                    order_ids=_json_list_as_strings(row[19]),
                    shop_skus=_json_list_as_strings(row[20]),
                    orders_count=int(row[21] or 0),
                    rows_count=int(row[22] or 0),
                    created_by=str(row[23]) if row[23] is not None else None,
                    reason=str(row[24]) if row[24] is not None else None,
                )
            )

        revenue_total = _round_money(revenue_total)
        expense_total = _round_money(expense_total)
        cash_flow_total = _round_money(revenue_total - expense_total)
        title_line_type = {"revenue": "Поступления", "expense": "Расходы"}.get(normalized_line_type, "Все строки")
        title_line_name = normalized_line_name or "Все строки"
        return FinanceCashFlowDetailsOut(
            title=f"{title_line_type}: {title_line_name}",
            totals=FinanceCashFlowTotalsOut(
                revenue=revenue_total,
                expense=expense_total,
                cash_flow=cash_flow_total,
                opening_balance=Decimal("0"),
                current_balance=Decimal("0"),
            ),
            items=items,
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
