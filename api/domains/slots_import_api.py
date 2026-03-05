from pathlib import Path
import threading
import uuid

from fastapi import Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response


def mount_slots_import_routes(
    app,
    *,
    clean_slots_excel,
    set_import_progress,
    get_import_progress,
    run_slots_validate_job,
    run_slots_import_job,
    build_import_report_xlsx,
    require_role,
    UserOut,
    ImportReportIn,
):
    @app.post("/accounts/slots/clean")
    def accounts_slots_clean(file: UploadFile = File(...), user: UserOut = Depends(require_role("admin", "owner"))):
        if not file or not file.filename:
            raise HTTPException(400, "file is required")
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            raise HTTPException(400, "Only .xlsx/.xls are supported")
        content = file.file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(400, "File too large. Max 10MB")
        cleaned = clean_slots_excel(content)
        base = Path(file.filename or "slots_import").stem
        filename = f"{base}_cleaned.xlsx"
        return Response(
            cleaned,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @app.post("/accounts/slots/validate")
    def accounts_slots_validate(
        file: UploadFile = File(...),
        limit: int | None = Form(None),
        user: UserOut = Depends(require_role("admin", "owner")),
    ):
        if not file or not file.filename:
            raise HTTPException(400, "file is required")
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            raise HTTPException(400, "Only .xlsx/.xls are supported")
        content = file.file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(400, "File too large. Max 10MB")
        job_id = uuid.uuid4().hex
        set_import_progress(job_id, user.username, {"phase": "queued", "current": 0, "total": 0, "done": False})
        thread = threading.Thread(target=run_slots_validate_job, args=(job_id, content, user.username, limit), daemon=True)
        thread.start()
        return {"ok": True, "job_id": job_id}

    @app.get("/accounts/slots/validate/status")
    def accounts_slots_validate_status(job_id: str, user: UserOut = Depends(require_role("admin", "owner"))):
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

    @app.post("/accounts/slots/validate/cancel")
    def accounts_slots_validate_cancel(job_id: str, user: UserOut = Depends(require_role("admin", "owner"))):
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

    @app.post("/accounts/slots/report")
    def accounts_slots_report(payload: ImportReportIn, user: UserOut = Depends(require_role("admin", "owner"))):
        content = build_import_report_xlsx(
            errors=payload.errors or [],
            warnings=payload.warnings or [],
        )
        return Response(
            content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=slots_import_report.xlsx"},
        )

    @app.post("/accounts/slots/import")
    def accounts_slots_import(file: UploadFile = File(...), user: UserOut = Depends(require_role("admin", "owner"))):
        if not file or not file.filename:
            raise HTTPException(400, "file is required")
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            raise HTTPException(400, "Only .xlsx/.xls are supported")
        content = file.file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(400, "File too large. Max 10MB")
        job_id = uuid.uuid4().hex
        set_import_progress(job_id, user.username, {"phase": "queued", "current": 0, "total": 0, "done": False})
        thread = threading.Thread(target=run_slots_import_job, args=(job_id, content, user.username), daemon=True)
        thread.start()
        return {"ok": True, "job_id": job_id}

    @app.get("/accounts/slots/import/status")
    def accounts_slots_import_status(job_id: str, user: UserOut = Depends(require_role("admin", "owner"))):
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

    @app.post("/accounts/slots/import/cancel")
    def accounts_slots_import_cancel(job_id: str, user: UserOut = Depends(require_role("admin", "owner"))):
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
