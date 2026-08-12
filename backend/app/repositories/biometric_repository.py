"""Oracle repositories for biometric imports and marks."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import oracledb

from app.repositories.oracle import (
    OracleRepositoryError,
    oracle_connection,
    oracle_date,
    oracle_timestamp,
)


class BiometricRepository:
    def list_imports(
        self,
        *,
        status: str | None = None,
        month: int | None = None,
        year: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        period_filter = ""
        limit_filter = ""
        params: dict[str, Any] = {"status": status}
        if month and year:
            start_date = date(year, month, 1)
            end_date = date(year + int(month == 12), 1 if month == 12 else month + 1, 1)
            period_filter = """
              AND (
                  period_start >= :start_date AND period_start < :end_date
                  OR period_end >= :start_date AND period_end < :end_date
              )
            """
            params.update({"start_date": start_date, "end_date": end_date})
        inner_sql = f"""
            SELECT id, file_name, file_path, uploaded_at, user_account_id, status,
                   period_start, period_end, total_rows, ok_rows, error_rows,
                   matched_rows, new_rows
            FROM biometric_import
            WHERE (:status IS NULL OR status = :status)
            {period_filter}
            ORDER BY id DESC
        """
        if limit:
            limit_filter = "WHERE ROWNUM <= :limit"
            params["limit"] = limit
        sql = f"SELECT * FROM ({inner_sql}) {limit_filter}"
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, **params)
                    return [self._import_row(row) for row in cursor.fetchall()]
        except oracledb.Error as exc:
            raise OracleRepositoryError("Biometric import list failed") from exc

    def get_import(self, import_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, file_name, file_path, uploaded_at, user_account_id, status,
                   period_start, period_end, total_rows, ok_rows, error_rows,
                   matched_rows, new_rows
            FROM biometric_import
            WHERE id = :id
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, id=import_id)
                    row = cursor.fetchone()
                    return self._import_row(row) if row else None
        except oracledb.Error as exc:
            raise OracleRepositoryError("Biometric import lookup failed") from exc

    def create_import(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = """
            INSERT INTO biometric_import (
                file_name, file_path, user_account_id, status, period_start,
                period_end, total_rows, ok_rows, error_rows, matched_rows, new_rows
            ) VALUES (
                :file_name, :file_path, :user_account_id, :status, :period_start,
                :period_end, :total_rows, :ok_rows, :error_rows, :matched_rows, :new_rows
            )
            RETURNING id INTO :id
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    new_id = cursor.var(oracledb.NUMBER)
                    cursor.execute(sql, id=new_id, **self._import_payload(data))
                connection.commit()
                return self.get_import(int(new_id.getvalue()[0]))
        except oracledb.Error as exc:
            raise OracleRepositoryError("Biometric import create failed") from exc

    def update_import(
        self, import_id: int, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        sql = """
            UPDATE biometric_import
               SET status = :status,
                   period_start = :period_start,
                   period_end = :period_end,
                   total_rows = :total_rows,
                   ok_rows = :ok_rows,
                   error_rows = :error_rows,
                   matched_rows = :matched_rows,
                   new_rows = :new_rows
             WHERE id = :id
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    payload = self._import_payload(data)
                    cursor.execute(
                        sql,
                        id=import_id,
                        status=payload["status"],
                        period_start=payload["period_start"],
                        period_end=payload["period_end"],
                        total_rows=payload["total_rows"],
                        ok_rows=payload["ok_rows"],
                        error_rows=payload["error_rows"],
                        matched_rows=payload["matched_rows"],
                        new_rows=payload["new_rows"],
                    )
                    if cursor.rowcount == 0:
                        connection.rollback()
                        return None
                connection.commit()
                return self.get_import(import_id)
        except oracledb.Error as exc:
            raise OracleRepositoryError("Biometric import update failed") from exc

    def cancel_import(self, import_id: int) -> dict[str, Any] | None:
        """Cancel an import and atomically revert all data produced by it."""
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM attendance_day WHERE biometric_import_id = :id",
                        id=import_id,
                    )
                    cursor.execute(
                        """
                        DELETE FROM inconsistency
                        WHERE mark_id IN (
                            SELECT id FROM biometric_mark
                            WHERE biometric_import_id = :id
                        )
                        """,
                        id=import_id,
                    )
                    cursor.execute(
                        "DELETE FROM biometric_mark WHERE biometric_import_id = :id",
                        id=import_id,
                    )
                    cursor.execute(
                        "UPDATE biometric_import SET status = 'cancelled' WHERE id = :id",
                        id=import_id,
                    )
                    if cursor.rowcount == 0:
                        connection.rollback()
                        return None
                connection.commit()
            return self.get_import(import_id)
        except oracledb.Error as exc:
            raise OracleRepositoryError(
                "Biometric import cancellation failed"
            ) from exc

    def insert_mark(
        self,
        *,
        staff_member_id: int,
        biometric_import_id: int,
        marked_at: datetime,
        mark_type: str,
        status: str = "valid",
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO biometric_mark (
                staff_member_id, biometric_import_id, marked_at, mark_type, status
            ) VALUES (
                :staff_member_id, :biometric_import_id, :marked_at, :mark_type, :status
            )
            RETURNING id INTO :id
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    new_id = cursor.var(oracledb.NUMBER)
                    cursor.execute(
                        sql,
                        id=new_id,
                        staff_member_id=staff_member_id,
                        biometric_import_id=biometric_import_id,
                        marked_at=marked_at,
                        mark_type=mark_type,
                        status=status,
                    )
                connection.commit()
                return {
                    "id": int(new_id.getvalue()[0]),
                    "staff_member_id": staff_member_id,
                    "biometric_import_id": biometric_import_id,
                    "marked_at": marked_at.isoformat(sep=" "),
                    "mark_type": mark_type,
                    "status": status,
                }
        except oracledb.Error as exc:
            raise OracleRepositoryError("Biometric mark insert failed") from exc

    def insert_marks(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        sql = """
            INSERT INTO biometric_mark (
                staff_member_id, biometric_import_id, marked_at, mark_type, status
            ) VALUES (
                :staff_member_id, :biometric_import_id, :marked_at, :mark_type, :status
            )
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.executemany(sql, rows)
                connection.commit()
        except oracledb.Error as exc:
            raise OracleRepositoryError("Biometric mark bulk insert failed") from exc

    def list_marks(self) -> list[dict[str, Any]]:
        sql = """
            SELECT id, staff_member_id, biometric_import_id, marked_at,
                   mark_type, status
            FROM biometric_mark
            ORDER BY marked_at DESC, id DESC
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                    return [
                        {
                            "id": int(row[0]),
                            "staff_member_id": int(row[1]),
                            "biometric_import_id": (
                                int(row[2]) if row[2] is not None else None
                            ),
                            "marked_at": oracle_timestamp(row[3]),
                            "mark_type": row[4],
                            "status": row[5],
                        }
                        for row in cursor.fetchall()
                    ]
        except oracledb.Error as exc:
            raise OracleRepositoryError("Biometric mark list failed") from exc

    def _import_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "file_name": data["file_name"],
            "file_path": data.get("file_path"),
            "user_account_id": data.get("user_account_id"),
            "status": data["status"],
            "period_start": (
                date.fromisoformat(data["period_start"])
                if data.get("period_start")
                else None
            ),
            "period_end": (
                date.fromisoformat(data["period_end"])
                if data.get("period_end")
                else None
            ),
            "total_rows": data.get("total_rows", 0),
            "ok_rows": data.get("ok_rows", 0),
            "error_rows": data.get("error_rows", 0),
            "matched_rows": data.get("matched_rows", 0),
            "new_rows": data.get("new_rows", 0),
        }

    def _import_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": int(row[0]),
            "file_name": row[1],
            "file_path": row[2],
            "uploaded_at": oracle_timestamp(row[3]),
            "user_account_id": int(row[4]) if row[4] is not None else None,
            "status": row[5],
            "period_start": oracle_date(row[6]),
            "period_end": oracle_date(row[7]),
            "total_rows": int(row[8] or 0),
            "ok_rows": int(row[9] or 0),
            "error_rows": int(row[10] or 0),
            "matched_rows": int(row[11] or 0),
            "new_rows": int(row[12] or 0),
        }


biometric_repository = BiometricRepository()
