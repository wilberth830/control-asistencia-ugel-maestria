"""Secure local storage for justification support files."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from app.core.config import settings


class SupportFileValidationError(ValueError):
    """Raised when a support file cannot be accepted."""


class SupportFileNotFoundError(FileNotFoundError):
    """Raised when a stored support file does not exist."""


class SupportFileService:
    allowed_extensions = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".webp"})
    allowed_content_types = frozenset(
        {
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/webp",
        }
    )

    def __init__(self) -> None:
        self._backend_root = Path(__file__).resolve().parents[2]

    @property
    def base_directory(self) -> Path:
        configured_path = Path(settings.support_files_dir)
        if configured_path.is_absolute():
            return configured_path.resolve()
        return (self._backend_root / configured_path).resolve()

    def save(self, filename: str, content_type: str | None, content: bytes) -> str:
        original_name = Path(filename or "").name
        extension = Path(original_name).suffix.lower()
        if not original_name or extension not in self.allowed_extensions:
            raise SupportFileValidationError("invalid_file_type")
        if content_type not in self.allowed_content_types:
            raise SupportFileValidationError("invalid_file_type")
        if not content:
            raise SupportFileValidationError("empty_file")
        if len(content) > settings.support_file_max_bytes:
            raise SupportFileValidationError("file_too_large")
        if not self._matches_signature(extension, content):
            raise SupportFileValidationError("invalid_file_content")

        safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(original_name).stem)
        safe_stem = safe_stem.strip("_")[:80] or "support"
        stored_name = f"{uuid4().hex}_{safe_stem}{extension}"
        target = self.base_directory / stored_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

        try:
            return target.relative_to(self._backend_root).as_posix()
        except ValueError:
            return str(target)

    def resolve(self, stored_path: str) -> Path:
        candidate = Path(stored_path)
        if not candidate.is_absolute():
            candidate = self._backend_root / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.base_directory)
        except ValueError as exc:
            raise SupportFileNotFoundError(stored_path) from exc
        if not resolved.is_file():
            raise SupportFileNotFoundError(stored_path)
        return resolved

    def delete(self, stored_path: str | None) -> None:
        if not stored_path:
            return
        try:
            self.resolve(stored_path).unlink(missing_ok=True)
        except SupportFileNotFoundError:
            return

    def original_name(self, stored_path: str) -> str:
        stored_name = Path(stored_path).name
        _, separator, original_name = stored_name.partition("_")
        return original_name if separator else stored_name

    def _matches_signature(self, extension: str, content: bytes) -> bool:
        if extension == ".pdf":
            return content.startswith(b"%PDF-")
        if extension in {".jpg", ".jpeg"}:
            return content.startswith(b"\xff\xd8\xff")
        if extension == ".png":
            return content.startswith(b"\x89PNG\r\n\x1a\n")
        if extension == ".webp":
            return (
                len(content) >= 12
                and content.startswith(b"RIFF")
                and content[8:12] == b"WEBP"
            )
        return False


support_file_service = SupportFileService()
