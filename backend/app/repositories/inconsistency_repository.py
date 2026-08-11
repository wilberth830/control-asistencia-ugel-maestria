"""Oracle repository for inconsistency."""

from __future__ import annotations

from typing import Any

import oracledb

from app.repositories.oracle import (
    OracleRepositoryError,
    oracle_connection,
    oracle_timestamp,
)


class InconsistencyRepository:
    def list(self, status: str | None = None) -> list[dict[str, Any]]:
        sql = """
            SELECT id, mark_id, issue_type, description, status, detected_at
            FROM inconsistency
            WHERE (:status IS NULL OR status = :status)
            ORDER BY detected_at DESC, id DESC
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, status=status)
                    return [self._row(row) for row in cursor.fetchall()]
        except oracledb.Error as exc:
            raise OracleRepositoryError("Inconsistency list failed") from exc

    def set_status(self, inconsistency_id: int, status: str) -> dict[str, Any] | None:
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE inconsistency
                           SET status = :status
                         WHERE id = :id
                        """,
                        id=inconsistency_id,
                        status=status,
                    )
                    if cursor.rowcount == 0:
                        connection.rollback()
                        return None
                connection.commit()
                return self.get(inconsistency_id)
        except oracledb.Error as exc:
            raise OracleRepositoryError("Inconsistency update failed") from exc

    def get(self, inconsistency_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, mark_id, issue_type, description, status, detected_at
            FROM inconsistency
            WHERE id = :id
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, id=inconsistency_id)
                    row = cursor.fetchone()
                    return self._row(row) if row else None
        except oracledb.Error as exc:
            raise OracleRepositoryError("Inconsistency lookup failed") from exc

    def _row(self, row: Any) -> dict[str, Any]:
        return {
            "id": int(row[0]),
            "mark_id": int(row[1]),
            "issue_type": row[2],
            "description": row[3],
            "status": row[4],
            "detected_at": oracle_timestamp(row[5]),
        }


inconsistency_repository = InconsistencyRepository()
