"""TEC-D07 — justifications with support file path."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

from app.core.runtime import use_memory_fallback
from app.repositories.justification_repository import justification_repository
from app.repositories.oracle import OracleRepositoryError
from app.services.attendance_service import attendance_service


class JustificationNotFoundError(LookupError):
    """Raised when a justification does not exist."""


class JustificationValidationError(ValueError):
    """Raised when justification data is invalid."""


class JustificationService:
    def __init__(self) -> None:
        self._items: dict[int, dict[str, Any]] = {}
        self._seq = 0

    def reset(self) -> None:
        self._items = {}
        self._seq = 0

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = self._validated_payload(data)
        attendance_status = self._attendance_status(payload["norm_code"])
        try:
            item = justification_repository.create(payload, attendance_status)
            if item is None:
                raise JustificationValidationError("no_absences_in_range")
            return item
        except OracleRepositoryError as exc:
            use_memory_fallback("justification create", exc)

        self._seq += 1
        item = {**payload, "id": self._seq, "status": "active"}
        self._items[self._seq] = item
        changed = attendance_service.apply_justification_range(
            justification_id=item["id"],
            staff_member_id=item["staff_member_id"],
            start_date=date.fromisoformat(item["start_date"]),
            end_date=date.fromisoformat(item["end_date"]),
            status=attendance_status,
        )
        if not changed:
            self._items.pop(item["id"], None)
            raise JustificationValidationError("no_absences_in_range")
        return deepcopy(item)

    def update(self, justification_id: int, data: dict[str, Any]) -> dict[str, Any]:
        payload = self._validated_payload(data)
        try:
            old_item = justification_repository.get(justification_id)
            if old_item is None:
                raise JustificationNotFoundError(
                    f"Justification {justification_id} not found"
                )
            item = justification_repository.update(justification_id, payload)
            if item is None:
                raise JustificationNotFoundError(
                    f"Justification {justification_id} not found"
                )
            attendance_service.cancel_justification(justification_id)
            attendance_service.apply_justification_range(
                justification_id=justification_id,
                staff_member_id=item["staff_member_id"],
                start_date=date.fromisoformat(item["start_date"]),
                end_date=date.fromisoformat(item["end_date"]),
                status=self._attendance_status(item["norm_code"]),
            )
            return {"old": old_item, "new": item}
        except OracleRepositoryError as exc:
            use_memory_fallback("justification update", exc)

        item = self._find(justification_id)
        old_item = deepcopy(item)
        item.update(payload)
        attendance_service.cancel_justification(justification_id)
        attendance_service.apply_justification_range(
            justification_id=justification_id,
            staff_member_id=item["staff_member_id"],
            start_date=date.fromisoformat(item["start_date"]),
            end_date=date.fromisoformat(item["end_date"]),
            status=self._attendance_status(item["norm_code"]),
        )
        return {"old": old_item, "new": deepcopy(item)}

    def list(
        self, staff_member_id: int | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        try:
            return justification_repository.list(staff_member_id, status)
        except OracleRepositoryError as exc:
            use_memory_fallback("justification list", exc)

        rows = list(self._items.values())
        if staff_member_id:
            rows = [
                row for row in rows if row.get("staff_member_id") == staff_member_id
            ]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        return [deepcopy(row) for row in rows]

    def get(self, justification_id: int) -> dict[str, Any]:
        try:
            item = justification_repository.get(justification_id)
            if item is not None:
                return item
        except OracleRepositoryError as exc:
            use_memory_fallback("justification lookup", exc)
        return deepcopy(self._find(justification_id))

    def cancel(self, justification_id: int, reason: str) -> dict[str, Any]:
        try:
            item = justification_repository.cancel(justification_id)
            if item is None:
                raise JustificationNotFoundError(
                    f"Justification {justification_id} not found"
                )
            attendance_service.cancel_justification(justification_id)
            item["cancel_reason"] = reason
            return item
        except OracleRepositoryError as exc:
            use_memory_fallback("justification cancellation", exc)

        item = self._find(justification_id)
        item["status"] = "cancelled"
        item["cancel_reason"] = reason
        attendance_service.cancel_justification(justification_id)
        return deepcopy(item)

    def _find(self, justification_id: int) -> dict[str, Any]:
        try:
            return self._items[justification_id]
        except KeyError as exc:
            raise JustificationNotFoundError(
                f"Justification {justification_id} not found"
            ) from exc

    def _validated_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        start_date = self._parse_date(data["start_date"])
        end_date = self._parse_date(data["end_date"])
        if end_date < start_date:
            raise JustificationValidationError("invalid_date_range")
        with_pay = data.get("with_pay", "Y")
        if with_pay not in {"Y", "N"}:
            raise JustificationValidationError("invalid_with_pay")
        staff_member_id = data.get("staff_member_id")
        if not isinstance(staff_member_id, int) or staff_member_id <= 0:
            raise JustificationValidationError("invalid_staff_member")
        norm_code = str(data.get("norm_code", "")).strip().upper()
        if norm_code not in {"LG", "LS", "P", "J", "H", "F", "LIC", "PER"}:
            raise JustificationValidationError("invalid_norm_code")
        if norm_code == "LG":
            with_pay = "Y"
        elif norm_code in {"LS", "P", "J", "H", "F"}:
            with_pay = "N"
        reason = data.get("reason")
        if isinstance(reason, str):
            reason = reason.strip() or None
        return {
            "staff_member_id": staff_member_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "norm_code": norm_code,
            "with_pay": with_pay,
            "reason": reason,
            "support_file_path": data.get("support_file_path"),
            "registered_by_id": data.get("registered_by_id"),
        }

    def _parse_date(self, value: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise JustificationValidationError("invalid_date") from exc

    def _attendance_status(self, norm_code: str) -> str:
        if norm_code in {"LG", "LS", "LIC"}:
            return "leave"
        if norm_code in {"P", "PER"}:
            return "permission"
        return "justified"


justification_service = JustificationService()
