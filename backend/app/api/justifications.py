"""TEC-D07 — justification routes."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import require_token
from app.core.config import settings
from app.services.audit_service import audit_service
from app.services.justification_service import (
    JustificationNotFoundError,
    JustificationValidationError,
    justification_service,
)
from app.services.support_file_service import (
    SupportFileNotFoundError,
    SupportFileValidationError,
    support_file_service,
)

router = APIRouter(prefix="/api/v1/justifications", tags=["justifications"])


@router.get("")
def list_justifications(
    staff_member_id: int | None = None,
    status: str | None = None,
    session: dict = Depends(require_token),
):
    return justification_service.list(staff_member_id, status)


class JustificationUpdate(BaseModel):
    staff_member_id: int
    start_date: str
    end_date: str
    norm_code: str
    with_pay: str = Field(default="Y", pattern=r"^[YN]$")
    reason: str | None = None
    support_file_path: str | None = None


@router.post("", status_code=201)
async def create_justification(
    staff_member_id: int = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    norm_code: str = Form(...),
    with_pay: str = Form("Y"),
    reason: str | None = Form(None),
    support_file: UploadFile | None = File(None),
    session: dict = Depends(require_token),
):
    support_file_path = None
    if support_file:
        try:
            content = await support_file.read(settings.support_file_max_bytes + 1)
            support_file_path = support_file_service.save(
                support_file.filename or "", support_file.content_type, content
            )
        except SupportFileValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            await support_file.close()
    data = {
        "staff_member_id": staff_member_id,
        "start_date": start_date,
        "end_date": end_date,
        "norm_code": norm_code,
        "with_pay": with_pay,
        "reason": reason,
        "support_file_path": support_file_path,
        "registered_by_id": session["user_id"],
    }
    try:
        item = justification_service.create(data)
    except JustificationValidationError as exc:
        support_file_service.delete(support_file_path)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        support_file_service.delete(support_file_path)
        raise
    audit_service.record(
        user_id=session["user_id"],
        entity_name="justification",
        entity_id=item["id"],
        action_name="create",
        new_value=item,
    )
    return item


@router.get("/{id}/support")
def download_support_file(id: int, session: dict = Depends(require_token)):
    try:
        item = justification_service.get(id)
    except JustificationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Justification not found") from exc

    stored_path = item.get("support_file_path")
    if not stored_path:
        raise HTTPException(status_code=404, detail="Support file not found")
    try:
        file_path = support_file_service.resolve(stored_path)
    except SupportFileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Support file not found") from exc
    return FileResponse(
        file_path,
        filename=support_file_service.original_name(stored_path),
    )


@router.put("/{id}")
def update_justification(
    id: int, body: JustificationUpdate, session: dict = Depends(require_token)
):
    data = body.model_dump()
    data["registered_by_id"] = session["user_id"]
    try:
        change = justification_service.update(id, data)
    except JustificationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Justification not found") from exc
    except JustificationValidationError as exc:
        raise HTTPException(status_code=400, detail="Invalid justification") from exc
    audit_service.record(
        user_id=session["user_id"],
        entity_name="justification",
        entity_id=id,
        action_name="update",
        old_value=change["old"],
        new_value=change["new"],
    )
    return change["new"]


class CancelBody(BaseModel):
    reason: str


@router.post("/{id}/cancellation")
def cancel_justification(
    id: int, body: CancelBody, session: dict = Depends(require_token)
):
    reason = body.reason.strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Cancellation reason is required")
    try:
        item = justification_service.cancel(id, reason)
    except JustificationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Justification not found") from exc
    audit_service.record(
        user_id=session["user_id"],
        entity_name="justification",
        entity_id=id,
        action_name="cancel",
        new_value={"reason": reason},
    )
    return item
