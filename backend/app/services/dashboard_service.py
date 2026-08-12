"""TEC-D10 — dashboard indicators."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.services.attendance_service import attendance_service
from app.services.biometric_import_service import biometric_import_service
from app.services.staff_member_service import staff_member_service


class DashboardService:
    def indicators(self, month: int, year: int) -> dict[str, Any]:
        attendance_rows = attendance_service.list_month(month, year)
        status_counts = Counter(row["status"] for row in attendance_rows)
        imports = biometric_import_service.list(month=month, year=year)
        recent_imports = sorted(imports, key=lambda row: row["id"], reverse=True)[:5]

        return {
            "total_uploaded_files": len(imports),
            "active_staff_members": len(staff_member_service.list(is_active="Y")),
            "period": {"month": month, "year": year},
            "mark_distribution": {
                "present": status_counts["present"],
                "late": status_counts["late"],
                "absent": status_counts["absent"],
                "justified": status_counts["justified"],
                "leave": status_counts["leave"],
                "unpaid_leave": status_counts["unpaid_leave"],
                "permission": status_counts["permission"],
                "strike": status_counts["strike"],
                "holiday": status_counts["holiday"],
            },
            "recent_imports": [
                {
                    "id": row["id"],
                    "file_name": row["file_name"],
                    "status": row["status"],
                    "period_start": row["period_start"],
                    "period_end": row["period_end"],
                    "total_rows": row["total_rows"],
                }
                for row in recent_imports
            ],
        }


dashboard_service = DashboardService()
