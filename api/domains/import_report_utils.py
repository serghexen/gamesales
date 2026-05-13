from io import BytesIO

from openpyxl import Workbook


def build_import_report_xlsx(errors, warnings) -> bytes:
    wb = Workbook()
    ws_err = wb.active
    ws_err.title = "Ошибки"
    ws_err.append(["Лист", "Строка", "Почта", "Поле", "Значение", "Сообщение"])

    def _get(issue, key):
        if isinstance(issue, dict):
            return issue.get(key)
        return getattr(issue, key, None)

    for issue in errors or []:
        ws_err.append([
            _get(issue, "sheet"),
            _get(issue, "row"),
            _get(issue, "account"),
            _get(issue, "field"),
            _get(issue, "value"),
            _get(issue, "message"),
        ])

    ws_warn = wb.create_sheet("Предупреждения")
    ws_warn.append(["Лист", "Строка", "Почта", "Поле", "Значение", "Сообщение"])
    for issue in warnings or []:
        ws_warn.append([
            _get(issue, "sheet"),
            _get(issue, "row"),
            _get(issue, "account"),
            _get(issue, "field"),
            _get(issue, "value"),
            _get(issue, "message"),
        ])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
