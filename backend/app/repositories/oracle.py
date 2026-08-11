"""Oracle connection helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
import json
from typing import Any

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


def oracle_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def oracle_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    return str(value)


def to_json_clob(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)
