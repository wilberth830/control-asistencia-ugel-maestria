"""TEC-D05 — wizard import routes."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.deps import require_token
from app.services.audit_service import audit_service
from app.services.biometric_import_service import (
    BiometricImportError,
    biometric_import_service,
)

router = APIRouter(prefix="/api/v1/biometric-imports", tags=["biometric-imports"])


@router.get("")
def list_imports(
    status: str | None = None,
    month: int | None = None,
    year: int | None = None,
    session: dict = Depends(require_token),
):
    return biometric_import_service.list(status=status, month=month, year=year)


@router.post("", status_code=201)
async def create_import(
    file: UploadFile = File(...), session: dict = Depends(require_token)
):
    content = await file.read()
    try:
        imp = biometric_import_service.create_draft_from_csv(
            file.filename or "upload.csv", content, session.get("user_id")
        )
    except BiometricImportError as exc:
        if exc.code == "invalid_file":
            raise HTTPException(
                status_code=400, detail="Invalid biometric file"
            ) from exc
        raise
    audit_service.record(
        user_id=session["user_id"],
        entity_name="biometric_import",
        entity_id=imp["id"],
        action_name="create",
        new_value={"file": file.filename, "bytes": len(content)},
    )
    return imp


@router.get("/{id}")
def get_import(id: int, session: dict = Depends(require_token)):
    imp = biometric_import_service.get(id)
    if not imp:
        raise HTTPException(status_code=404, detail="Biometric import not found")
    return imp


class RowPatch(BaseModel):
    dni: str | None = None
    last_names: str | None = None
    first_names: str | None = None
    action: str


@router.patch("/{id}/rows/{row_id}")
def patch_row(
    id: int, row_id: int, body: RowPatch, session: dict = Depends(require_token)
):
    try:
        row = biometric_import_service.update_row(
            id,
            row_id,
            action=body.action,
            dni=body.dni,
            last_names=body.last_names,
            first_names=body.first_names,
        )
    except BiometricImportError as exc:
        if exc.code in {"not_found", "row_not_found"}:
            raise HTTPException(status_code=404, detail="Import row not found") from exc
        if exc.code == "conflict_not_draft":
            raise HTTPException(status_code=409, detail="Import is not draft") from exc
        if exc.code == "invalid_row_action":
            raise HTTPException(status_code=400, detail="Invalid row action") from exc
        raise
    return row


@router.post("/{id}/confirmation")
def confirm(id: int, session: dict = Depends(require_token)):
    try:
        imp = biometric_import_service.confirm(id)
    except BiometricImportError as exc:
        if exc.code == "not_found":
            raise HTTPException(
                status_code=404, detail="Biometric import not found"
            ) from exc
        if exc.code == "conflict_not_draft":
            raise HTTPException(status_code=409, detail="Import is not draft") from exc
        if exc.code == "unresolved_new_rows":
            raise HTTPException(status_code=400, detail="Unresolved new rows") from exc
        raise
    audit_service.record(
        user_id=session["user_id"],
        entity_name="biometric_import",
        entity_id=id,
        action_name="confirm",
    )
    return imp


class CancelBody(BaseModel):
    reason: str


@router.post("/{id}/cancellation")
def cancel(id: int, body: CancelBody, session: dict = Depends(require_token)):
    try:
        imp = biometric_import_service.cancel(id, body.reason)
    except BiometricImportError as exc:
        if exc.code == "not_found":
            raise HTTPException(
                status_code=404, detail="Biometric import not found"
            ) from exc
        if exc.code == "conflict_not_confirmed":
            raise HTTPException(
                status_code=409, detail="Import is not confirmed"
            ) from exc
        raise
    audit_service.record(
        user_id=session["user_id"],
        entity_name="biometric_import",
        entity_id=id,
        action_name="cancel",
        new_value={"reason": body.reason},
    )
    return imp
