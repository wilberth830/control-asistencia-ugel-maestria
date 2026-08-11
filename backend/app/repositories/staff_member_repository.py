"""Oracle repository for staff_member."""

from __future__ import annotations

from typing import Any

import oracledb

from app.repositories.oracle import (
    OracleRepositoryError,
    oracle_connection,
    oracle_date,
)


class StaffMemberRepository:
    def list(
        self,
        *,
        q: str | None = None,
        is_active: str | None = None,
        job_title: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT id, dni, last_names, first_names, job_title,
                   employment_status, is_active, registered_at
            FROM staff_member
            WHERE (:is_active IS NULL OR is_active = :is_active)
              AND (:job_title IS NULL OR LOWER(job_title) = LOWER(:job_title))
              AND (
                  :q IS NULL
                  OR dni LIKE '%' || :q || '%'
                  OR LOWER(last_names) LIKE '%' || LOWER(:q) || '%'
                  OR LOWER(first_names) LIKE '%' || LOWER(:q) || '%'
              )
            ORDER BY last_names, first_names, id
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, q=q, is_active=is_active, job_title=job_title)
                    return [self._row(row) for row in cursor.fetchall()]
        except oracledb.Error as exc:
            raise OracleRepositoryError("Staff list failed") from exc

    def get(self, staff_member_id: int) -> dict[str, Any] | None:
        return self._get_by("id = :value", staff_member_id)

    def get_by_dni(self, dni: str) -> dict[str, Any] | None:
        return self._get_by("dni = :value", dni)

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = """
            INSERT INTO staff_member (
                dni, last_names, first_names, job_title, employment_status, is_active
            ) VALUES (
                :dni, :last_names, :first_names, :job_title,
                :employment_status, :is_active
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
        except oracledb.IntegrityError:
            raise
        except oracledb.Error as exc:
            raise OracleRepositoryError("Staff create failed") from exc

    def update(
        self, staff_member_id: int, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        sql = """
            UPDATE staff_member
               SET dni = :dni,
                   last_names = :last_names,
                   first_names = :first_names,
                   job_title = :job_title,
                   employment_status = :employment_status,
                   is_active = :is_active
             WHERE id = :id
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, id=staff_member_id, **self._payload(data))
                    if cursor.rowcount == 0:
                        connection.rollback()
                        return None
                connection.commit()
                return self.get(staff_member_id)
        except oracledb.IntegrityError:
            raise
        except oracledb.Error as exc:
            raise OracleRepositoryError("Staff update failed") from exc

    def deactivate(self, staff_member_id: int) -> dict[str, Any] | None:
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE staff_member SET is_active = 'N' WHERE id = :id",
                        id=staff_member_id,
                    )
                    if cursor.rowcount == 0:
                        connection.rollback()
                        return None
                connection.commit()
                return self.get(staff_member_id)
        except oracledb.Error as exc:
            raise OracleRepositoryError("Staff deactivate failed") from exc

    def _get_by(self, predicate: str, value: Any) -> dict[str, Any] | None:
        sql = f"""
            SELECT id, dni, last_names, first_names, job_title,
                   employment_status, is_active, registered_at
            FROM staff_member
            WHERE {predicate}
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, value=value)
                    row = cursor.fetchone()
                    return self._row(row) if row else None
        except oracledb.Error as exc:
            raise OracleRepositoryError("Staff lookup failed") from exc

    def _payload(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "dni": data["dni"],
            "last_names": data["last_names"],
            "first_names": data["first_names"],
            "job_title": data["job_title"],
            "employment_status": data.get("employment_status"),
            "is_active": data.get("is_active", "Y"),
        }

    def _row(self, row: Any) -> dict[str, Any]:
        return {
            "id": int(row[0]),
            "dni": row[1],
            "last_names": row[2],
            "first_names": row[3],
            "job_title": row[4],
            "employment_status": row[5],
            "is_active": row[6],
            "registered_at": oracle_date(row[7]),
        }


staff_member_repository = StaffMemberRepository()
