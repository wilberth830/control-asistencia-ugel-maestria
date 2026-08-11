"""TEC-D09 + TEC-D12 — annex reports using institution header + attendance_day."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.repositories.institution_repository import institution_repository
from app.repositories.oracle import OracleRepositoryError
from app.services.attendance_service import attendance_service
from app.services.staff_member_service import (
    StaffMemberNotFoundError,
    staff_member_service,
)

DEMO_INSTITUTION = {
    "ugel": "UGEL Demo",
    "school_name": "IE Demo CHIQUISTRUKIS",
    "modular_code": "1234567",
    "education_level": "Secundaria",
    "shift_name": "Mañana",
}


class ReportService:
    def annex_03(
        self, month: int, year: int, institution: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        inst = institution or self._institution()
        attendance_rows = attendance_service.list_month(month, year)
        rows_by_staff: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in attendance_rows:
            rows_by_staff[row["staff_member_id"]].append(row)

        rows = []
        for staff_member_id, days in sorted(rows_by_staff.items()):
            staff_member = self._staff_member(staff_member_id)
            rows.append(
                {
                    "staff_member_id": staff_member_id,
                    "dni": staff_member.get("dni"),
                    "full_name": self._full_name(staff_member),
                    "days": sorted(days, key=lambda day: day["attendance_date"]),
                }
            )

        return {
            "institution": inst,
            "period": {"month": month, "year": year},
            "source": "attendance_day",
            "rows": rows,
        }

    def annex_04(self, month: int, year: int) -> dict[str, Any]:
        attendance_rows = attendance_service.list_month(month, year)
        totals = Counter(row["status"] for row in attendance_rows)
        staff_member_ids = {row["staff_member_id"] for row in attendance_rows}
        return {
            "institution": self._institution(),
            "period": {"month": month, "year": year},
            "source": "attendance_day",
            "staff_count": len(staff_member_ids),
            "totals": {
                "present": totals["present"],
                "late": totals["late"],
                "absent": totals["absent"],
                "justified": totals["justified"],
                "leave": totals["leave"],
                "permission": totals["permission"],
            },
        }

    def _staff_member(self, staff_member_id: int) -> dict[str, Any]:
        try:
            return staff_member_service.get(staff_member_id)
        except StaffMemberNotFoundError:
            return {
                "dni": None,
                "last_names": "Unknown",
                "first_names": "Staff",
            }

    def _full_name(self, staff_member: dict[str, Any]) -> str:
        return f"{staff_member['last_names']}, {staff_member['first_names']}"

    def _institution(self) -> dict[str, Any]:
        try:
            return institution_repository.get_active() or DEMO_INSTITUTION
        except OracleRepositoryError:
            return DEMO_INSTITUTION


report_service = ReportService()
