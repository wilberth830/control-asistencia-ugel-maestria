"""TEC-D09 + TEC-D12 — annex reports using institution header + attendance_day."""

from __future__ import annotations

from collections import Counter, defaultdict
from calendar import monthrange
from datetime import date
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

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

MONTH_NAMES = (
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SETIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
)


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

    def monthly_workbook(self, month: int, year: int) -> BytesIO:
        if month < 1 or month > 12:
            raise ValueError("invalid_month")
        institution = self._institution()
        staff_rows = self._staff_rows(month, year)
        workbook = Workbook()
        attendance_sheet = workbook.active
        attendance_sheet.title = "ASISTENCIA"
        consolidated_sheet = workbook.create_sheet("REPORTE CONSOLIDADO")
        self._write_attendance_sheet(
            attendance_sheet, institution, staff_rows, month, year
        )
        self._write_consolidated_sheet(
            consolidated_sheet, institution, staff_rows, month, year
        )
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return output

    def _staff_rows(self, month: int, year: int) -> list[dict[str, Any]]:
        attendance_rows = attendance_service.list_month(month, year)
        days_by_staff: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
        for item in attendance_rows:
            days_by_staff[item["staff_member_id"]][item["attendance_date"]] = item
        rows = []
        for staff in staff_member_service.list(is_active="Y"):
            rows.append({**staff, "days": days_by_staff.get(staff["id"], {})})
        return rows

    def _write_common_header(
        self, sheet: Any, institution: dict[str, Any], month: int, year: int, title: str, end_column: int
    ) -> None:
        blue = PatternFill("solid", fgColor="00A1D6")
        thin = Side(style="thin", color="000000")
        sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=end_column)
        sheet.cell(1, 1, "ANEXO " + ("03" if "DETALLADO" in title else "04"))
        sheet.cell(1, 1).font = Font(bold=True, size=12)
        sheet.cell(1, 1).alignment = Alignment(horizontal="center")
        sheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=end_column)
        title_cell = sheet.cell(2, 1, title)
        title_cell.fill = blue
        title_cell.font = Font(bold=True, size=14)
        title_cell.alignment = Alignment(horizontal="center")
        for row, label, value in [
            (3, "UGEL:", institution.get("ugel", "")),
            (4, "INSTITUCIÓN EDUCATIVA:", institution.get("school_name", "")),
            (5, "NIVEL EDUCATIVO Y MODALIDAD:", institution.get("education_level", "")),
            (6, "CÓDIGO MODULAR:", institution.get("modular_code", "")),
        ]:
            sheet.cell(row, 1, label).font = Font(bold=True)
            sheet.merge_cells(start_row=row, start_column=2, end_row=row, end_column=min(7, end_column))
            sheet.cell(row, 2, value)
        sheet.cell(3, max(8, end_column - 8), "MES:").font = Font(bold=True)
        sheet.cell(3, max(8, end_column - 7), MONTH_NAMES[month - 1])
        sheet.cell(3, max(8, end_column - 4), "AÑO:").font = Font(bold=True)
        sheet.cell(3, max(8, end_column - 3), year)
        sheet.cell(3, max(8, end_column - 1), "TURNO:").font = Font(bold=True)
        sheet.cell(3, end_column, institution.get("shift_name", ""))
        for row in sheet.iter_rows(min_row=1, max_row=6, min_col=1, max_col=end_column):
            for cell in row:
                cell.border = Border(bottom=thin)
                cell.alignment = Alignment(vertical="center")

    def _write_attendance_sheet(
        self, sheet: Any, institution: dict[str, Any], staff_rows: list[dict[str, Any]], month: int, year: int
    ) -> None:
        days = monthrange(year, month)[1]
        first_day_column = 7
        end_column = first_day_column + days - 1
        self._write_common_header(
            sheet, institution, month, year, "FORMATO 01: REPORTE DE ASISTENCIA DETALLADO", end_column
        )
        blue = PatternFill("solid", fgColor="B7DEE8")
        thin = Side(style="thin", color="000000")
        headers = ["N°", "DNI", "APELLIDOS Y NOMBRES", "CARGO", "CONDICIÓN\nLABORAL", "JORNADA\nLABORAL"]
        for column, header in enumerate(headers, start=1):
            sheet.merge_cells(start_row=8, start_column=column, end_row=9, end_column=column)
            cell = sheet.cell(8, column, header)
            cell.fill = blue
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        sheet.merge_cells(start_row=8, start_column=first_day_column, end_row=8, end_column=end_column)
        calendar_cell = sheet.cell(8, first_day_column, "DÍAS CALENDARIO")
        calendar_cell.fill = blue
        calendar_cell.font = Font(bold=True)
        calendar_cell.alignment = Alignment(horizontal="center")
        weekday_labels = ["lu.", "ma.", "mi.", "ju.", "vi.", "sá.", "do."]
        for day in range(1, days + 1):
            column = first_day_column + day - 1
            cell = sheet.cell(9, column, day)
            cell.fill = blue
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")
            sheet.cell(10, column, weekday_labels[date(year, month, day).weekday()]).alignment = Alignment(horizontal="center")
        for index, staff in enumerate(staff_rows, start=1):
            row = 10 + index
            values = [index, staff["dni"], self._full_name(staff), staff["job_title"], staff.get("employment_status") or "", ""]
            for column, value in enumerate(values, start=1):
                sheet.cell(row, column, value)
            for day in range(1, days + 1):
                attendance = staff["days"].get(date(year, month, day).isoformat())
                status = attendance.get("status") if attendance else ""
                code = {"present": "A", "late": "T", "absent": "F", "justified": "J", "leave": "L", "permission": "P"}.get(status, "")
                sheet.cell(row, first_day_column + day - 1, code).alignment = Alignment(horizontal="center")
        self._format_table(sheet, 8, 10 + max(1, len(staff_rows)), end_column, [5, 12, 34, 16, 16, 16])

    def _write_consolidated_sheet(
        self, sheet: Any, institution: dict[str, Any], staff_rows: list[dict[str, Any]], month: int, year: int
    ) -> None:
        headers = ["N°", "DNI", "APELLIDOS Y NOMBRES", "CARGO", "CONDICIÓN\nLABORAL", "JORNADA\nLABORAL", "INASISTENCIAS\nJUSTIFICADAS\nDÍAS", "LICENCIAS\nCON GOCE", "LICENCIAS\nSIN GOCE", "LICENCIAS\nDU", "FALTAS\nDÍAS", "TARDANZAS\nMINUTOS (*)", "PERMISOS SG\nHORAS (*)", "PERMISOS SG\nMINUTOS (*)", "HUELGA PARO\nDÍAS", "OBSERVACIONES"]
        end_column = len(headers)
        self._write_common_header(
            sheet, institution, month, year,
            "FORMATO 02: REPORTE CONSOLIDADO DE INASISTENCIAS, TARDANZAS Y PERMISOS SIN GOCE DE REMUNERACIÓN", end_column,
        )
        blue = PatternFill("solid", fgColor="B7DEE8")
        for column, header in enumerate(headers, start=1):
            cell = sheet.cell(8, column, header)
            cell.fill = blue
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for index, staff in enumerate(staff_rows, start=1):
            status_counts = Counter(item["status"] for item in staff["days"].values())
            late_minutes = sum(item.get("late_minutes", 0) for item in staff["days"].values() if item["status"] == "late")
            values = [index, staff["dni"], self._full_name(staff), staff["job_title"], staff.get("employment_status") or "", "", status_counts["justified"], status_counts["leave"], 0, 0, status_counts["absent"], late_minutes, 0, 0, 0, ""]
            for column, value in enumerate(values, start=1):
                cell = sheet.cell(8 + index, column, value)
                if column >= 7 and column <= 15:
                    cell.alignment = Alignment(horizontal="center")
        self._format_table(sheet, 8, 8 + max(1, len(staff_rows)), end_column, [5, 12, 34, 16, 16, 16, 15, 14, 14, 12, 12, 14, 14, 16, 14, 28])

    def _format_table(self, sheet: Any, start_row: int, end_row: int, end_column: int, widths: list[int]) -> None:
        thin = Side(style="thin", color="000000")
        for row in sheet.iter_rows(min_row=start_row, max_row=end_row, min_col=1, max_col=end_column):
            for cell in row:
                cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
                cell.alignment = cell.alignment.copy(vertical="center", wrap_text=True)
        for column, width in enumerate(widths, start=1):
            sheet.column_dimensions[chr(64 + column)].width = width
        sheet.freeze_panes = "G10"
        sheet.sheet_view.showGridLines = False
        sheet.row_dimensions[8].height = 45

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
