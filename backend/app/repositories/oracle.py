"""Oracle connection helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import oracledb

from app.core.config import settings


class OracleRepositoryError(RuntimeError):
    """Raised when Oracle cannot be used by a repository."""


def _validate_oracle_settings() -> None:
    if (
        not settings.oracle_user
        or not settings.oracle_password
        or not settings.oracle_dsn
    ):
        raise OracleRepositoryError("Oracle connection settings are incomplete")


@contextmanager
def oracle_connection() -> Iterator[oracledb.Connection]:
    _validate_oracle_settings()
    try:
        connection = oracledb.connect(
            user=settings.oracle_user,
            password=settings.oracle_password,
            dsn=settings.oracle_dsn,
        )
    except oracledb.Error as exc:
        raise OracleRepositoryError("Oracle connection failed") from exc

    try:
        yield connection
    finally:
        connection.close()
