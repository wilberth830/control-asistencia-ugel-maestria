"""TEC-D05 — biometric import wizard (draft → confirm/cancel)."""

from __future__ import annotations

import csv
from copy import deepcopy
from datetime import datetime
from io import StringIO
import re
from typing import Any

from app.repositories.biometric_repository import biometric_repository
from app.repositories.ai_usage_repository import ai_usage_repository
from app.repositories.oracle import OracleRepositoryError
from app.services.ai_biometric_normalizer_service import (
    AINormalizationResult,
    ai_biometric_normalizer_service,
)
from app.services.staff_member_service import (
    StaffMemberConflictError,
    staff_member_service,
)


class BiometricImportError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class BiometricImportService:
    def __init__(self) -> None:
        self._imports: dict[int, dict[str, Any]] = {}
        self._seq = 0

    def reset(self) -> None:
        self._imports = {}
        self._seq = 0

    def list(
        self,
        *,
        status: str | None = None,
        month: int | None = None,
        year: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        try:
            rows = biometric_repository.list_imports(
                status=status, month=month, year=year, limit=limit
            )
            memory_by_id = {
                row["id"]: deepcopy(row)
                for row in self._imports.values()
                if self._matches_filters(row, status=status, month=month, year=year)
            }
            rows = [memory_by_id.pop(row["id"], row) for row in rows]
            memory_rows = sorted(
                memory_by_id.values(), key=lambda row: row["id"], reverse=True
            )
            combined = memory_rows + rows
            return combined[:limit] if limit else combined
        except OracleRepositoryError:
            pass

        rows = list(self._imports.values())
        rows = [
            row
            for row in rows
            if self._matches_filters(row, status=status, month=month, year=year)
        ]
        rows = sorted(rows, key=lambda row: row["id"], reverse=True)
        if limit:
            rows = rows[:limit]
        return [deepcopy(row) for row in rows]

    def create_draft_from_csv(
        self, file_name: str, content: bytes, user_account_id: int | None = None
    ) -> dict[str, Any]:
        rows, ai_usage = self._parse_input_file(file_name, content)
        final_file_name = self._timestamped_file_name(file_name)
        if ai_usage and ai_usage.source == "openai":
            final_file_name = self._file_name_with_ai_cost(
                final_file_name, ai_usage.estimated_cost_usd
            )
        final_file_name = self._fit_file_name(final_file_name)
        return self._create_draft(
            final_file_name, rows, user_account_id, ai_usage
        )

    def get(self, import_id: int) -> dict[str, Any] | None:
        row = self._imports.get(import_id)
        if row:
            return deepcopy(row)
        try:
            return biometric_repository.get_import(import_id)
        except OracleRepositoryError:
            return None

    def update_row(
        self,
        import_id: int,
        row_id: int,
        *,
        action: str,
        dni: str | None = None,
        last_names: str | None = None,
        first_names: str | None = None,
    ) -> dict[str, Any]:
        imp = self._find(import_id)
        if imp["status"] != "draft":
            raise BiometricImportError("conflict_not_draft")
        row = self._find_row(imp, row_id)
        if dni:
            row["dni"] = dni
        if last_names:
            row["last_names"] = last_names
        if first_names:
            row["first_names"] = first_names

        if action == "research":
            self._apply_match(row)
            row["resolved"] = row["match"] == "matched"
        elif action == "register_new":
            self._register_new_staff(row)
            self._apply_match(row)
            row["resolved"] = True
        elif action == "skip":
            row["skipped"] = True
            row["resolved"] = True
        else:
            raise BiometricImportError("invalid_row_action")

        self._refresh_counters(imp)
        return deepcopy(row)

    def confirm(self, import_id: int) -> dict[str, Any]:
        from app.services.attendance_service import attendance_service

        imp = self._find(import_id)
        if imp["status"] != "draft":
            raise BiometricImportError("conflict_not_draft")
        registered_dnis: set[str] = set()
        for row in imp["rows"]:
            if row.get("skipped"):
                continue
            if (
                row.get("match") == "new"
                and not row.get("staff_member_id")
                and row["dni"] not in registered_dnis
            ):
                self._register_new_staff(row)
                registered_dnis.add(row["dni"])
        self._apply_matches(imp["rows"])
        for row in imp["rows"]:
            if row.get("match") == "matched":
                row["resolved"] = True
        self._refresh_counters(imp)
        imp["status"] = "confirmed"
        imp["ok_rows"] = sum(1 for row in imp["rows"] if not row.get("skipped"))
        imp["error_rows"] = sum(1 for row in imp["rows"] if row.get("skipped"))
        mark_rows = []
        attendance_rows_by_key: dict[tuple[int, str], dict[str, Any]] = {}
        for row in imp["rows"]:
            if row.get("skipped") or not row.get("staff_member_id"):
                continue
            marked_at = datetime.fromisoformat(str(row["marked_at"]))
            mark_rows.append(
                {
                    "staff_member_id": row["staff_member_id"],
                    "biometric_import_id": imp["id"],
                    "marked_at": marked_at,
                    "mark_type": row["mark_type"],
                    "status": "valid",
                }
            )
            attendance_date = str(row["marked_at"])[:10]
            attendance_rows_by_key[(row["staff_member_id"], attendance_date)] = {
                "staff_member_id": row["staff_member_id"],
                "biometric_import_id": imp["id"],
                "attendance_date": attendance_date,
                "status": "present",
                "late_minutes": 0,
                "justification_id": None,
            }
        try:
            biometric_repository.insert_marks(mark_rows)
        except OracleRepositoryError:
            pass
        attendance_service.bulk_upsert_days(list(attendance_rows_by_key.values()))
        try:
            persisted = biometric_repository.update_import(imp["id"], imp)
            if persisted:
                imp.update(persisted)
        except OracleRepositoryError:
            pass
        return deepcopy(imp)

    def cancel(self, import_id: int, reason: str) -> dict[str, Any]:
        try:
            imp = self._find(import_id)
        except BiometricImportError:
            try:
                persisted = biometric_repository.get_import(import_id)
            except OracleRepositoryError:
                persisted = None
            if not persisted:
                raise
            if persisted["status"] == "cancelled":
                raise BiometricImportError("conflict_cancelled")
            persisted["status"] = "cancelled"
            updated = biometric_repository.update_import(import_id, persisted)
            updated = updated or persisted
            updated["cancel_reason"] = reason
            return updated
        if imp["status"] == "cancelled":
            raise BiometricImportError("conflict_cancelled")
        imp["status"] = "cancelled"
        imp["cancel_reason"] = reason
        try:
            persisted = biometric_repository.update_import(imp["id"], imp)
            if persisted:
                imp.update(persisted)
        except OracleRepositoryError:
            pass
        return deepcopy(imp)

    def _create_draft(
        self,
        file_name: str,
        rows: list[dict[str, Any]],
        user_account_id: int | None = None,
        ai_usage: AINormalizationResult | None = None,
    ) -> dict[str, Any]:
        imp = {
            "id": 0,
            "file_name": file_name,
            "file_path": None,
            "user_account_id": user_account_id,
            "status": "draft",
            "period_start": self._period_value(rows, minimum=True),
            "period_end": self._period_value(rows, minimum=False),
            "total_rows": len(rows),
            "matched_rows": 0,
            "new_rows": 0,
            "ok_rows": 0,
            "error_rows": 0,
            "rows": rows,
            "normalization_source": ai_usage.source if ai_usage else "parser",
            "ai_estimated_cost_usd": (
                str(ai_usage.estimated_cost_usd) if ai_usage else "0"
            ),
        }
        self._refresh_counters(imp)
        try:
            persisted = biometric_repository.create_import(imp)
            imp.update(persisted)
        except OracleRepositoryError:
            self._seq += 1
            imp["id"] = self._seq
        if ai_usage and ai_usage.source == "openai":
            self._record_ai_usage(imp, ai_usage)
        self._imports[imp["id"]] = imp
        return deepcopy(imp)

    def _timestamped_file_name(self, file_name: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        if "." not in file_name:
            return f"{file_name}_{timestamp}"
        stem, extension = file_name.rsplit(".", 1)
        return f"{stem}_{timestamp}.{extension}"

    def _file_name_with_ai_cost(self, file_name: str, cost: Any) -> str:
        suffix = f"ia_usd_{str(cost).replace('.', '_')}"
        if "." not in file_name:
            return f"{file_name}_{suffix}"
        stem, extension = file_name.rsplit(".", 1)
        return f"{stem}_{suffix}.{extension}"

    def _fit_file_name(self, file_name: str, max_length: int = 255) -> str:
        if len(file_name) <= max_length:
            return file_name
        if "." not in file_name:
            return file_name[:max_length]
        stem, extension = file_name.rsplit(".", 1)
        extension_part = f".{extension}"
        available_stem_length = max_length - len(extension_part)
        if available_stem_length <= 0:
            return file_name[:max_length]
        return f"{stem[:available_stem_length]}{extension_part}"

    def _record_ai_usage(
        self, imp: dict[str, Any], ai_usage: AINormalizationResult
    ) -> None:
        try:
            ai_usage_repository.record(
                {
                    "biometric_import_id": imp["id"],
                    "file_name": imp["file_name"],
                    "provider": ai_usage.provider or "openai",
                    "model_name": ai_usage.model or "",
                    "input_tokens": ai_usage.input_tokens,
                    "output_tokens": ai_usage.output_tokens,
                    "total_tokens": ai_usage.total_tokens,
                    "estimated_cost_usd": str(ai_usage.estimated_cost_usd),
                }
            )
        except OracleRepositoryError:
            pass

    def _matches_filters(
        self,
        row: dict[str, Any],
        *,
        status: str | None = None,
        month: int | None = None,
        year: int | None = None,
    ) -> bool:
        if status and row["status"] != status:
            return False
        if month and year:
            prefix = f"{year:04d}-{month:02d}"
            return str(row.get("period_start") or "").startswith(prefix) or str(
                row.get("period_end") or ""
            ).startswith(prefix)
        return True

    def _parse_input_file(
        self, file_name: str, content: bytes
    ) -> tuple[list[dict[str, Any]], AINormalizationResult | None]:
        text = self._decode_content(content)
        if file_name.lower().endswith((".bat", ".cmd")):
            text = self._extract_csv_from_batch(text)
        try:
            return self._parse_csv_text(text), None
        except BiometricImportError:
            normalized_result = ai_biometric_normalizer_service.normalize_to_csv(text)
            if not normalized_result:
                raise
            if isinstance(normalized_result, str):
                normalized_result = AINormalizationResult(
                    csv_text=normalized_result, source="openai"
                )
            return self._parse_csv_text(normalized_result.csv_text), normalized_result

    def _decode_content(self, content: bytes) -> str:
        for encoding in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise BiometricImportError("invalid_file")

    def _extract_csv_from_batch(self, text: str) -> str:
        rows: list[str] = []
        pattern = re.compile(r'^\s*(?:>|>>)\s*"?[^"]+"?\s+echo\s+(.+?)\s*$', re.I)
        for line in text.splitlines():
            match = pattern.match(line)
            if match:
                value = match.group(1).strip()
                if "," in value:
                    rows.append(value)
        if not rows:
            raise BiometricImportError("invalid_file")
        return "\n".join(rows)

    def _parse_csv_text(self, text: str) -> list[dict[str, Any]]:
        reader = csv.DictReader(StringIO(text), delimiter=self._detect_delimiter(text))
        field_map = self._field_map(reader.fieldnames or [])
        required_fields = {"dni", "marked_at", "mark_type"}
        if not required_fields.issubset(set(field_map.values())):
            raise BiometricImportError("invalid_file")

        rows: list[dict[str, Any]] = []
        for order, raw_row in enumerate(reader, start=1):
            normalized_row = self._normalized_csv_row(raw_row, field_map)
            marked_at = self._parse_marked_at(normalized_row.get("marked_at") or "")
            row = {
                "row_id": order,
                "order": order,
                "dni": (normalized_row.get("dni") or "").strip(),
                "last_names": (normalized_row.get("last_names") or "").strip(),
                "first_names": (normalized_row.get("first_names") or "").strip(),
                "marked_at": marked_at.isoformat(sep=" "),
                "mark_type": self._normalized_mark_type(
                    normalized_row.get("mark_type") or ""
                ),
                "match": "new",
                "staff_member_id": None,
                "resolved": False,
                "skipped": False,
            }
            if row["mark_type"] not in {"entry", "exit"}:
                raise BiometricImportError("invalid_file")
            rows.append(row)
        if not rows:
            raise BiometricImportError("invalid_file")
        self._apply_matches(rows)
        return rows

    def _field_map(self, fieldnames: list[str]) -> dict[str, str]:
        aliases = {
            "dni": "dni",
            "documento": "dni",
            "document_number": "dni",
            "document": "dni",
            "doc": "dni",
            "cedula": "dni",
            "employee_id": "dni",
            "user_id": "dni",
            "pin": "dni",
            "last_names": "last_names",
            "apellidos": "last_names",
            "apellido": "last_names",
            "surname": "last_names",
            "last_name": "last_names",
            "first_names": "first_names",
            "nombres": "first_names",
            "nombre": "first_names",
            "name": "first_names",
            "first_name": "first_names",
            "marked_at": "marked_at",
            "fecha_hora": "marked_at",
            "fecha hora": "marked_at",
            "fecha/hora": "marked_at",
            "fecha": "marked_at",
            "datetime": "marked_at",
            "date_time": "marked_at",
            "timestamp": "marked_at",
            "punch_time": "marked_at",
            "check_time": "marked_at",
            "mark_type": "mark_type",
            "tipo_marca": "mark_type",
            "tipo marca": "mark_type",
            "tipo": "mark_type",
            "event": "mark_type",
            "direction": "mark_type",
            "in_out": "mark_type",
        }
        return {
            field_name: aliases.get(field_name.strip().lower(), field_name)
            for field_name in fieldnames
        }

    def _normalized_csv_row(
        self, raw_row: dict[str, str | None], field_map: dict[str, str]
    ) -> dict[str, str]:
        row: dict[str, str] = {}
        for source, target in field_map.items():
            row[target] = (raw_row.get(source) or "").strip()
        return row

    def _normalized_mark_type(self, value: str) -> str:
        normalized = value.strip().lower()
        aliases = {
            "0": "entry",
            "1": "exit",
            "e": "entry",
            "s": "exit",
            "in": "entry",
            "out": "exit",
            "entrada": "entry",
            "ingreso": "entry",
            "check-in": "entry",
            "checkin": "entry",
            "salida": "exit",
            "egreso": "exit",
            "check-out": "exit",
            "checkout": "exit",
        }
        return aliases.get(normalized, normalized)

    def _detect_delimiter(self, text: str) -> str:
        sample = text[:4096]
        try:
            return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            return ","

    def _apply_match(self, row: dict[str, Any]) -> None:
        staff_member = staff_member_service.get_by_dni(row["dni"])
        if staff_member:
            row["match"] = "matched"
            row["staff_member_id"] = staff_member["id"]
            row["resolved"] = True
            row["skipped"] = False
        else:
            row["match"] = "new"
            row["staff_member_id"] = None

    def _apply_matches(self, rows: list[dict[str, Any]]) -> None:
        staff_by_dni = staff_member_service.get_by_dnis([row["dni"] for row in rows])
        for row in rows:
            staff_member = staff_by_dni.get(row["dni"])
            if staff_member:
                row["match"] = "matched"
                row["staff_member_id"] = staff_member["id"]
                row["resolved"] = True
                row["skipped"] = False
            else:
                row["match"] = "new"
                row["staff_member_id"] = None

    def _register_new_staff(self, row: dict[str, Any]) -> None:
        try:
            staff_member_service.create(
                {
                    "dni": row["dni"],
                    "last_names": row["last_names"] or "Sin apellidos",
                    "first_names": row["first_names"] or "Sin nombres",
                    "job_title": "No especificado",
                    "employment_status": "Registrado en carga biométrica",
                }
            )
        except StaffMemberConflictError:
            pass

    def _refresh_counters(self, imp: dict[str, Any]) -> None:
        rows = imp["rows"]
        imp["matched_rows"] = sum(1 for row in rows if row.get("match") == "matched")
        imp["new_rows"] = sum(
            1 for row in rows if row.get("match") == "new" and not row.get("resolved")
        )

    def _period_value(self, rows: list[dict[str, Any]], *, minimum: bool) -> str | None:
        dates = [str(row["marked_at"])[:10] for row in rows]
        if not dates:
            return None
        return min(dates) if minimum else max(dates)

    def _find(self, import_id: int) -> dict[str, Any]:
        try:
            return self._imports[import_id]
        except KeyError as exc:
            raise BiometricImportError("not_found") from exc

    def _find_row(self, imp: dict[str, Any], row_id: int) -> dict[str, Any]:
        for row in imp["rows"]:
            if row["row_id"] == row_id:
                return row
        raise BiometricImportError("row_not_found")

    def _parse_marked_at(self, value: str) -> datetime:
        try:
            return datetime.fromisoformat(value.strip())
        except ValueError as exc:
            raise BiometricImportError("invalid_file") from exc


biometric_import_service = BiometricImportService()
