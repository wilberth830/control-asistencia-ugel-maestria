from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.repositories.attendance_day_repository import attendance_day_repository
from app.services.attendance_service import AttendanceService, attendance_service
from app.services.justification_service import (
    JustificationService,
    justification_service,
)


@pytest.fixture(autouse=True)
def reset_attendance_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "oracle_user", "")
    monkeypatch.setattr(settings, "oracle_password", "")
    monkeypatch.setattr(settings, "oracle_dsn", "")
    monkeypatch.setattr(settings, "app_allow_memory_data", True)
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

    for attendance_date, status in [
        ("2026-07-10", "absent"),
        ("2026-07-11", "present"),
        ("2026-07-12", "absent"),
    ]:
        response = client.put(
            "/api/v1/attendance-records/days",
            json={
                "staff_member_id": 1,
                "attendance_date": attendance_date,
                "status": status,
                "late_minutes": 0,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    create_response = client.post(
        "/api/v1/justifications",
        data={
            "staff_member_id": "1",
            "start_date": "2026-07-10",
            "end_date": "2026-07-12",
            "norm_code": "LG",
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
    assert [day["status"] for day in days] == ["leave", "present", "leave"]
    assert [day["justification_id"] for day in days] == [item["id"], None, item["id"]]


def test_cancel_justification_reverts_attendance_days(
    auth_headers: dict[str, str],
) -> None:
    client = TestClient(app)
    attendance_response = client.put(
        "/api/v1/attendance-records/days",
        json={
            "staff_member_id": 1,
            "attendance_date": "2026-07-10",
            "status": "absent",
            "late_minutes": 0,
        },
        headers=auth_headers,
    )
    assert attendance_response.status_code == 200

    item = client.post(
        "/api/v1/justifications",
        data={
            "staff_member_id": "1",
            "start_date": "2026-07-10",
            "end_date": "2026-07-10",
            "norm_code": "P",
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


def test_create_justification_requires_a_pending_absence(
    auth_headers: dict[str, str],
) -> None:
    response = TestClient(app).post(
        "/api/v1/justifications",
        data={
            "staff_member_id": "1",
            "start_date": "2026-07-10",
            "end_date": "2026-07-10",
            "norm_code": "J",
            "with_pay": "N",
            "reason": "Sustento presentado",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "no_absences_in_range"}
    assert justification_service.list() == []


@pytest.mark.parametrize(
    ("norm_code", "expected_status", "expected_with_pay"),
    [
        ("LG", "leave", "Y"),
        ("LS", "unpaid_leave", "N"),
        ("P", "permission", "N"),
        ("J", "justified", "N"),
        ("H", "strike", "N"),
        ("F", "holiday", "N"),
    ],
)
def test_norm_code_determines_attendance_status_and_pay(
    auth_headers: dict[str, str],
    norm_code: str,
    expected_status: str,
    expected_with_pay: str,
) -> None:
    client = TestClient(app)
    attendance_date = "2026-07-15"
    assert client.put(
        "/api/v1/attendance-records/days",
        json={
            "staff_member_id": 1,
            "attendance_date": attendance_date,
            "status": "absent",
            "late_minutes": 0,
        },
        headers=auth_headers,
    ).status_code == 200

    response = client.post(
        "/api/v1/justifications",
        data={
            "staff_member_id": "1",
            "start_date": attendance_date,
            "end_date": attendance_date,
            "norm_code": norm_code,
            "with_pay": "N" if expected_with_pay == "Y" else "Y",
            "reason": "Aplicación de norma",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["with_pay"] == expected_with_pay
    day = client.get(
        "/api/v1/attendance-records",
        params={"month": 7, "year": 2026, "staff_member_id": 1},
        headers=auth_headers,
    ).json()[0]
    assert day["status"] == expected_status


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


@pytest.mark.parametrize(
    "status",
    [
        "no_record",
        "present",
        "late",
        "absent",
        "justified",
        "unpaid_leave",
        "permission",
        "strike",
        "holiday",
    ],
)
def test_manual_attendance_statuses_and_late_minutes(
    monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    def upsert_stub(**data):
        return {
            "id": 1,
            **data,
            "attendance_date": data["attendance_date"].isoformat(),
        }

    monkeypatch.setattr(attendance_day_repository, "upsert", upsert_stub)
    row = AttendanceService().upsert_day(
        staff_member_id=1,
        attendance_date="2026-07-03",
        status=status,
        late_minutes=12,
    )

    assert row["status"] == status
    assert row["late_minutes"] == (12 if status == "late" else 0)


@pytest.mark.parametrize(
    ("norm_code", "expected_status"),
    [
        ("LG", "leave"),
        ("LS", "unpaid_leave"),
        ("P", "permission"),
        ("J", "justified"),
        ("H", "strike"),
        ("F", "holiday"),
    ],
)
def test_norm_codes_map_to_distinct_attendance_statuses(
    norm_code: str, expected_status: str
) -> None:
    assert JustificationService()._attendance_status(norm_code) == expected_status
