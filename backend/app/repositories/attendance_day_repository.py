"""Oracle repository for attendance_day."""

from __future__ import annotations

from datetime import date
from typing import Any

import oracledb

from app.repositories.oracle import (
    OracleRepositoryError,
    oracle_connection,
    oracle_date,
)


class AttendanceDayRepository:
    def upsert(
        self,
        *,
        staff_member_id: int,
        attendance_date: date,
        status: str,
        late_minutes: int,
        justification_id: int | None,
    ) -> dict[str, Any]:
        sql = """
            MERGE INTO attendance_day target
            USING (
                SELECT :staff_member_id AS staff_member_id,
                       :attendance_date AS attendance_date
                FROM dual
            ) source
            ON (
                target.staff_member_id = source.staff_member_id
                AND target.attendance_date = source.attendance_date
            )
            WHEN MATCHED THEN UPDATE SET
                target.status = :status,
                target.late_minutes = :late_minutes,
                target.justification_id = :justification_id
            WHEN NOT MATCHED THEN INSERT (
                staff_member_id, attendance_date, status, late_minutes,
                justification_id
            ) VALUES (
                :staff_member_id, :attendance_date, :status, :late_minutes,
                :justification_id
            )
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        sql,
                        staff_member_id=staff_member_id,
                        attendance_date=attendance_date,
                        status=status,
                        late_minutes=late_minutes,
                        justification_id=justification_id,
                    )
                connection.commit()
                return self.get_by_staff_date(staff_member_id, attendance_date)
        except oracledb.Error as exc:
            raise OracleRepositoryError("Attendance upsert failed") from exc

    def get_by_staff_date(
        self, staff_member_id: int, attendance_date: date
    ) -> dict[str, Any]:
        sql = """
            SELECT id, staff_member_id, attendance_date, status,
                   late_minutes, justification_id
            FROM attendance_day
            WHERE staff_member_id = :staff_member_id
              AND attendance_date = :attendance_date
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        sql,
                        staff_member_id=staff_member_id,
                        attendance_date=attendance_date,
                    )
                    row = cursor.fetchone()
                    if row is None:
                        raise OracleRepositoryError("Attendance row was not found")
                    return self._row(row)
        except oracledb.Error as exc:
            raise OracleRepositoryError("Attendance lookup failed") from exc

    def list_month(
        self, *, month: int, year: int, staff_member_id: int | None = None
    ) -> list[dict[str, Any]]:
        start_date = date(year, month, 1)
        end_date = date(year + int(month == 12), 1 if month == 12 else month + 1, 1)
        sql = """
            SELECT id, staff_member_id, attendance_date, status,
                   late_minutes, justification_id
            FROM attendance_day
            WHERE attendance_date >= :start_date
              AND attendance_date < :end_date
              AND (:staff_member_id IS NULL OR staff_member_id = :staff_member_id)
            ORDER BY attendance_date, staff_member_id
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        sql,
                        start_date=start_date,
                        end_date=end_date,
                        staff_member_id=staff_member_id,
                    )
                    return [self._row(row) for row in cursor.fetchall()]
        except oracledb.Error as exc:
            raise OracleRepositoryError("Attendance list failed") from exc

    def list_by_import(self, import_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                MIN(ad.id) AS id,
                ad.staff_member_id,
                ad.attendance_date,
                MAX(ad.status) KEEP (DENSE_RANK LAST ORDER BY bm.marked_at) AS status,
                MAX(ad.late_minutes) AS late_minutes,
                MAX(ad.justification_id) AS justification_id
            FROM biometric_mark bm
            JOIN attendance_day ad
              ON ad.staff_member_id = bm.staff_member_id
             AND ad.attendance_date = TRUNC(bm.marked_at)
            WHERE bm.biometric_import_id = :import_id
            GROUP BY ad.staff_member_id, ad.attendance_date
            ORDER BY ad.attendance_date, ad.staff_member_id
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, import_id=import_id)
                    return [self._row(row) for row in cursor.fetchall()]
        except oracledb.Error as exc:
            raise OracleRepositoryError("Attendance import list failed") from exc

    def clear_justification(self, justification_id: int) -> list[dict[str, Any]]:
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE attendance_day
                           SET status = 'absent',
                               late_minutes = 0,
                               justification_id = NULL
                         WHERE justification_id = :justification_id
                        """,
                        justification_id=justification_id,
                    )
                connection.commit()
            return []
        except oracledb.Error as exc:
            raise OracleRepositoryError(
                "Attendance justification clear failed"
            ) from exc

    def _row(self, row: Any) -> dict[str, Any]:
        return {
            "id": int(row[0]),
            "staff_member_id": int(row[1]),
            "attendance_date": oracle_date(row[2]),
            "status": row[3],
            "late_minutes": int(row[4] or 0),
            "justification_id": int(row[5]) if row[5] is not None else None,
        }


attendance_day_repository = AttendanceDayRepository()
