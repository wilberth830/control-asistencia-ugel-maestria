from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.attendance_service import attendance_service
from app.services.biometric_import_service import biometric_import_service
from app.services.justification_service import justification_service
from app.services.staff_member_service import staff_member_service

CSV_CONTENT = (
    "dni,last_names,first_names,marked_at,mark_type\n"
    "45678912,Quispe Mamani,Maria Elena,2026-07-01 07:42:00,entry\n"
)


@pytest.fixture(autouse=True)
def reset_demo_data() -> None:
    staff_member_service.reset_demo_data()
    attendance_service.reset()
    justification_service.reset()
    biometric_import_service.reset()


@pytest.fixture()
def auth_headers(fake_redis) -> dict[str, str]:
    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/sessions",
        json={"username": "director.demo", "password": "Demo12345"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def seed_attendance(client: TestClient, auth_headers: dict[str, str]) -> None:
    for payload in [
        {
            "staff_member_id": 1,
            "attendance_date": "2026-07-01",
            "status": "present",
        },
        {
            "staff_member_id": 1,
            "attendance_date": "2026-07-02",
            "status": "late",
            "late_minutes": 9,
        },
    ]:
        response = client.put(
            "/api/v1/attendance-records/days",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200


def test_annex_03_uses_attendance_day_and_institution_header(
    auth_headers: dict[str, str],
) -> None:
    client = TestClient(app)
    seed_attendance(client, auth_headers)

    response = client.get(
        "/api/v1/reports/annex-03",
        params={"month": 7, "year": 2026, "format": "json"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "attendance_day"
    assert payload["institution"]["modular_code"] == "1234567"
    assert payload["rows"][0]["dni"] == "45678912"
    assert [day["status"] for day in payload["rows"][0]["days"]] == ["present", "late"]


def test_annex_04_returns_month_totals(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    seed_attendance(client, auth_headers)

    response = client.get(
        "/api/v1/reports/annex-04",
        params={"month": 7, "year": 2026, "format": "json"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["staff_count"] == 1
    assert payload["totals"]["present"] == 1
    assert payload["totals"]["late"] == 1


def test_dashboard_indicators_use_attendance_staff_and_imports(
    auth_headers: dict[str, str],
) -> None:
    client = TestClient(app)
    seed_attendance(client, auth_headers)
    upload_response = client.post(
        "/api/v1/biometric-imports",
        files={"file": ("marks.csv", CSV_CONTENT, "text/csv")},
        headers=auth_headers,
    )
    assert upload_response.status_code == 201

    response = client.get(
        "/api/v1/dashboard/indicators",
        params={"month": 7, "year": 2026},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_uploaded_files"] == 1
    assert payload["active_staff_members"] == 3
    assert payload["mark_distribution"]["present"] == 1
    assert payload["mark_distribution"]["late"] == 1
    assert payload["recent_imports"][0]["file_name"].startswith("marks_")
    assert payload["recent_imports"][0]["file_name"].endswith(".csv")


def test_reports_reject_xlsx_in_json_step(auth_headers: dict[str, str]) -> None:
    response = TestClient(app).get(
        "/api/v1/reports/annex-03",
        params={"month": 7, "year": 2026, "format": "xlsx"},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Only JSON format is available"}


def test_annex_03_filters_by_import_id(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    upload_response = client.post(
        "/api/v1/biometric-imports",
        files={"file": ("marks.csv", CSV_CONTENT, "text/csv")},
        headers=auth_headers,
    )
    assert upload_response.status_code == 201
    import_id = upload_response.json()["id"]

    confirm_response = client.post(
        f"/api/v1/biometric-imports/{import_id}/confirmation",
        headers=auth_headers,
    )
    assert confirm_response.status_code == 200

    response = client.get(
        "/api/v1/reports/annex-03",
        params={"month": 7, "year": 2026, "format": "json", "import_id": import_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "attendance_day"
    assert payload["rows"]
    assert payload["rows"][0]["dni"] == "45678912"


def test_monthly_export_accepts_import_id(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    upload_response = client.post(
        "/api/v1/biometric-imports",
        files={"file": ("marks.csv", CSV_CONTENT, "text/csv")},
        headers=auth_headers,
    )
    assert upload_response.status_code == 201
    import_id = upload_response.json()["id"]

    confirm_response = client.post(
        f"/api/v1/biometric-imports/{import_id}/confirmation",
        headers=auth_headers,
    )
    assert confirm_response.status_code == 200

    response = client.get(
        "/api/v1/reports/monthly-export",
        params={"month": 7, "year": 2026, "import_id": import_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
