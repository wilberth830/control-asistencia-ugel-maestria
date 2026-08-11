from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _test_user(username: str) -> dict | None:
    from app.core.security import hash_password

    if username != "director.demo":
        return None
    return {
        "id": 1,
        "username": "director.demo",
        "password_hash": hash_password("Demo12345"),
        "role_name": "Director",
        "is_active": "Y",
    }


@pytest.fixture(autouse=True)
def oracle_user_lookup_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.auth_service as auth_service_module

    monkeypatch.setattr(
        auth_service_module.user_account_repository,
        "find_active_by_username",
        _test_user,
    )


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def ping(self) -> bool:
        return True

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        assert ttl_seconds > 0
        self.values[key] = value

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def delete(self, key: str) -> None:
        self.values.pop(key, None)


@pytest.fixture()
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    import app.services.session_store as session_store_module

    client = FakeRedis()
    store = session_store_module.session_store
    monkeypatch.setattr(store, "_client", client)
    return client
