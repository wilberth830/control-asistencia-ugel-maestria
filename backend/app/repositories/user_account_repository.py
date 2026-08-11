"""Oracle repository for user_account."""

from __future__ import annotations

from typing import Any

import oracledb

from app.repositories.oracle import OracleRepositoryError, oracle_connection


class UserAccountRepository:
    def find_active_by_username(self, username: str) -> dict[str, Any] | None:
        sql = """
            SELECT
                id,
                username,
                password_hash,
                role_name,
                is_active
            FROM user_account
            WHERE username = :username
              AND is_active = 'Y'
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, username=username)
                    row = cursor.fetchone()
        except oracledb.Error as exc:
            raise OracleRepositoryError("User lookup failed") from exc

        if row is None:
            return None

        return {
            "id": row[0],
            "username": row[1],
            "password_hash": row[2],
            "role_name": row[3],
            "is_active": row[4],
        }


user_account_repository = UserAccountRepository()
