from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.services.auth_service as auth_service_module
import app.services.session_store as session_store_module
from app.core.security import hash_password
from app.repositories.oracle import OracleRepositoryError
from tests.conftest import FakeRedis


def stub_user(username: str) -> dict | None:
    if username != "director.demo":
        return None
    return {
        "id": 1,
        "username": "director.demo",
        "password_hash": hash_password("Demo12345"),
        "role_name": "Director",
        "is_active": "Y",
    }


def test_health_is_public() -> None:
    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_current_and_logout_use_redis(
    fake_redis: FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        auth_service_module.user_account_repository,
        "find_active_by_username",
        stub_user,
    )
    client = TestClient(app)

    login_response = client.post(
        "/api/v1/auth/sessions",
        json={"username": "director.demo", "password": "Demo12345"},
    )

    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["username"] == "director.demo"
    assert payload["role"] == "Director"
    assert payload["access"]["operations"]["ver_dashboard"] is True
    assert fake_redis.values[f"session:{payload['token']}"]

    current_response = client.get(
        "/api/v1/auth/sessions/current",
        headers={"Authorization": f"Bearer {payload['token']}"},
    )

    assert current_response.status_code == 200
    assert current_response.json()["access"]["modules"]

    logout_response = client.delete(
        "/api/v1/auth/sessions/current",
        headers={"Authorization": f"Bearer {payload['token']}"},
    )

    assert logout_response.status_code == 200
    assert logout_response.json() == {"message": "Session closed"}
    assert f"session:{payload['token']}" not in fake_redis.values


def test_invalid_credentials_do_not_create_session(
    fake_redis: FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        auth_service_module.user_account_repository,
        "find_active_by_username",
        stub_user,
    )
    response = TestClient(app).post(
        "/api/v1/auth/sessions",
        json={"username": "director.demo", "password": "bad-password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}
    assert fake_redis.values == {}


def test_redis_unavailable_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth_service_module.user_account_repository,
        "find_active_by_username",
        stub_user,
    )
    store = session_store_module.session_store
    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "USE_REDIS", True)
    monkeypatch.setattr(session_store_module, "redis", None)
    monkeypatch.setattr(
        session_store_module.settings, "app_allow_memory_session", False
    )

    response = TestClient(app).post(
        "/api/v1/auth/sessions",
        json={"username": "director.demo", "password": "Demo12345"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Session service unavailable"}


def test_memory_session_does_not_retry_redis_on_every_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = session_store_module.session_store
    calls = {"count": 0}

    class BrokenRedis:
        @staticmethod
        def from_url(*args, **kwargs):
            calls["count"] += 1
            raise RuntimeError("redis down")

    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(store, "_redis_unavailable_until", 0.0)
    monkeypatch.setattr(session_store_module, "redis", BrokenRedis)
    monkeypatch.setattr(store, "USE_REDIS", True)
    monkeypatch.setattr(session_store_module.settings, "app_allow_memory_session", True)
    monkeypatch.setattr(store, "REDIS_RETRY_SECONDS", 30)

    store.save("token-1", {"user_id": 1}, 60)
    assert store.get("token-1") == {"user_id": 1}
    assert store.get("token-1") == {"user_id": 1}
    assert calls["count"] == 1


def test_memory_session_skips_redis_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = session_store_module.session_store

    class UnexpectedRedis:
        @staticmethod
        def from_url(*args, **kwargs):
            raise AssertionError("Redis should not be used")

    monkeypatch.setattr(store, "_client", None)
    monkeypatch.setattr(session_store_module, "redis", UnexpectedRedis)
    monkeypatch.setattr(store, "USE_REDIS", False)
    monkeypatch.setattr(session_store_module.settings, "app_allow_memory_session", True)

    store.save("token-disabled", {"user_id": 1}, 60)
    assert store.get("token-disabled") == {"user_id": 1}


def test_oracle_unavailable_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_oracle_error(username: str):
        raise OracleRepositoryError("Oracle unavailable")

    monkeypatch.setattr(
        auth_service_module.user_account_repository,
        "find_active_by_username",
        raise_oracle_error,
    )

    response = TestClient(app).post(
        "/api/v1/auth/sessions",
        json={"username": "director.demo", "password": "Demo12345"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication store unavailable"}
