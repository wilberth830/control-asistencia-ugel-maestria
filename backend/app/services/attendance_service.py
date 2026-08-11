"""TEC-D08 — attendance_day source of truth."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

from app.repositories.attendance_day_repository import attendance_day_repository
from app.repositories.oracle import OracleRepositoryError

VALID_ATTENDANCE_STATUSES = {
    "present",
    "late",
    "absent",
    "justified",
    "leave",
    "permission",
}


class AttendanceValidationError(ValueError):
    """Raised when an attendance_day mutation is invalid."""


class AttendanceService:
    def __init__(self) -> None:
        self._days: dict[str, dict[str, Any]] = {}
        self._seq = 0

    def reset(self) -> None:
        self._days = {}
        self._seq = 0

    def upsert_day(
        self,
        staff_member_id: int,
        attendance_date: str,
        status: str,
        late_minutes: int = 0,
        justification_id: int | None = None,
    ) -> dict[str, Any]:
        self._validate(status, late_minutes)
        parsed_date = self._parse_date(attendance_date)
        try:
            return attendance_day_repository.upsert(
                staff_member_id=staff_member_id,
                attendance_date=parsed_date,
                status=status,
                late_minutes=late_minutes,
                justification_id=justification_id,
            )
        except OracleRepositoryError:
            pass

        key = self._key(staff_member_id, parsed_date.isoformat())
        old = self._days.get(key)
        row_id = old["id"] if old else self._next_id()
        row = {
            "id": row_id,
            "staff_member_id": staff_member_id,
            "attendance_date": parsed_date.isoformat(),
            "status": status,
            "late_minutes": late_minutes,
            "justification_id": justification_id,
        }
        self._days[key] = row
        return deepcopy(row)

    def apply_justification_range(
        self,
        *,
        justification_id: int,
        staff_member_id: int,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        rows = []
        current = start_date
        while current <= end_date:
            rows.append(
                self.upsert_day(
                    staff_member_id=staff_member_id,
                    attendance_date=current.isoformat(),
                    status="justified",
                    late_minutes=0,
                    justification_id=justification_id,
                )
            )
            current = date.fromordinal(current.toordinal() + 1)
        return rows

    def cancel_justification(self, justification_id: int) -> list[dict[str, Any]]:
        try:
            return attendance_day_repository.clear_justification(justification_id)
        except OracleRepositoryError:
            pass

        changed = []
        for row in self._days.values():
            if row.get("justification_id") == justification_id:
                row["status"] = "absent"
                row["late_minutes"] = 0
                row["justification_id"] = None
                changed.append(deepcopy(row))
        return changed

    def list_month(
        self,
        month: int,
        year: int,
        staff_member_id: int | None = None,
        import_id: int | None = None,
    ) -> list[dict[str, Any]]:
        if month < 1 or month > 12:
            raise AttendanceValidationError("invalid_month")
        try:
            if import_id:
                return attendance_day_repository.list_by_import(import_id)
            return attendance_day_repository.list_month(
                month=month, year=year, staff_member_id=staff_member_id
            )
        except OracleRepositoryError:
            pass

        prefix = f"{year:04d}-{month:02d}"
        out = []
        for row in self._days.values():
            if not str(row["attendance_date"]).startswith(prefix):
                continue
            if staff_member_id and row["staff_member_id"] != staff_member_id:
                continue
            out.append(deepcopy(row))
        return sorted(
            out, key=lambda row: (row["attendance_date"], row["staff_member_id"])
        )

    def _validate(self, status: str, late_minutes: int) -> None:
        if status not in VALID_ATTENDANCE_STATUSES:
            raise AttendanceValidationError("invalid_status")
        if late_minutes < 0:
            raise AttendanceValidationError("invalid_late_minutes")

    def _parse_date(self, value: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise AttendanceValidationError("invalid_date") from exc

    def _next_id(self) -> int:
        self._seq += 1
        return self._seq

    def _key(self, staff_member_id: int, attendance_date: str) -> str:
        return f"{staff_member_id}:{attendance_date}"


attendance_service = AttendanceService()
