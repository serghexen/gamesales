from dataclasses import dataclass
from datetime import date, datetime, timezone
from io import BytesIO
from typing import Any, Callable
import re
import ssl
import urllib.error
import urllib.request

from fastapi import HTTPException
from openpyxl import load_workbook


@dataclass
class ImportParsers:
    GAME_IMPORT_HEADERS: list[str]
    parse_import_platforms: Callable[[str], list[str]]
    validate_game_import_rows: Callable[..., tuple[list[dict[str, Any]], list[dict[str, Any]]]]
    read_games_from_excel: Callable[[bytes], list[dict[str, Any]]]
    read_accounts_from_excel: Callable[[bytes], list[dict[str, Any]]]
    read_slots_from_excel: Callable[[bytes], list[dict[str, Any]]]
    clean_slots_excel: Callable[[bytes], bytes]
    split_account: Callable[[str], tuple[str | None, str | None]]
    validate_account_import_rows: Callable[..., tuple[list[dict[str, Any]], list[dict[str, Any]]]]
    SLOT_FILE_TO_TYPE: dict[str, tuple[str, int]]
    normalize_slot_file_value: Callable[[str], str]
    normalize_cell_text: Callable[[Any], str]
    normalize_slot_date: Callable[[Any], str | None]
    normalize_slot_date_to_dt: Callable[[Any], datetime | None]
    resolve_source_id: Callable[[Any, str], int | None]
    validate_slot_import_rows: Callable[..., tuple[list[dict[str, Any]], list[dict[str, Any]], int]]
    detect_logo_mime_from_bytes: Callable[[bytes], str]
    fetch_logo_from_url: Callable[[str], tuple[bytes, str]]


