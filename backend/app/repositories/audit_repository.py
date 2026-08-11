"""Oracle repository for audit_log."""

from __future__ import annotations

from typing import Any

import oracledb

from app.repositories.oracle import (
    OracleRepositoryError,
    oracle_connection,
    to_json_clob,
)


class AuditRepository:
    def record(
        self,
        *,
        user_id: int,
        entity_name: str,
        entity_id: int,
        action_name: str,
        old_value: Any = None,
        new_value: Any = None,
    ) -> None:
        sql = """
            INSERT INTO audit_log (
                user_account_id, entity_name, entity_id, action_name,
                old_value, new_value
            ) VALUES (
                :user_id, :entity_name, :entity_id, :action_name,
                :old_value, :new_value
            )
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        sql,
                        user_id=user_id,
                        entity_name=entity_name,
                        entity_id=entity_id,
                        action_name=action_name,
                        old_value=to_json_clob(old_value),
                        new_value=to_json_clob(new_value),
                    )
                connection.commit()
        except oracledb.Error as exc:
            raise OracleRepositoryError("Audit insert failed") from exc


audit_repository = AuditRepository()
