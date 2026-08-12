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
        biometric_import_id: int | None = None,
        attendance_date: date,
        status: str,
        late_minutes: int,
        justification_id: int | None,
    ) -> dict[str, Any]:
        sql = """
            MERGE INTO attendance_day target
            USING (
                SELECT :staff_member_id AS staff_member_id,
                       :biometric_import_id AS biometric_import_id,
                       :attendance_date AS attendance_date
                FROM dual
            ) source
            ON (
                target.staff_member_id = source.staff_member_id
                AND (
                    target.biometric_import_id = source.biometric_import_id
                    OR (
                        target.biometric_import_id IS NULL
                        AND source.biometric_import_id IS NULL
                    )
                )
                AND target.attendance_date = source.attendance_date
            )
            WHEN MATCHED THEN UPDATE SET
                target.status = :status,
                target.late_minutes = :late_minutes,
                target.justification_id = :justification_id
            WHEN NOT MATCHED THEN INSERT (
                staff_member_id, biometric_import_id, attendance_date, status,
                late_minutes, justification_id
            ) VALUES (
                :staff_member_id, :biometric_import_id, :attendance_date, :status,
                :late_minutes, :justification_id
            )
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        sql,
                        staff_member_id=staff_member_id,
                        biometric_import_id=biometric_import_id,
                        attendance_date=attendance_date,
                        status=status,
                        late_minutes=late_minutes,
                        justification_id=justification_id,
                    )
                connection.commit()
                return self.get_by_staff_date(
                    staff_member_id, attendance_date, biometric_import_id
                )
        except oracledb.Error as exc:
            raise OracleRepositoryError("Attendance upsert failed") from exc

    def get_by_staff_date(
        self,
        staff_member_id: int,
        attendance_date: date,
        biometric_import_id: int | None = None,
    ) -> dict[str, Any]:
        sql = """
            SELECT id, staff_member_id, biometric_import_id, attendance_date, status,
                   late_minutes, justification_id
            FROM attendance_day
            WHERE staff_member_id = :staff_member_id
              AND attendance_date = :attendance_date
              AND (
                  biometric_import_id = :biometric_import_id
                  OR (
                      biometric_import_id IS NULL
                      AND :biometric_import_id IS NULL
                  )
              )
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        sql,
                        staff_member_id=staff_member_id,
                        attendance_date=attendance_date,
                        biometric_import_id=biometric_import_id,
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
            SELECT id, staff_member_id, biometric_import_id, attendance_date, status,
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

    def list_by_import(
        self, import_id: int, *, month: int | None = None, year: int | None = None
    ) -> list[dict[str, Any]]:
        mark_period_filter = ""
        attendance_period_filter = ""
        params: dict[str, Any] = {"import_id": import_id}
        if month and year:
            start_date = date(year, month, 1)
            end_date = date(year + int(month == 12), 1 if month == 12 else month + 1, 1)
            mark_period_filter = """
              AND bm.marked_at >= :start_date
              AND bm.marked_at < :end_date
            """
            attendance_period_filter = """
              AND ad.attendance_date >= :start_date
              AND ad.attendance_date < :end_date
            """
            params.update({"start_date": start_date, "end_date": end_date})
        sql = """
            WITH mark_days AS (
                SELECT
                    bm.staff_member_id,
                    bm.biometric_import_id,
                    TRUNC(bm.marked_at) AS attendance_date,
                    MIN(COALESCE(scoped.id, generic.id)) AS attendance_id,
                    MAX(COALESCE(scoped.status, generic.status, 'present'))
                        KEEP (DENSE_RANK LAST ORDER BY bm.marked_at) AS status,
                    MAX(COALESCE(scoped.late_minutes, generic.late_minutes, 0))
                        AS late_minutes,
                    MAX(COALESCE(scoped.justification_id, generic.justification_id))
                        AS justification_id
                FROM biometric_mark bm
                LEFT JOIN attendance_day scoped
                  ON scoped.staff_member_id = bm.staff_member_id
                 AND scoped.attendance_date = TRUNC(bm.marked_at)
                 AND scoped.biometric_import_id = bm.biometric_import_id
                LEFT JOIN attendance_day generic
                  ON generic.staff_member_id = bm.staff_member_id
                 AND generic.attendance_date = TRUNC(bm.marked_at)
                 AND generic.biometric_import_id IS NULL
                WHERE bm.biometric_import_id = :import_id
                {mark_period_filter}
                GROUP BY bm.staff_member_id, bm.biometric_import_id, TRUNC(bm.marked_at)
            ),
            manual_days AS (
                SELECT
                    ad.id,
                    ad.staff_member_id,
                    ad.biometric_import_id,
                    ad.attendance_date,
                    ad.status,
                    ad.late_minutes,
                    ad.justification_id
                FROM attendance_day ad
                WHERE ad.biometric_import_id = :import_id
                {attendance_period_filter}
                  AND NOT EXISTS (
                      SELECT 1
                      FROM mark_days md
                      WHERE md.staff_member_id = ad.staff_member_id
                        AND md.biometric_import_id = ad.biometric_import_id
                        AND md.attendance_date = ad.attendance_date
                  )
            )
            SELECT
                COALESCE(
                    attendance_id,
                    -ROW_NUMBER() OVER (ORDER BY attendance_date, staff_member_id)
                ) AS id,
                staff_member_id,
                biometric_import_id,
                attendance_date,
                status,
                late_minutes,
                justification_id
            FROM mark_days
            UNION ALL
            SELECT
                id,
                staff_member_id,
                biometric_import_id,
                attendance_date,
                status,
                late_minutes,
                justification_id
            FROM manual_days
            ORDER BY attendance_date, staff_member_id
        """.format(
            mark_period_filter=mark_period_filter,
            attendance_period_filter=attendance_period_filter,
        )
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, **params)
                    return [self._row(row) for row in cursor.fetchall()]
        except oracledb.Error as exc:
            raise OracleRepositoryError("Attendance import list failed") from exc

    def bulk_upsert(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        sql = """
            MERGE INTO attendance_day target
            USING (
                SELECT :staff_member_id AS staff_member_id,
                       :biometric_import_id AS biometric_import_id,
                       :attendance_date AS attendance_date
                FROM dual
            ) source
            ON (
                target.staff_member_id = source.staff_member_id
                AND target.biometric_import_id = source.biometric_import_id
                AND target.attendance_date = source.attendance_date
            )
            WHEN MATCHED THEN UPDATE SET
                target.status = :status,
                target.late_minutes = :late_minutes,
                target.justification_id = :justification_id
            WHEN NOT MATCHED THEN INSERT (
                staff_member_id, biometric_import_id, attendance_date, status,
                late_minutes, justification_id
            ) VALUES (
                :staff_member_id, :biometric_import_id, :attendance_date, :status,
                :late_minutes, :justification_id
            )
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.executemany(sql, rows)
                connection.commit()
        except oracledb.Error as exc:
            raise OracleRepositoryError("Attendance bulk upsert failed") from exc

    def clear_justification(self, justification_id: int) -> list[dict[str, Any]]:
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE attendance_day
                           SET status = CASE
                                   WHEN EXISTS (
                                       SELECT 1
                                       FROM biometric_mark bm
                                       WHERE bm.staff_member_id = attendance_day.staff_member_id
                                         AND TRUNC(bm.marked_at) = attendance_day.attendance_date
                                         AND (
                                             attendance_day.biometric_import_id IS NULL
                                             OR bm.biometric_import_id = attendance_day.biometric_import_id
                                         )
                                   ) THEN 'present'
                                   ELSE 'absent'
                               END,
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

    def apply_justification(
        self,
        *,
        justification_id: int,
        staff_member_id: int,
        start_date: date,
        end_date: date,
        status: str,
    ) -> int:
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE attendance_day
                           SET status = :status,
                               late_minutes = 0,
                               justification_id = :justification_id
                         WHERE staff_member_id = :staff_member_id
                           AND attendance_date >= :start_date
                           AND attendance_date <= :end_date
                           AND status = 'absent'
                           AND justification_id IS NULL
                        """,
                        status=status,
                        justification_id=justification_id,
                        staff_member_id=staff_member_id,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    changed_count = cursor.rowcount
                connection.commit()
                return changed_count
        except oracledb.Error as exc:
            raise OracleRepositoryError(
                "Attendance justification apply failed"
            ) from exc

    def _row(self, row: Any) -> dict[str, Any]:
        return {
            "id": int(row[0]),
            "staff_member_id": int(row[1]),
            "biometric_import_id": int(row[2]) if row[2] is not None else None,
            "attendance_date": oracle_date(row[3]),
            "status": row[4],
            "late_minutes": int(row[5] or 0),
            "justification_id": int(row[6]) if row[6] is not None else None,
        }


attendance_day_repository = AttendanceDayRepository()
