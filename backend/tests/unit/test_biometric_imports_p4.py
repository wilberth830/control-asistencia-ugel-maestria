from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.repositories.biometric_repository import biometric_repository
from app.services.ai_biometric_normalizer_service import AINormalizationResult
from app.services.attendance_service import attendance_service
from app.services.biometric_import_service import biometric_import_service
from app.services.staff_member_service import staff_member_service

CSV_CONTENT = (
    "dni,last_names,first_names,marked_at,mark_type\n"
    "45678912,Quispe Mamani,Maria Elena,2026-07-01 07:42:00,entry\n"
    "99999999,Nuevo Demo,Carga,2026-07-02 15:05:00,exit\n"
)

SPANISH_CSV_CONTENT = (
    "dni,apellidos,nombres,fecha_hora,tipo_marca\n"
    "45678912,Quispe Mamani,Maria Elena,2026-06-16 07:55:12,entrada\n"
    "45678912,Quispe Mamani,Maria Elena,2026-06-16 13:02:41,salida\n"
)

DUPLICATE_NEW_DNI_CSV = (
    "dni,last_names,first_names,marked_at,mark_type\n"
    "99990000,Nuevo Repetido,Carga,2026-07-01 07:42:00,entry\n"
    "99990000,Nuevo Repetido,Carga,2026-07-01 13:05:00,exit\n"
)

SEMICOLON_DAT_CONTENT = (
    "document;last_name;first_name;punch_time;direction\n"
    "45678912;Quispe Mamani;Maria Elena;2026-05-02 07:55:00;in\n"
    "45678912;Quispe Mamani;Maria Elena;2026-05-02 13:02:00;out\n"
)

UNKNOWN_BIOMETRIC_CONTENT = (
    "codigo|trabajador|momento|evento\n"
    "45678912|Maria Elena Quispe Mamani|2026/05/03 07:55:00|ENT\n"
)

BAT_CONTENT = rb"""
@echo off
> "%OUTFILE%" echo dni,apellidos,nombres,fecha_hora,tipo_marca
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-06-16 07:55:12,entrada
>> "%OUTFILE%" echo 99998888,Perez Soto,Juan Carlos,2026-06-16 08:10:00,entrada
"""


@pytest.fixture(autouse=True)
def reset_demo_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "oracle_user", "")
    monkeypatch.setattr(settings, "oracle_password", "")
    monkeypatch.setattr(settings, "oracle_dsn", "")
    monkeypatch.setattr(settings, "app_allow_memory_data", True)
    staff_member_service.reset_demo_data()
    biometric_import_service.reset()
    attendance_service.reset()


