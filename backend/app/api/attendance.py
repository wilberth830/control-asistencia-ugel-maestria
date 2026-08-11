"""TEC-D08 — attendance records."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import require_token
from app.services.attendance_service import (
    AttendanceValidationError,
    attendance_service,
)
from app.services.audit_service import audit_service

router = APIRouter(prefix="/api/v1/attendance-records", tags=["attendance"])


@router.get("")
def list_records(
    month: int,
    year: int,
    staff_member_id: int | None = None,
    import_id: int | None = None,
    session: dict = Depends(require_token),
):
    try:
        return attendance_service.list_month(month, year, staff_member_id, import_id)
    except AttendanceValidationError as exc:
        raise HTTPException(status_code=400, detail="Invalid attendance query") from exc


class DayUpdate(BaseModel):
    staff_member_id: int
    biometric_import_id: int | None = None
    attendance_date: str
    status: str
    late_minutes: int = Field(default=0, ge=0)
    norm_code: str | None = None
    justification_id: int | None = None


@router.put("/days")
def update_day(body: DayUpdate, session: dict = Depends(require_token)):
    try:
        row = attendance_service.upsert_day(
            body.staff_member_id,
            body.attendance_date,
            body.status,
            body.late_minutes,
            body.justification_id,
            body.biometric_import_id,
        )
    except AttendanceValidationError as exc:
        raise HTTPException(status_code=400, detail="Invalid attendance day") from exc
    audit_service.record(
        user_id=session["user_id"],
        entity_name="attendance_day",
        entity_id=row["id"],
        action_name="edit",
        new_value=row,
    )
    return row
