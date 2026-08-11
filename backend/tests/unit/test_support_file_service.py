import asyncio
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.api import justifications as justifications_api
from app.core.config import settings
from app.services.support_file_service import (
    SupportFileNotFoundError,
    SupportFileValidationError,
    support_file_service,
)


def test_save_and_resolve_pdf_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "support_files_dir", str(tmp_path))

    stored_path = support_file_service.save(
        "Resolución médica.pdf",
        "application/pdf",
        b"%PDF-1.7\nvalid-test-content",
    )

    resolved = support_file_service.resolve(stored_path)
    assert resolved.read_bytes().startswith(b"%PDF-")
    assert support_file_service.original_name(stored_path) == "Resoluci_n_m_dica.pdf"


def test_rejects_file_with_fake_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "support_files_dir", str(tmp_path))

    with pytest.raises(SupportFileValidationError, match="invalid_file_content"):
        support_file_service.save(
            "sustento.pdf",
            "application/pdf",
            b"this is not a pdf",
        )


def test_rejects_path_outside_support_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    support_directory = tmp_path / "support"
    outside_file = tmp_path / "outside.pdf"
    outside_file.write_bytes(b"%PDF-1.7")
    monkeypatch.setattr(settings, "support_files_dir", str(support_directory))

    with pytest.raises(SupportFileNotFoundError):
        support_file_service.resolve(str(outside_file))


def test_create_endpoint_persists_uploaded_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "support_files_dir", str(tmp_path))

    def create_stub(data: dict) -> dict:
        return {**data, "id": 21, "status": "active"}

    monkeypatch.setattr(justifications_api.justification_service, "create", create_stub)
    monkeypatch.setattr(justifications_api.audit_service, "record", lambda **_: None)
    upload = UploadFile(
        BytesIO(b"%PDF-1.7\nendpoint-test"),
        filename="sustento.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )

    item = asyncio.run(
        justifications_api.create_justification(
            staff_member_id=4,
            start_date="2026-07-10",
            end_date="2026-07-12",
            norm_code="LG",
            with_pay="Y",
            reason="Licencia médica",
            support_file=upload,
            session={"user_id": 1},
        )
    )

    assert item["support_file_path"]
    assert support_file_service.resolve(item["support_file_path"]).is_file()
