"""TEC-D09 + TEC-D12 — annex reports (formato oficial UGEL).

Solo generación visual del Excel. Endpoints y lógica de datos intactos.
Soporta override de cabecera (institution_override) para editar antes de exportar.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from calendar import monthrange
from datetime import date
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.repositories.biometric_repository import biometric_repository
from app.repositories.institution_repository import institution_repository
from app.repositories.oracle import OracleRepositoryError
from app.services.attendance_service import attendance_service
from app.services.staff_member_service import (
    StaffMemberNotFoundError,
    staff_member_service,
)

DEMO_INSTITUTION = {
    "ugel": "SAN ROMAN",
    "school_name": "IE Demo CHIQUISTRUKIS",
    "modular_code": "1234567",
    "education_level": "Secundaria",
    "shift_name": "Manana",
    "address": "Direccion de IE",
    "department": "PUNO",
    "province": "SAN ROMAN",
    "district": "",
}

MONTH_NAMES = (
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SETIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
)

LEGAL_HEADER = (
    "NORMAS PARA EL REGISTRO Y CONTROL DE ASISTENCIA Y SU APLICACION EN LA "
    "PLANILLA UNICA DE PAGOS DE LOS PROFESORES Y AUXILIARES DE EDUCACION, "
    "EN EL MARCO DE LA LEY DE REFORMA MAGISTERIAL Y SU REGLAMENTO "
    "(R.S.G. N 326-2017-MINEDU)"
)

FILL_TITLE = PatternFill("solid", fgColor="0070C0")
FILL_HEADER = PatternFill("solid", fgColor="BDD7EE")
FILL_ALT = PatternFill("solid", fgColor="F2F2F2")
FONT_BLACK_BOLD = Font(bold=True, size=9, name="Calibri")
FONT_RED_BOLD = Font(bold=True, color="C00000", size=10, name="Calibri")
FONT_TITLE = Font(bold=True, color="FFFFFF", size=12, name="Calibri")
FONT_NORMAL = Font(size=9, name="Calibri")
FONT_SMALL = Font(size=8, name="Calibri")
THIN = Side(style="thin", color="000000")
THIN_BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)


def _safe(value: Any, default: str = "") -> str:
    """Normaliza texto para Excel (evita caracteres problemáticos)."""
    if value is None:
        return default
    text = str(value)
    # Sustituciones seguras para ñ/tildes en entornos que fallan encoding
    replacements = {
        "ñ": "n", "Ñ": "N",
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ü": "u", "Ü": "U",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


class ReportService:
    def annex_03(
        self,
        month: int,
        year: int,
        institution: dict[str, Any] | None = None,
        import_id: int | None = None,
    ) -> dict[str, Any]:
        inst = institution or self._institution()
        attendance_rows = attendance_service.list_month(
            month, year, import_id=import_id
        )
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

    def annex_04(self, month: int, year: int, import_id: int | None = None) -> dict[str, Any]:
        attendance_rows = attendance_service.list_month(
            month, year, import_id=import_id
        )
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

    def monthly_workbook(
        self,
        month: int,
        year: int,
        import_id: int | None = None,
        institution_override: dict[str, Any] | None = None,
    ) -> BytesIO:
        if month < 1 or month > 12:
            raise ValueError("invalid_month")
        institution = {**self._institution()}
        if institution_override:
            # Solo campos de cabecera permitidos
            for key in (
                "ugel", "school_name", "modular_code", "education_level",
                "shift_name", "address", "department", "province", "district",
            ):
                if key in institution_override and institution_override[key] is not None:
                    institution[key] = institution_override[key]
        staff_rows = self._staff_rows(month, year, import_id=import_id)
        workbook = Workbook()
        attendance_sheet = workbook.active
        attendance_sheet.title = "Anexo 03 - Asistencia"
        consolidated_sheet = workbook.create_sheet("Anexo 04 - Consolidado")
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

    def _staff_rows(
        self, month: int, year: int, import_id: int | None = None
    ) -> list[dict[str, Any]]:
        attendance_rows = attendance_service.list_month(
            month, year, import_id=import_id
        )
        days_by_staff: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
        for item in attendance_rows:
            days_by_staff[item["staff_member_id"]][item["attendance_date"]] = item
        rows = []
        for staff in staff_member_service.list(is_active="Y"):
            rows.append({**staff, "days": days_by_staff.get(staff["id"], {})})
        return rows

    def _write_official_header(
        self,
        sheet: Any,
        institution: dict[str, Any],
        month: int,
        year: int,
        annex_label: str,
        title: str,
        end_column: int,
    ) -> int:
        ugel = _safe(institution.get("ugel"))
        school = _safe(institution.get("school_name"))
        level = _safe(institution.get("education_level"))
        modular = _safe(institution.get("modular_code"))
        address = _safe(institution.get("address") or institution.get("lugar"))
        department = _safe(
            institution.get("department") or institution.get("departamento") or "PUNO"
        )
        province = _safe(
            institution.get("province") or institution.get("provincia")
        )
        district = _safe(
            institution.get("district") or institution.get("distrito")
        )
        shift = _safe(institution.get("shift_name"))

        # Fila 1 — texto legal
        sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=end_column)
        cell = sheet.cell(1, 1, LEGAL_HEADER)
        cell.font = Font(bold=True, size=8, name="Calibri")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        sheet.row_dimensions[1].height = 26

        # Fila 2 — ANEXO
        sheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=end_column)
        cell = sheet.cell(2, 1, annex_label)
        cell.font = Font(bold=True, size=11, name="Calibri")
        cell.alignment = CENTER
        sheet.row_dimensions[2].height = 16

        # Fila 3 — titulo azul
        sheet.merge_cells(start_row=3, start_column=1, end_row=3, end_column=end_column)
        cell = sheet.cell(3, 1, title)
        cell.fill = FILL_TITLE
        cell.font = FONT_TITLE
        cell.alignment = CENTER
        sheet.row_dimensions[3].height = 20

        # --- Bloque datos (filas 4-7) — sin merges que se pisen ---
        # Fila 4
        sheet.cell(4, 1, "UGEL:").font = FONT_BLACK_BOLD
        sheet.cell(4, 2, ugel).font = Font(bold=True, size=10, name="Calibri")
        sheet.cell(4, 5, "MES:").font = FONT_BLACK_BOLD
        sheet.cell(4, 6, MONTH_NAMES[month - 1]).font = FONT_RED_BOLD
        sheet.cell(4, 8, "ANO:").font = FONT_BLACK_BOLD
        sheet.cell(4, 9, year).font = FONT_RED_BOLD
        sheet.cell(4, 11, "TURNO:").font = FONT_BLACK_BOLD
        sheet.cell(4, 12, shift).font = FONT_RED_BOLD
        sheet.row_dimensions[4].height = 15

        # Fila 5
        sheet.cell(5, 1, "INSTITUCION EDUCATIVA:").font = FONT_BLACK_BOLD
        sheet.cell(5, 2, school).font = FONT_RED_BOLD
        sheet.cell(5, 5, "LUGAR:").font = FONT_BLACK_BOLD
        sheet.cell(5, 6, address).font = FONT_RED_BOLD
        sheet.row_dimensions[5].height = 15

        # Fila 6
        sheet.cell(6, 1, "NIVEL EDUCATIVO Y MODALIDAD:").font = FONT_BLACK_BOLD
        sheet.cell(6, 2, level).font = FONT_RED_BOLD
        sheet.cell(6, 5, "DEP:").font = FONT_BLACK_BOLD
        sheet.cell(6, 6, department).font = FONT_RED_BOLD
        sheet.cell(6, 8, "PROV:").font = FONT_BLACK_BOLD
        sheet.cell(6, 9, province).font = FONT_RED_BOLD
        sheet.cell(6, 11, "DIS:").font = FONT_BLACK_BOLD
        sheet.cell(6, 12, district).font = FONT_RED_BOLD
        sheet.row_dimensions[6].height = 15

        # Fila 7
        sheet.cell(7, 1, "CODIGO MODULAR:").font = FONT_BLACK_BOLD
        sheet.cell(7, 2, modular).font = FONT_RED_BOLD
        sheet.row_dimensions[7].height = 15

        # Fila 8 vacía separadora
        sheet.row_dimensions[8].height = 6

        return 9

    def _write_attendance_sheet(
        self,
        sheet: Any,
        institution: dict[str, Any],
        staff_rows: list[dict[str, Any]],
        month: int,
        year: int,
    ) -> None:
        days = monthrange(year, month)[1]
        first_day_col = 7
        end_column = first_day_col + days - 1

        table_start = self._write_official_header(
            sheet,
            institution,
            month,
            year,
            "ANEXO 03",
            "FORMATO 01: REPORTE DE ASISTENCIA DETALLADO",
            end_column,
        )

        fixed_headers = [
            "N°", "DNI", "APELLIDOS Y NOMBRES", "CARGO",
            "CONDICION LABORAL", "JORNADA LABORAL",
        ]
        header_row = table_start
        day_row = table_start + 1
        weekday_row = table_start + 2

        for col, header in enumerate(fixed_headers, start=1):
            sheet.merge_cells(
                start_row=header_row, start_column=col,
                end_row=day_row, end_column=col,
            )
            cell = sheet.cell(header_row, col, header)
            cell.fill = FILL_HEADER
            cell.font = FONT_BLACK_BOLD
            cell.alignment = CENTER
            cell.border = THIN_BORDER
            sheet.cell(day_row, col).border = THIN_BORDER
            sheet.cell(day_row, col).fill = FILL_HEADER

        # DIAS CALENDARIO
        sheet.merge_cells(
            start_row=header_row, start_column=first_day_col,
            end_row=header_row, end_column=end_column,
        )
        cell = sheet.cell(header_row, first_day_col, "DIAS CALENDARIO")
        cell.fill = FILL_HEADER
        cell.font = FONT_BLACK_BOLD
        cell.alignment = CENTER
        for c in range(first_day_col, end_column + 1):
            sheet.cell(header_row, c).border = THIN_BORDER
            sheet.cell(header_row, c).fill = FILL_HEADER

        weekday_labels = ["lu.", "ma.", "mi.", "ju.", "vi.", "sa.", "do."]
        for day in range(1, days + 1):
            col = first_day_col + day - 1
            cell = sheet.cell(day_row, col, day)
            cell.fill = FILL_HEADER
            cell.font = FONT_BLACK_BOLD
            cell.alignment = CENTER
            cell.border = THIN_BORDER
            wd = sheet.cell(
                weekday_row, col,
                weekday_labels[date(year, month, day).weekday()],
            )
            wd.font = FONT_SMALL
            wd.alignment = CENTER
            wd.border = THIN_BORDER

        sheet.row_dimensions[header_row].height = 18
        sheet.row_dimensions[day_row].height = 14
        sheet.row_dimensions[weekday_row].height = 12

        data_start = weekday_row + 1
        status_code = {
            "present": "A", "late": "T", "absent": "F",
            "justified": "J", "leave": "L", "permission": "P",
        }

        for index, staff in enumerate(staff_rows, start=1):
            row = data_start + index - 1
            values = [
                index,
                staff.get("dni") or "",
                _safe(self._full_name(staff)),
                _safe(staff.get("job_title")),
                _safe(staff.get("employment_status")),
                "",
            ]
            for col, value in enumerate(values, start=1):
                cell = sheet.cell(row, col, value)
                cell.border = THIN_BORDER
                cell.font = FONT_NORMAL
                cell.alignment = CENTER if col in (1, 2) else LEFT
                if index % 2 == 0:
                    cell.fill = FILL_ALT

            for day in range(1, days + 1):
                attendance = staff["days"].get(date(year, month, day).isoformat())
                status = attendance.get("status") if attendance else ""
                code = status_code.get(status, "")
                cell = sheet.cell(row, first_day_col + day - 1, code)
                cell.alignment = CENTER
                cell.border = THIN_BORDER
                cell.font = FONT_SMALL
                if index % 2 == 0:
                    cell.fill = FILL_ALT

            sheet.row_dimensions[row].height = 14

        last_row = data_start + max(len(staff_rows), 1) - 1
        if not staff_rows:
            for col in range(1, end_column + 1):
                sheet.cell(data_start, col).border = THIN_BORDER
            sheet.row_dimensions[data_start].height = 14

        for col, width in enumerate([4, 10, 30, 12, 14, 10], start=1):
            sheet.column_dimensions[get_column_letter(col)].width = width
        for d in range(days):
            sheet.column_dimensions[get_column_letter(first_day_col + d)].width = 3.2

        self._apply_print_settings(sheet, header_row, last_row, end_column)
        sheet.freeze_panes = f"{get_column_letter(first_day_col)}{data_start}"

    def _write_consolidated_sheet(
        self,
        sheet: Any,
        institution: dict[str, Any],
        staff_rows: list[dict[str, Any]],
        month: int,
        year: int,
    ) -> None:
        headers = [
            "N°", "DNI", "APELLIDOS Y NOMBRES", "CARGO",
            "CONDICION LABORAL", "JORNADA LABORAL",
            "INASIST. JUSTIF. DIAS",
            "LIC. CON GOCE", "LIC. SIN GOCE", "LIC. DU",
            "FALTAS DIAS", "TARDANZAS MIN (*)",
            "PERM. SG HORAS (*)", "PERM. SG MIN (*)",
            "HUELGA PARO DIAS", "Observaciones",
        ]
        end_column = len(headers)

        table_start = self._write_official_header(
            sheet,
            institution,
            month,
            year,
            "ANEXO 04",
            "FORMATO 02: REPORTE CONSOLIDADO DE INASISTENCIAS, TARDANZAS Y PERMISOS SIN GOCE DE REMUNERACION",
            end_column,
        )

        header_row = table_start
        for col, header in enumerate(headers, start=1):
            cell = sheet.cell(header_row, col, header)
            cell.fill = FILL_HEADER
            cell.font = FONT_BLACK_BOLD
            cell.alignment = CENTER
            cell.border = THIN_BORDER
        sheet.row_dimensions[header_row].height = 32

        data_start = header_row + 1
        for index, staff in enumerate(staff_rows, start=1):
            status_counts = Counter(item["status"] for item in staff["days"].values())
            late_minutes = sum(
                item.get("late_minutes", 0)
                for item in staff["days"].values()
                if item.get("status") == "late"
            )
            row = data_start + index - 1
            values = [
                index,
                staff.get("dni") or "",
                _safe(self._full_name(staff)),
                _safe(staff.get("job_title")),
                _safe(staff.get("employment_status")),
                "",
                status_counts.get("justified", 0),
                status_counts.get("leave", 0),
                0, 0,
                status_counts.get("absent", 0),
                late_minutes,
                0, 0, 0, "",
            ]
            for col, value in enumerate(values, start=1):
                cell = sheet.cell(row, col, value)
                cell.border = THIN_BORDER
                cell.font = FONT_NORMAL
                cell.alignment = CENTER if col in (1, 2) or col >= 7 else LEFT
                if index % 2 == 0:
                    cell.fill = FILL_ALT
            sheet.row_dimensions[row].height = 14

        last_row = data_start + max(len(staff_rows), 1) - 1
        if not staff_rows:
            for col in range(1, end_column + 1):
                sheet.cell(data_start, col).border = THIN_BORDER
            sheet.row_dimensions[data_start].height = 14

        widths = [4, 10, 28, 12, 14, 10, 12, 10, 10, 8, 9, 12, 11, 11, 11, 18]
        for col, width in enumerate(widths, start=1):
            sheet.column_dimensions[get_column_letter(col)].width = width

        self._apply_print_settings(sheet, header_row, last_row, end_column)
        sheet.freeze_panes = f"A{data_start}"

    def _apply_print_settings(
        self, sheet: Any, start_row: int, end_row: int, end_column: int
    ) -> None:
        sheet.sheet_view.showGridLines = False
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_margins.left = 0.25
        sheet.page_margins.right = 0.25
        sheet.page_margins.top = 0.35
        sheet.page_margins.bottom = 0.35
        sheet.print_title_rows = f"1:{start_row}"
        sheet.print_area = f"A1:{get_column_letter(end_column)}{end_row}"

    def _staff_member(self, staff_member_id: int) -> dict[str, Any]:
        try:
            return staff_member_service.get(staff_member_id)
        except StaffMemberNotFoundError:
            return {"dni": None, "last_names": "Unknown", "first_names": "Staff"}

    def _full_name(self, staff_member: dict[str, Any]) -> str:
        last = staff_member.get("last_names") or ""
        first = staff_member.get("first_names") or ""
        return f"{last}, {first}".strip(", ")

    def _institution(self) -> dict[str, Any]:
        try:
            inst = institution_repository.get_active()
            if inst:
                return {**DEMO_INSTITUTION, **inst}
            return DEMO_INSTITUTION
        except OracleRepositoryError:
            return DEMO_INSTITUTION


report_service = ReportService()
