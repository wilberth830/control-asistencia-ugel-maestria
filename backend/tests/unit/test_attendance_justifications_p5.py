from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.attendance_service import attendance_service
from app.services.justification_service import justification_service


@pytest.fixture(autouse=True)
def reset_attendance_data() -> None:
    attendance_service.reset()
    justification_service.reset()


@pytest.fixture()
def auth_headers(fake_redis) -> dict[str, str]:
    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/sessions",
        json={"username": "director.demo", "password": "Demo12345"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_upsert_attendance_day_and_list_month(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)

    update_response = client.put(
        "/api/v1/attendance-records/days",
        json={
            "staff_member_id": 1,
            "attendance_date": "2026-07-03",
            "status": "late",
            "late_minutes": 12,
        },
        headers=auth_headers,
    )

    assert update_response.status_code == 200
    assert update_response.json()["id"] == 1

    list_response = client.get(
        "/api/v1/attendance-records",
        params={"month": 7, "year": 2026, "staff_member_id": 1},
        headers=auth_headers,
    )

    assert list_response.status_code == 200
    assert list_response.json()[0]["status"] == "late"


def test_update_attendance_is_scoped_by_import(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)

    first_response = client.put(
        "/api/v1/attendance-records/days",
        json={
            "staff_member_id": 1,
            "biometric_import_id": 10,
            "attendance_date": "2026-07-03",
            "status": "late",
            "late_minutes": 8,
        },
        headers=auth_headers,
    )
    second_response = client.put(
        "/api/v1/attendance-records/days",
        json={
            "staff_member_id": 1,
            "biometric_import_id": 20,
            "attendance_date": "2026-07-03",
            "status": "present",
            "late_minutes": 0,
        },
        headers=auth_headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    update_first_response = client.put(
        "/api/v1/attendance-records/days",
        json={
            "staff_member_id": 1,
            "biometric_import_id": 10,
            "attendance_date": "2026-07-03",
            "status": "absent",
            "late_minutes": 0,
        },
        headers=auth_headers,
    )

    assert update_first_response.status_code == 200
    assert update_first_response.json()["id"] == first_response.json()["id"]

    first_list = client.get(
        "/api/v1/attendance-records",
        params={"month": 7, "year": 2026, "import_id": 10},
        headers=auth_headers,
    ).json()
    second_list = client.get(
        "/api/v1/attendance-records",
        params={"month": 7, "year": 2026, "import_id": 20},
        headers=auth_headers,
    ).json()

    assert first_list[0]["status"] == "absent"
    assert second_list[0]["status"] == "present"


def test_create_justification_applies_attendance_range(
    auth_headers: dict[str, str],
) -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/justifications",
        data={
            "staff_member_id": "1",
            "start_date": "2026-07-10",
            "end_date": "2026-07-12",
            "norm_code": "LIC",
            "with_pay": "Y",
            "reason": "Licencia aprobada",
        },
        headers=auth_headers,
    )

    assert create_response.status_code == 201
    item = create_response.json()
    assert item["status"] == "active"

    attendance_response = client.get(
        "/api/v1/attendance-records",
        params={"month": 7, "year": 2026, "staff_member_id": 1},
        headers=auth_headers,
    )

    days = attendance_response.json()
    assert [day["attendance_date"] for day in days] == [
        "2026-07-10",
        "2026-07-11",
        "2026-07-12",
    ]
    assert all(day["status"] == "justified" for day in days)
    assert all(day["justification_id"] == item["id"] for day in days)


def test_cancel_justification_reverts_attendance_days(
    auth_headers: dict[str, str],
) -> None:
    client = TestClient(app)
    item = client.post(
        "/api/v1/justifications",
        data={
            "staff_member_id": "1",
            "start_date": "2026-07-10",
            "end_date": "2026-07-10",
            "norm_code": "PER",
            "with_pay": "N",
        },
        headers=auth_headers,
    ).json()

    cancel_response = client.post(
        f"/api/v1/justifications/{item['id']}/cancellation",
        json={"reason": "Sustento inválido"},
        headers=auth_headers,
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    attendance_response = client.get(
        "/api/v1/attendance-records",
        params={"month": 7, "year": 2026, "staff_member_id": 1},
        headers=auth_headers,
    )

    assert attendance_response.json()[0]["status"] == "absent"
    assert attendance_response.json()[0]["justification_id"] is None


def test_invalid_attendance_status_returns_400(auth_headers: dict[str, str]) -> None:
    response = TestClient(app).put(
        "/api/v1/attendance-records/days",
        json={
            "staff_member_id": 1,
            "attendance_date": "2026-07-03",
            "status": "unknown",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid attendance day"}
