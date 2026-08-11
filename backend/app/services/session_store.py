"""TEC-D03 — Redis session store."""

from __future__ import annotations

import json
import time
from typing import Any, Optional

from app.core.config import settings

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore


class SessionStoreUnavailable(RuntimeError):
    """Raised when the external Redis session service is unavailable."""


class SessionStore:
    USE_REDIS = False
    REDIS_RETRY_SECONDS = 30
    REDIS_SOCKET_TIMEOUT_SECONDS = 0.2

    def __init__(self) -> None:
        self._client = None
        self._redis_unavailable_until = 0.0
        self._memory: dict[str, tuple[float, str]] = {}

    def _redis(self):
        if not self.USE_REDIS:
            raise SessionStoreUnavailable("Redis session service is disabled")
        if redis is None:
            raise SessionStoreUnavailable("Redis client library is not installed")
        now = time.time()
        if self._client is None and now < self._redis_unavailable_until:
            raise SessionStoreUnavailable("Redis session service is unavailable")
        if self._client is None:
            try:
                self._client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=self.REDIS_SOCKET_TIMEOUT_SECONDS,
                    socket_timeout=self.REDIS_SOCKET_TIMEOUT_SECONDS,
                    retry_on_timeout=False,
                )
                self._client.ping()
            except Exception as exc:
                self._client = None
                self._redis_unavailable_until = (
                    time.time() + self.REDIS_RETRY_SECONDS
                )
                raise SessionStoreUnavailable(
                    "Redis session service is unavailable"
                ) from exc
        try:
            self._client.ping()
        except Exception as exc:
            self._client = None
            self._redis_unavailable_until = time.time() + self.REDIS_RETRY_SECONDS
            raise SessionStoreUnavailable(
                "Redis session service is unavailable"
            ) from exc
        self._redis_unavailable_until = 0.0
        return self._client

    def _memory_save(self, token: str, raw: str, ttl_seconds: int) -> None:
        self._memory[token] = (time.time() + ttl_seconds, raw)

    def _memory_get(self, token: str) -> Optional[dict[str, Any]]:
        item = self._memory.get(token)
        if not item:
            return None
        expires_at, raw = item
        if time.time() > expires_at:
            self._memory.pop(token, None)
            return None
        return json.loads(raw)

    def save(self, token: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        raw = json.dumps(payload)
        try:
            client = self._redis()
            client.setex(f"session:{token}", ttl_seconds, raw)
        except SessionStoreUnavailable:
            if not settings.app_allow_memory_session:
                raise
            self._memory_save(token, raw, ttl_seconds)

    def get(self, token: str) -> Optional[dict[str, Any]]:
        try:
            client = self._redis()
            raw = client.get(f"session:{token}")
            if not raw:
                return None
            return json.loads(raw)
        except SessionStoreUnavailable:
            if not settings.app_allow_memory_session:
                raise
            return self._memory_get(token)

    def delete(self, token: str) -> None:
        try:
            client = self._redis()
            client.delete(f"session:{token}")
        except SessionStoreUnavailable:
            if not settings.app_allow_memory_session:
                raise
        self._memory.pop(token, None)


session_store = SessionStore()
