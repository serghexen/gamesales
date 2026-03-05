from io import BytesIO
import threading
import uuid

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from openpyxl import Workbook


def mount_products_import_routes(
    app,
    *,
    DB_DSN,
    psycopg,
    read_games_from_excel,
    validate_game_import_rows,
    set_import_progress,
    get_import_progress,
    run_games_import_job,
    build_import_report_xlsx,
    require_role,
    UserOut,
    ImportReportIn,
    GAME_IMPORT_HEADERS,
):
    @app.get("/products/import/template")
    def products_import_template(user: UserOut = Depends(require_role("admin", "owner"))):
        wb = Workbook()
        ws = wb.active
        ws.title = "products"
        ws.append(GAME_IMPORT_HEADERS)
        for col in range(1, len(GAME_IMPORT_HEADERS) + 1):
            ws.column_dimensions[chr(64 + col)].width = 20
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        return Response(
            content=buf.read(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=products_import_template.xlsx"},
        )

    @app.get("/products/import/status")
    def products_import_status(job_id: str, user: UserOut = Depends(require_role("admin", "owner"))):
        status = get_import_progress(job_id)
        if not status:
            return {"phase": "idle", "current": 0, "total": 0, "done": True}
        if status.get("owner") and status.get("owner") != user.username:
            raise HTTPException(403, "job not found")
        return {
            "phase": status.get("phase", "idle"),
            "current": int(status.get("current") or 0),
            "total": int(status.get("total") or 0),
            "done": bool(status.get("done")),
            "result": status.get("result"),
        }

    @app.post("/products/import/validate")
    def products_import_validate(file: UploadFile = File(...), user: UserOut = Depends(require_role("admin", "owner"))):
        if not file or not file.filename:
            raise HTTPException(400, "file is required")
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            raise HTTPException(400, "Only .xlsx/.xls are supported")
        content = file.file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(400, "File too large. Max 5MB")
        with psycopg.connect(DB_DSN) as conn:
            rows = read_games_from_excel(content)
            errors, warnings = validate_game_import_rows(conn, rows, progress_cb=None, check_logo=False)
        return {"ok": len(errors) == 0, "total": len(rows), "errors": errors, "warnings": warnings}

    @app.post("/products/import")
    def products_import(file: UploadFile = File(...), user: UserOut = Depends(require_role("admin", "owner"))):
        if not file or not file.filename:
            raise HTTPException(400, "file is required")
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            raise HTTPException(400, "Only .xlsx/.xls are supported")
        content = file.file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(400, "File too large. Max 5MB")
        job_id = uuid.uuid4().hex
        set_import_progress(job_id, user.username, {"phase": "queued", "current": 0, "total": 0, "done": False})
        thread = threading.Thread(target=run_games_import_job, args=(job_id, content, user.username), daemon=True)
        thread.start()
        return {"ok": True, "job_id": job_id}

    @app.post("/products/import/cancel")
    def products_import_cancel(job_id: str, user: UserOut = Depends(require_role("admin", "owner"))):
        status = get_import_progress(job_id)
        if not status:
            return {"ok": True}
        if status.get("owner") and status.get("owner") != user.username:
            raise HTTPException(403, "job not found")
        set_import_progress(
            job_id,
            user.username,
            {
                "phase": "cancelled",
                "current": int(status.get("current") or 0),
                "total": int(status.get("total") or 0),
                "done": True,
                "cancelled": True,
                "result": {"ok": False, "cancelled": True},
            },
        )
        return {"ok": True}

    @app.post("/products/import/report")
    def products_import_report(payload: ImportReportIn, user: UserOut = Depends(require_role("admin", "owner"))):
        content = build_import_report_xlsx(
            [i.dict() for i in payload.errors],
            [i.dict() for i in payload.warnings],
        )
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=products_import_report.xlsx"},
        )
