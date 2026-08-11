"""Oracle repository for institution."""

from __future__ import annotations

from typing import Any

import oracledb

from app.repositories.oracle import OracleRepositoryError, oracle_connection


class InstitutionRepository:
    def get_active(self) -> dict[str, Any] | None:
        sql = """
            SELECT id, ugel, school_name, modular_code, education_level,
                   shift_name, is_active
            FROM institution
            WHERE is_active = 'Y'
            ORDER BY id
            FETCH FIRST 1 ROWS ONLY
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                    row = cursor.fetchone()
        except oracledb.Error as exc:
            raise OracleRepositoryError("Institution lookup failed") from exc

        if row is None:
            return None

        return {
            "id": int(row[0]),
            "ugel": row[1],
            "school_name": row[2],
            "modular_code": row[3],
            "education_level": row[4],
            "shift_name": row[5],
            "is_active": row[6],
        }


institution_repository = InstitutionRepository()
