"""TEC-D08 — attendance_day source of truth."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

from app.core.runtime import use_memory_fallback
from app.repositories.attendance_day_repository import attendance_day_repository
from app.repositories.oracle import OracleRepositoryError

VALID_ATTENDANCE_STATUSES = {
    "no_record",
    "present",
    "late",
    "absent",
    "justified",
    "leave",
    "unpaid_leave",
    "permission",
    "strike",
    "holiday",
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
        biometric_import_id: int | None = None,
    ) -> dict[str, Any]:
        self._validate(status, late_minutes)
        late_minutes = late_minutes if status == "late" else 0
        parsed_date = self._parse_date(attendance_date)
        try:
            return attendance_day_repository.upsert(
                staff_member_id=staff_member_id,
                biometric_import_id=biometric_import_id,
                attendance_date=parsed_date,
                status=status,
                late_minutes=late_minutes,
                justification_id=justification_id,
            )
        except OracleRepositoryError as exc:
            use_memory_fallback("attendance upsert", exc)

        key = self._key(staff_member_id, parsed_date.isoformat(), biometric_import_id)
        old = self._days.get(key)
        row_id = old["id"] if old else self._next_id()
        row = {
            "id": row_id,
            "staff_member_id": staff_member_id,
            "biometric_import_id": biometric_import_id,
            "attendance_date": parsed_date.isoformat(),
            "status": status,
            "late_minutes": late_minutes,
            "justification_id": justification_id,
            "status_before_justification": (
                old.get("status_before_justification", old["status"])
                if old and justification_id is not None
                else None
            ),
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
        status: str,
    ) -> int:
        self._validate(status, 0)
        try:
            return attendance_day_repository.apply_justification(
                justification_id=justification_id,
                staff_member_id=staff_member_id,
                start_date=start_date,
                end_date=end_date,
                status=status,
            )
        except OracleRepositoryError as exc:
            use_memory_fallback("justification attendance apply", exc)

        changed = []
        for row in self._days.values():
            attendance_date = date.fromisoformat(str(row["attendance_date"])[:10])
            if (
                row["staff_member_id"] == staff_member_id
                and start_date <= attendance_date <= end_date
                and row["status"] == "absent"
                and row.get("justification_id") is None
            ):
                row["status_before_justification"] = "absent"
                row["status"] = status
                row["late_minutes"] = 0
                row["justification_id"] = justification_id
                changed.append(deepcopy(row))
        return len(changed)

    def bulk_upsert_days(self, rows: list[dict[str, Any]]) -> None:
        payload = []
        for row in rows:
            self._validate(row["status"], row.get("late_minutes", 0))
            normalized_late_minutes = (
                row.get("late_minutes", 0) if row["status"] == "late" else 0
            )
            payload.append(
                {
                    **row,
                    "attendance_date": self._parse_date(row["attendance_date"]),
                    "late_minutes": normalized_late_minutes,
                    "justification_id": row.get("justification_id"),
                }
            )
        try:
            attendance_day_repository.bulk_upsert(payload)
            return
        except OracleRepositoryError as exc:
            use_memory_fallback("attendance bulk upsert", exc)

        for row in rows:
            self.upsert_day(
                staff_member_id=row["staff_member_id"],
                attendance_date=row["attendance_date"],
                status=row["status"],
                late_minutes=(
                    row.get("late_minutes", 0) if row["status"] == "late" else 0
                ),
                justification_id=row.get("justification_id"),
                biometric_import_id=row.get("biometric_import_id"),
            )

    def cancel_justification(self, justification_id: int) -> list[dict[str, Any]]:
        try:
            return attendance_day_repository.clear_justification(justification_id)
        except OracleRepositoryError as exc:
            use_memory_fallback("justification attendance rollback", exc)

        changed = []
        for row in self._days.values():
            if row.get("justification_id") == justification_id:
                row["status"] = row.get("status_before_justification") or "absent"
                row["late_minutes"] = 0
                row["justification_id"] = None
                row["status_before_justification"] = None
                changed.append(deepcopy(row))
        return changed

    def cancel_import(self, import_id: int) -> None:
        self._days = {
            key: row
            for key, row in self._days.items()
            if row.get("biometric_import_id") != import_id
        }

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
                return attendance_day_repository.list_by_import(
                    import_id, month=month, year=year
                )
            return attendance_day_repository.list_month(
                month=month, year=year, staff_member_id=staff_member_id
            )
        except OracleRepositoryError as exc:
            use_memory_fallback("attendance list", exc)

        prefix = f"{year:04d}-{month:02d}"
        out = []
        for row in self._days.values():
            if not str(row["attendance_date"]).startswith(prefix):
                continue
            if import_id and row.get("biometric_import_id") != import_id:
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

    def _key(
        self,
        staff_member_id: int,
        attendance_date: str,
        biometric_import_id: int | None = None,
    ) -> str:
        return f"{staff_member_id}:{attendance_date}:{biometric_import_id or 0}"


attendance_service = AttendanceService()
