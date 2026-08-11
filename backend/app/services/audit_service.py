"""TEC-D11 — audit trail (persists when Oracle available; always logs structured events)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.repositories.audit_repository import audit_repository
from app.repositories.oracle import OracleRepositoryError


class AuditService:
    def __init__(self) -> None:
        self._memory: list[dict[str, Any]] = []

    def record(
        self,
        *,
        user_id: int,
        entity_name: str,
        entity_id: int,
        action_name: str,
        old_value: Any = None,
        new_value: Any = None,
    ) -> dict[str, Any]:
        entry = {
            "user_account_id": user_id,
            "entity_name": entity_name,
            "entity_id": entity_id,
            "action_name": action_name,
            "old_value": old_value,
            "new_value": new_value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._memory.append(entry)
        try:
            audit_repository.record(
                user_id=user_id,
                entity_name=entity_name,
                entity_id=entity_id,
                action_name=action_name,
                old_value=old_value,
                new_value=new_value,
            )
        except OracleRepositoryError:
            pass
        return entry


audit_service = AuditService()