@pytest.fixture()
def auth_headers(fake_redis) -> dict[str, str]:
    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/sessions",
        json={"username": "director.demo", "password": "Demo12345"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def create_import(client: TestClient, auth_headers: dict[str, str]):
    return client.post(
        "/api/v1/biometric-imports",
        files={"file": ("marks.csv", CSV_CONTENT, "text/csv")},
        headers=auth_headers,
    )


def test_create_import_reads_csv_in_order_and_detects_period(
    auth_headers: dict[str, str],
) -> None:
    response = create_import(TestClient(app), auth_headers)

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "draft"
    assert payload["period_start"] == "2026-07-01"
    assert payload["period_end"] == "2026-07-02"
    assert payload["matched_rows"] == 1
    assert payload["new_rows"] == 1
    assert [row["order"] for row in payload["rows"]] == [1, 2]
    assert payload["rows"][0]["match"] == "matched"
    assert payload["rows"][1]["match"] == "new"


def test_create_import_accepts_spanish_biometric_csv(
    auth_headers: dict[str, str],
) -> None:
    response = TestClient(app).post(
        "/api/v1/biometric-imports",
        files={"file": ("marcas.csv", SPANISH_CSV_CONTENT, "text/csv")},
        headers=auth_headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["period_start"] == "2026-06-16"
    assert payload["period_end"] == "2026-06-16"
    assert payload["rows"][0]["mark_type"] == "entry"
    assert payload["rows"][1]["mark_type"] == "exit"


def test_create_import_accepts_batch_generator_file(
    auth_headers: dict[str, str],
) -> None:
    response = TestClient(app).post(
        "/api/v1/biometric-imports",
        files={
            "file": (
                "simular_marcas_biometricas.bat",
                BAT_CONTENT,
                "application/octet-stream",
            )
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["total_rows"] == 2
    assert payload["matched_rows"] == 1
    assert payload["new_rows"] == 1
    assert payload["rows"][1]["dni"] == "99998888"


def test_create_import_accepts_dat_with_device_aliases(
    auth_headers: dict[str, str],
) -> None:
    response = TestClient(app).post(
        "/api/v1/biometric-imports",
        files={"file": ("device.dat", SEMICOLON_DAT_CONTENT, "text/plain")},
        headers=auth_headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["total_rows"] == 2
    assert payload["rows"][0]["mark_type"] == "entry"
    assert payload["rows"][1]["mark_type"] == "exit"


def test_create_import_uses_ai_normalizer_when_required_fields_are_unknown(
    auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import biometric_import_service as import_service_module

    monkeypatch.setattr(
        import_service_module.ai_biometric_normalizer_service,
        "normalize_to_csv",
        lambda text: AINormalizationResult(
            csv_text=(
                "dni,apellidos,nombres,fecha_hora,tipo_marca\n"
                "45678912,Quispe Mamani,Maria Elena,2026-05-03 07:55:00,entrada\n"
            ),
            source="local_fallback",
        ),
    )

    response = TestClient(app).post(
        "/api/v1/biometric-imports",
        files={"file": ("unknown.dat", UNKNOWN_BIOMETRIC_CONTENT, "text/plain")},
        headers=auth_headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["total_rows"] == 1
    assert payload["rows"][0]["dni"] == "45678912"
    assert payload["rows"][0]["mark_type"] == "entry"


def test_create_import_adds_ai_cost_to_file_name_and_records_usage(
    auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import biometric_import_service as import_service_module

    recorded: list[dict] = []

    monkeypatch.setattr(
        import_service_module.ai_biometric_normalizer_service,
        "normalize_to_csv",
        lambda text: AINormalizationResult(
            csv_text=(
                "dni,apellidos,nombres,fecha_hora,tipo_marca\n"
                "45678912,Quispe Mamani,Maria Elena,2026-05-03 07:55:00,entrada\n"
            ),
            source="openai",
            provider="openai",
            model="gpt-5.2",
            input_tokens=100,
            output_tokens=10,
            total_tokens=110,
            estimated_cost_usd=Decimal("0.000315"),
        ),
    )
    monkeypatch.setattr(
        import_service_module.ai_usage_repository,
        "record",
        lambda data: recorded.append(data),
    )

    response = TestClient(app).post(
        "/api/v1/biometric-imports",
        files={"file": ("unknown.dat", UNKNOWN_BIOMETRIC_CONTENT, "text/plain")},
        headers=auth_headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert "_ia_usd_0_000315.dat" in payload["file_name"]
    assert payload["normalization_source"] == "openai"
    assert payload["ai_estimated_cost_usd"] == "0.000315"
    assert recorded == [
        {
            "biometric_import_id": payload["id"],
            "file_name": payload["file_name"],
            "provider": "openai",
            "model_name": "gpt-5.2",
            "input_tokens": 100,
            "output_tokens": 10,
            "total_tokens": 110,
            "estimated_cost_usd": "0.000315",
        }
    ]


def test_confirm_auto_registers_new_rows(
    auth_headers: dict[str, str],
) -> None:
    client = TestClient(app)
    import_id = create_import(client, auth_headers).json()["id"]

    response = client.post(
        f"/api/v1/biometric-imports/{import_id}/confirmation",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "confirmed"
    assert payload["ok_rows"] == 2
    assert payload["rows"][1]["match"] == "matched"


def test_confirm_registers_duplicate_new_dni_once(
    auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/biometric-imports",
        files={"file": ("duplicate.csv", DUPLICATE_NEW_DNI_CSV, "text/csv")},
        headers=auth_headers,
    )
    import_id = response.json()["id"]
    calls = []
    original_register = biometric_import_service._register_new_staff

    def wrapped_register(row):
        calls.append(row["dni"])
        return original_register(row)

    monkeypatch.setattr(
        biometric_import_service, "_register_new_staff", wrapped_register
    )

    confirm_response = client.post(
        f"/api/v1/biometric-imports/{import_id}/confirmation",
        headers=auth_headers,
    )

    assert confirm_response.status_code == 200
    assert calls == ["99990000"]


def test_confirmed_import_can_be_filtered_from_attendance(
    auth_headers: dict[str, str],
) -> None:
    client = TestClient(app)
    import_id = create_import(client, auth_headers).json()["id"]

    confirm_response = client.post(
        f"/api/v1/biometric-imports/{import_id}/confirmation",
        headers=auth_headers,
    )
    assert confirm_response.status_code == 200

    attendance_response = client.get(
        "/api/v1/attendance-records",
        params={"month": 7, "year": 2026, "import_id": import_id},
        headers=auth_headers,
    )

    assert attendance_response.status_code == 200
    payload = attendance_response.json()
    assert len(payload) == 8
    assert {row["attendance_date"] for row in payload} == {
        "2026-07-01",
        "2026-07-02",
    }
    assert all(row["biometric_import_id"] == import_id for row in payload)
    assert sum(row["status"] == "present" for row in payload) == 2
    assert sum(row["status"] == "absent" for row in payload) == 6


def test_confirm_is_idempotent_after_success(
    auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    client = TestClient(app)
    import_id = create_import(client, auth_headers).json()["id"]

    first_response = client.post(
        f"/api/v1/biometric-imports/{import_id}/confirmation",
        headers=auth_headers,
    )
    second_response = client.post(
        f"/api/v1/biometric-imports/{import_id}/confirmation",
        headers=auth_headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["status"] == "confirmed"

    confirmed_import = first_response.json()
    biometric_import_service.reset()
    monkeypatch.setattr(
        biometric_repository,
        "get_import",
        lambda persisted_id: confirmed_import if persisted_id == import_id else None,
    )
    recovery_response = client.post(
        f"/api/v1/biometric-imports/{import_id}/confirmation",
        headers=auth_headers,
    )

    assert recovery_response.status_code == 200
    assert recovery_response.json()["status"] == "confirmed"


def test_confirmed_import_list_excludes_cancelled_imports(
    auth_headers: dict[str, str],
) -> None:
    client = TestClient(app)
    confirmed_id = create_import(client, auth_headers).json()["id"]
    cancelled_id = create_import(client, auth_headers).json()["id"]

    assert (
        client.post(
            f"/api/v1/biometric-imports/{confirmed_id}/confirmation",
            headers=auth_headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/biometric-imports/{cancelled_id}/cancellation",
            json={"reason": "Archivo incorrecto"},
            headers=auth_headers,
        ).status_code
        == 200
    )

    response = client.get(
        "/api/v1/biometric-imports",
        params={"status": "confirmed"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert confirmed_id in ids
    assert cancelled_id not in ids


def test_register_new_then_confirm_and_cancel(
    auth_headers: dict[str, str],
) -> None:
    client = TestClient(app)
    import_id = create_import(client, auth_headers).json()["id"]

    patch_response = client.patch(
        f"/api/v1/biometric-imports/{import_id}/rows/2",
        json={"action": "register_new"},
        headers=auth_headers,
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["match"] == "matched"
    assert patch_response.json()["resolved"] is True

    confirm_response = client.post(
        f"/api/v1/biometric-imports/{import_id}/confirmation",
        headers=auth_headers,
    )

    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"
    assert confirm_response.json()["ok_rows"] == 2

    cancel_response = client.post(
        f"/api/v1/biometric-imports/{import_id}/cancellation",
        json={"reason": "Archivo/mes incorrecto"},
        headers=auth_headers,
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"


def test_cancel_draft_and_reject_already_cancelled(
    auth_headers: dict[str, str],
) -> None:
    client = TestClient(app)
    import_id = create_import(client, auth_headers).json()["id"]

    cancel_draft_response = client.post(
        f"/api/v1/biometric-imports/{import_id}/cancellation",
        json={"reason": "Todavía borrador"},
        headers=auth_headers,
    )

    assert cancel_draft_response.status_code == 200
    assert cancel_draft_response.json()["status"] == "cancelled"

    cancel_again_response = client.post(
        f"/api/v1/biometric-imports/{import_id}/cancellation",
        json={"reason": "Otra vez"},
        headers=auth_headers,
    )

    assert cancel_again_response.status_code == 409
    assert cancel_again_response.json() == {"detail": "Import is already cancelled"}


def test_cancelled_import_remains_visible_in_import_history(
    auth_headers: dict[str, str],
) -> None:
    client = TestClient(app)
    import_id = create_import(client, auth_headers).json()["id"]

    cancel_response = client.post(
        f"/api/v1/biometric-imports/{import_id}/cancellation",
        json={"reason": "Archivo/mes incorrecto"},
        headers=auth_headers,
    )
    assert cancel_response.status_code == 200

    list_response = client.get("/api/v1/biometric-imports", headers=auth_headers)

    assert list_response.status_code == 200
    imports_by_id = {item["id"]: item for item in list_response.json()}
    assert imports_by_id[import_id]["status"] == "cancelled"


def test_import_history_can_be_limited_to_latest_rows(
    auth_headers: dict[str, str],
) -> None:
    client = TestClient(app)
    created_ids = [create_import(client, auth_headers).json()["id"] for _ in range(12)]

    list_response = client.get(
        "/api/v1/biometric-imports?limit=10", headers=auth_headers
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 10
    assert [item["id"] for item in payload] == list(reversed(created_ids[-10:]))
