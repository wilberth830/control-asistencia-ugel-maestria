"""Oracle connection helpers."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from threading import Lock
from typing import Any

import oracledb

from app.core.config import settings


class OracleRepositoryError(RuntimeError):
    """Raised when Oracle cannot be used by a repository."""


_pool: Any = None
_pool_lock = Lock()


def _validate_oracle_settings() -> None:
    if (
        not settings.oracle_user
        or not settings.oracle_password
        or not settings.oracle_dsn
    ):
        raise OracleRepositoryError("Oracle connection settings are incomplete")


def _oracle_pool():
    global _pool

    _validate_oracle_settings()
    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is None:
            try:
                _pool = oracledb.create_pool(
                    user=settings.oracle_user,
                    password=settings.oracle_password,
                    dsn=settings.oracle_dsn,
                    min=1,
                    max=5,
                    increment=1,
                    ping_interval=60,
                )
            except oracledb.Error as exc:
                raise OracleRepositoryError("Oracle pool creation failed") from exc
    return _pool


@contextmanager
def oracle_connection() -> Iterator[oracledb.Connection]:
    try:
        connection = _oracle_pool().acquire()
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