def build_import_parsers(*, q1, qall, normalize_platform_codes):
    max_logo_bytes = 5 * 1024 * 1024
    allowed_logo_mime = {"image/jpeg", "image/png", "image/webp"}

    game_import_headers = ["Товар", "Платформа"]
    game_import_header_map = {
        "Товар": "title",
        "товар": "title",
        "Игра": "title",
        "игра": "title",
        "Платформа": "platform_codes",
        "title": "title",
        "platform_codes": "platform_codes",
    }
    account_import_header_map = {
        "Аккаунт": "account",
        "аккаунт": "account",
        "Login": "account",
        "Логин": "account",
        "логин": "account",
        "Пароль": "password",
        "пароль": "password",
        "Password": "password",
        "Товар": "game",
        "товар": "game",
        "Игра": "game",
        "игра": "game",
        "Game": "game",
    }
    slot_import_header_map = {
        "Аккаунт": "account",
        "аккаунт": "account",
        "Товар": "game",
        "товар": "game",
        "Игра": "game",
        "игра": "game",
        "Статус": "status",
        "статус": "status",
        "Пользователь": "customer",
        "пользователь": "customer",
        "Источник": "source",
        "источник": "source",
        "Дата": "date",
        "дата": "date",
        "Слот": "slot",
        "слот": "slot",
    }
    slot_file_to_type = {
        "п4": ("activate_ps4", 1),
        "п5": ("activate_ps5", 1),
        "ps4(1)": ("play_ps4", 1),
        "ps4(2)": ("play_ps4", 2),
        "ps5(1)": ("play_ps5", 1),
        "ps5(2)": ("play_ps5", 2),
    }
    ru_months = {
        "январь": 1,
        "февраль": 2,
        "март": 3,
        "апрель": 4,
        "май": 5,
        "июнь": 6,
        "июль": 7,
        "август": 8,
        "сентябрь": 9,
        "октябрь": 10,
        "ноябрь": 11,
        "декабрь": 12,
    }

    def parse_import_platforms(value: str) -> list[str]:
        if not value:
            return []
        raw = str(value).strip()
        if raw in {"-", "—"}:
            return []
        parts = []
        for chunk in raw.replace(";", ",").split(","):
            val = chunk.strip().lower()
            if val:
                parts.append(val)
        return normalize_platform_codes(parts)

    # Проверяет, что игровой товар существует в каталоге, и возвращает product_id.
    def resolve_game_product_id_by_title(conn, game_title: str):
        if not game_title:
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
            (game_title,),
        )
        return int(row[0]) if row and row[0] is not None else None

    def detect_logo_mime_from_bytes(data: bytes) -> str:
        if not data:
            return ""
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        return ""

    def fetch_logo_from_url(url: str) -> tuple[bytes, str]:
        if not url:
            raise ValueError("logo url is empty")
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "gamesales-import"})
        try:
            with urllib.request.urlopen(req, timeout=10, context=context) as resp:
                content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                data = resp.read(max_logo_bytes + 1)
        except urllib.error.URLError as exc:
            raise ValueError(f"logo download failed: {exc}") from exc
        if len(data) > max_logo_bytes:
            raise ValueError("logo too large")
        mime = content_type if content_type in allowed_logo_mime else ""
        if not mime:
            mime = detect_logo_mime_from_bytes(data)
        if mime not in allowed_logo_mime:
            raise ValueError("logo type not allowed")
        return data, mime

    def validate_game_import_rows(conn, rows: list[dict], progress_cb=None, check_logo=False):
        errors = []
        warnings = []
        platform_rows = qall(conn, "SELECT code FROM app.platforms")
        platforms = {str(r[0]).strip().lower() for r in platform_rows}
        for idx, row in enumerate(rows, start=2):
            report_row = idx - 1
            title = (row.get("title") or "").strip()
            platform_raw = row.get("platform_codes") or ""
            platform_codes = parse_import_platforms(platform_raw)
            if not title:
                errors.append({"row": report_row, "field": "Товар", "value": title, "message": "Название обязательно"})
            if not platform_codes:
                warnings.append({"row": report_row, "field": "Платформа", "value": str(platform_raw).strip(), "message": "Платформы не указаны — строка будет пропущена"})
            for code in platform_codes:
                if code not in platforms:
                    errors.append({"row": report_row, "field": "Платформа", "value": code, "message": f"Неизвестная платформа: {code}"})
            if progress_cb:
                progress_cb(idx - 1)
        return errors, warnings

    def read_games_from_excel(content: bytes) -> list[dict]:
        wb = load_workbook(BytesIO(content), data_only=True)
        ws = wb.active
        headers = []
        for cell in ws[1]:
            if cell.value is None:
                headers.append("")
            else:
                raw = str(cell.value).strip()
                headers.append(game_import_header_map.get(raw, raw))
        data = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(row):
                continue
            item = {}
            for idx, key in enumerate(headers):
                if not key:
                    continue
                item[key] = row[idx] if idx < len(row) else None
            data.append(item)
        return data

    def read_accounts_from_excel(content: bytes) -> list[dict]:
        wb = load_workbook(BytesIO(content), data_only=True)
        ws = wb.active
        headers = []
        for cell in ws[1]:
            if cell.value is None:
                headers.append("")
            else:
                raw = str(cell.value).strip()
                headers.append(account_import_header_map.get(raw, raw))
        data = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(row):
                continue
            item = {}
            for idx, key in enumerate(headers):
                if not key:
                    continue
                item[key] = row[idx] if idx < len(row) else None
            data.append(item)
        return data

    def read_slots_from_excel(content: bytes) -> list[dict]:
        wb = load_workbook(BytesIO(content), data_only=True)
        ws = wb.active
        headers = []
        for cell in ws[1]:
            if cell.value is None:
                headers.append("")
            else:
                raw = str(cell.value).strip()
                headers.append(slot_import_header_map.get(raw, raw))
        data = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(row):
                continue
            item = {}
            for idx, key in enumerate(headers):
                if not key:
                    continue
                item[key] = row[idx] if idx < len(row) else None
            data.append(item)
        return data

    def clean_slots_excel(content: bytes) -> bytes:
        wb = load_workbook(BytesIO(content))
        ws = wb.active
        status_col = None
        for idx, cell in enumerate(ws[1], start=1):
            if cell.value is None:
                continue
            header = str(cell.value).strip()
            if header.lower() == "статус":
                status_col = idx
                break
        if not status_col:
            raise HTTPException(400, 'Колонка "Статус" не найдена')
        for row_idx in range(ws.max_row, 1, -1):
            raw = ws.cell(row=row_idx, column=status_col).value
            value = "" if raw is None else str(raw).strip()
            if not value or value.lower() == "свободен":
                ws.delete_rows(row_idx, 1)
        out = BytesIO()
        wb.save(out)
        return out.getvalue()

    def split_account(value: str):
        if not value:
            return None, None
        raw = str(value).strip()
        if not raw or "@" not in raw:
            return None, None
        login, domain = raw.split("@", 1)
        login = login.strip()
        domain = domain.strip()
        if not login or not domain:
            return None, None
        return login, domain

    def validate_account_import_rows(conn, rows: list[dict], progress_cb=None):
        errors = []
        warnings = []
        for idx, row in enumerate(rows, start=2):
            report_row = idx - 1
            account_val = (row.get("account") or "").strip()
            game_title = (row.get("game") or "").strip()
            login, domain = split_account(account_val)
            if not account_val or not login or not domain:
                warnings.append({"row": report_row, "field": "Аккаунт", "value": account_val, "message": "Нужно значение в формате login@domain — строка будет пропущена"})
            if not game_title:
                warnings.append({"row": report_row, "field": "Товар", "value": game_title, "message": "Товар не указан — строка будет пропущена"})
            else:
                if resolve_game_product_id_by_title(conn, game_title) is None:
                    warnings.append({"row": report_row, "field": "Товар", "value": game_title, "message": "Не найден в списке товаров — строка будет пропущена"})
            if progress_cb:
                progress_cb(idx - 1)
        return errors, warnings

    def normalize_slot_file_value(value: str) -> str:
        return str(value or "").strip().lower()

    def normalize_cell_text(value) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def normalize_slot_date(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        raw = str(value).strip()
        if not raw:
            return None
        m = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", raw)
        if m:
            d = int(m.group(1))
            mo = int(m.group(2))
            y = int(m.group(3))
            if y < 100:
                y += 2000
            try:
                return date(y, mo, d).isoformat()
            except ValueError:
                return None
        m = re.match(r"^\s*([A-Za-zА-Яа-яёЁ]+)\s+(\d{2,4})\s*$", raw)
        if m:
            month_name = m.group(1).strip().lower()
            year = int(m.group(2))
            if year < 100:
                year += 2000
            month = ru_months.get(month_name)
            if month:
                try:
                    return date(year, month, 1).isoformat()
                except ValueError:
                    return None
        return None

    def normalize_slot_date_to_dt(value):
        normalized = normalize_slot_date(value)
        if not normalized:
            return None
        try:
            return datetime.fromisoformat(normalized).replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def resolve_source_id(conn, source_val: str):
        if not source_val:
            return None
        parts = [p for p in str(source_val).strip().split() if p]
        row = None
        if len(parts) >= 2:
            name_part = parts[0]
            code_part = parts[-1]
            row = q1(
                conn,
                """
                SELECT source_id
                FROM app.sources
                WHERE lower(name) = lower(%s) AND lower(code) = lower(%s)
                """,
                (name_part, code_part),
            )
            if not row:
                row = q1(
                    conn,
                    """
                    SELECT source_id
                    FROM app.sources
                    WHERE lower(name) = lower(%s) AND lower(code) = lower(%s)
                    """,
                    (code_part, name_part),
                )
        if not row:
            row = q1(
                conn,
                """
                SELECT source_id
                FROM app.sources
                WHERE lower(code) = lower(%s) OR lower(name) = lower(%s)
                """,
                (source_val, source_val),
            )
        return int(row[0]) if row else None

    def validate_slot_import_rows(conn, rows: list[dict], progress_cb=None):
        errors = []
        warnings = []
        total = 0

        slot_rows = qall(conn, "SELECT code FROM app.slot_types")
        slot_types = {str(r[0]).strip().lower() for r in slot_rows}

        for idx, row in enumerate(rows, start=2):
            report_row = idx - 1
            if progress_cb:
                progress_cb(idx - 1)
            status_raw = row.get("status")
            status = "" if status_raw is None else str(status_raw).strip().lower()
            if not status or status == "свободен":
                continue

            total += 1
            account_val = normalize_cell_text(row.get("account"))
            slot_val = normalize_cell_text(row.get("slot"))
            game_title = normalize_cell_text(row.get("game"))
            customer = normalize_cell_text(row.get("customer"))
            source_val = normalize_cell_text(row.get("source"))
            date_val = row.get("date")

            if not account_val:
                errors.append({"row": report_row, "field": "Аккаунт", "value": account_val, "message": "Аккаунт обязателен"})
            else:
                login, domain = split_account(account_val)
                if not login or not domain:
                    warnings.append({"row": report_row, "field": "Аккаунт", "value": account_val, "message": "Нужно значение в формате login@domain"})
                else:
                    row_acc = q1(
                        conn,
                        """
                        SELECT 1
                        FROM app.accounts a
                        JOIN app.domains d ON d.domain_id = a.domain_id
                        WHERE lower(a.login_name) = lower(%s) AND lower(d.name) = lower(%s)
                        """,
                        (login, domain),
                    )
                    if not row_acc:
                        warnings.append({"row": report_row, "field": "Аккаунт", "value": account_val, "message": "Аккаунт не найден"})

            if not slot_val:
                errors.append({"row": report_row, "field": "Слот", "value": slot_val, "message": "Слот обязателен"})
            else:
                normalized_slot = normalize_slot_file_value(slot_val)
                slot_mapping = slot_file_to_type.get(normalized_slot)
                if not slot_mapping:
                    warnings.append({"row": report_row, "field": "Слот", "value": slot_val, "message": "Неизвестный слот"})
                elif slot_mapping[0].lower() not in slot_types:
                    warnings.append({"row": report_row, "field": "Слот", "value": slot_val, "message": "Слот не найден в БД"})

            if game_title:
                if resolve_game_product_id_by_title(conn, game_title) is None:
                    warnings.append({"row": report_row, "field": "Товар", "value": game_title, "message": "Товар не найден"})
            else:
                warnings.append({"row": report_row, "field": "Товар", "value": game_title, "message": "Товар не указан"})

            if not customer:
                warnings.append({"row": report_row, "field": "Пользователь", "value": customer, "message": "Пользователь не указан"})

            if source_val:
                parts = [p for p in str(source_val).strip().split() if p]
                row_source = None
                if len(parts) >= 2:
                    name_part = parts[0]
                    code_part = parts[-1]
                    row_source = q1(
                        conn,
                        """
                        SELECT 1
                        FROM app.sources
                        WHERE lower(name) = lower(%s) AND lower(code) = lower(%s)
                        """,
                        (name_part, code_part),
                    )
                    if not row_source:
                        row_source = q1(
                            conn,
                            """
                            SELECT 1
                            FROM app.sources
                            WHERE lower(name) = lower(%s) AND lower(code) = lower(%s)
                            """,
                            (code_part, name_part),
                        )
                if not row_source:
                    row_source = q1(
                        conn,
                        """
                        SELECT 1
                        FROM app.sources
                        WHERE lower(code) = lower(%s) OR lower(name) = lower(%s)
                        """,
                        (source_val, source_val),
                    )
                if not row_source:
                    warnings.append({"row": report_row, "field": "Источник", "value": source_val, "message": "Источник не найден"})

            if date_val not in (None, ""):
                normalized_date = normalize_slot_date(date_val)
                original_date = normalize_cell_text(date_val)
                if normalized_date:
                    if normalized_date != original_date:
                        warnings.append({"row": report_row, "field": "Дата", "value": original_date, "message": f"Будет сохранено как {normalized_date}"})
                else:
                    warnings.append({"row": report_row, "field": "Дата", "value": original_date, "message": "Не удалось распознать дату"})

            if progress_cb:
                progress_cb(idx - 1)

        return errors, warnings, total

    return ImportParsers(
        GAME_IMPORT_HEADERS=game_import_headers,
        parse_import_platforms=parse_import_platforms,
        validate_game_import_rows=validate_game_import_rows,
        read_games_from_excel=read_games_from_excel,
        read_accounts_from_excel=read_accounts_from_excel,
        read_slots_from_excel=read_slots_from_excel,
        clean_slots_excel=clean_slots_excel,
        split_account=split_account,
        validate_account_import_rows=validate_account_import_rows,
        SLOT_FILE_TO_TYPE=slot_file_to_type,
        normalize_slot_file_value=normalize_slot_file_value,
        normalize_cell_text=normalize_cell_text,
        normalize_slot_date=normalize_slot_date,
        normalize_slot_date_to_dt=normalize_slot_date_to_dt,
        resolve_source_id=resolve_source_id,
        validate_slot_import_rows=validate_slot_import_rows,
        detect_logo_mime_from_bytes=detect_logo_mime_from_bytes,
        fetch_logo_from_url=fetch_logo_from_url,
    )
