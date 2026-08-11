"""Oracle repository for justification."""

from __future__ import annotations

from datetime import date
from typing import Any

import oracledb

from app.repositories.oracle import (
    OracleRepositoryError,
    oracle_connection,
    oracle_date,
    oracle_timestamp,
)


class JustificationRepository:
    def list(
        self, staff_member_id: int | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT id, staff_member_id, start_date, end_date, norm_code,
                   with_pay, reason, support_file_path, registered_by_id,
                   registered_at, status
            FROM justification
            WHERE (:staff_member_id IS NULL OR staff_member_id = :staff_member_id)
              AND (:status IS NULL OR status = :status)
            ORDER BY start_date DESC, id DESC
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, staff_member_id=staff_member_id, status=status)
                    return [self._row(row) for row in cursor.fetchall()]
        except oracledb.Error as exc:
            raise OracleRepositoryError("Justification list failed") from exc

    def get(self, justification_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, staff_member_id, start_date, end_date, norm_code,
                   with_pay, reason, support_file_path, registered_by_id,
                   registered_at, status
            FROM justification
            WHERE id = :id
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, id=justification_id)
                    row = cursor.fetchone()
                    return self._row(row) if row else None
        except oracledb.Error as exc:
            raise OracleRepositoryError("Justification lookup failed") from exc

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = """
            INSERT INTO justification (
                staff_member_id, start_date, end_date, norm_code, with_pay,
                reason, support_file_path, registered_by_id, status
            ) VALUES (
                :staff_member_id, :start_date, :end_date, :norm_code, :with_pay,
                :reason, :support_file_path, :registered_by_id, 'active'
            )
            RETURNING id INTO :id
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    new_id = cursor.var(oracledb.NUMBER)
                    cursor.execute(sql, id=new_id, **self._payload(data))
                connection.commit()
                return self.get(int(new_id.getvalue()[0]))
        except oracledb.Error as exc:
            raise OracleRepositoryError("Justification create failed") from exc

    def update(
        self, justification_id: int, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        sql = """
            UPDATE justification
               SET staff_member_id = :staff_member_id,
                   start_date = :start_date,
                   end_date = :end_date,
                   norm_code = :norm_code,
                   with_pay = :with_pay,
                   reason = :reason,
                   support_file_path = :support_file_path,
                   registered_by_id = :registered_by_id
             WHERE id = :id
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, id=justification_id, **self._payload(data))
                    if cursor.rowcount == 0:
                        connection.rollback()
                        return None
                connection.commit()
                return self.get(justification_id)
        except oracledb.Error as exc:
            raise OracleRepositoryError("Justification update failed") from exc

    def cancel(self, justification_id: int) -> dict[str, Any] | None:
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE justification SET status = 'cancelled' WHERE id = :id",
                        id=justification_id,
                    )
                    if cursor.rowcount == 0:
                        connection.rollback()
                        return None
                connection.commit()
                return self.get(justification_id)
        except oracledb.Error as exc:
            raise OracleRepositoryError("Justification cancel failed") from exc

    def _payload(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "staff_member_id": data["staff_member_id"],
            "start_date": date.fromisoformat(data["start_date"]),
            "end_date": date.fromisoformat(data["end_date"]),
            "norm_code": data["norm_code"],
            "with_pay": data.get("with_pay", "Y"),
            "reason": data.get("reason"),
            "support_file_path": data.get("support_file_path"),
            "registered_by_id": data.get("registered_by_id"),
        }

    def _row(self, row: Any) -> dict[str, Any]:
        return {
            "id": int(row[0]),
            "staff_member_id": int(row[1]),
            "start_date": oracle_date(row[2]),
            "end_date": oracle_date(row[3]),
            "norm_code": row[4],
            "with_pay": row[5],
            "reason": row[6],
            "support_file_path": row[7],
            "registered_by_id": int(row[8]) if row[8] is not None else None,
            "registered_at": oracle_timestamp(row[9]),
            "status": row[10],
        }


justification_repository = JustificationRepository()
