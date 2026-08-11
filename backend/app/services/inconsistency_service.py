"""TEC-D06 — inconsistency orchestration."""

from __future__ import annotations

from app.repositories.inconsistency_repository import inconsistency_repository
from app.rules.inconsistency_rules import detect_basic_issues, ia_suggest
from app.repositories.biometric_repository import biometric_repository
from app.repositories.oracle import OracleRepositoryError


class InconsistencyNotFoundError(LookupError):
    """Raised when an inconsistency does not exist."""


class InconsistencyService:
    def list(self) -> list[dict]:
        try:
            rows = inconsistency_repository.list()
            if rows:
                return rows
        except OracleRepositoryError:
            pass
        return self.analyze([])

    def review(self, inconsistency_id: int) -> dict:
        return self._set_status(inconsistency_id, "reviewed")

    def correct(self, inconsistency_id: int) -> dict:
        return self._set_status(inconsistency_id, "corrected")

    def analyze(self, marks: list[dict]) -> list[dict]:
        if not marks:
            try:
                marks = biometric_repository.list_marks()
            except OracleRepositoryError:
                marks = []
        issues = detect_basic_issues(marks)
        issues.extend(ia_suggest(marks))
        return issues

    def _set_status(self, inconsistency_id: int, status: str) -> dict:
        try:
            row = inconsistency_repository.set_status(inconsistency_id, status)
            if row is None:
                raise InconsistencyNotFoundError(
                    f"Inconsistency {inconsistency_id} not found"
                )
            return row
        except OracleRepositoryError:
            return {"id": inconsistency_id, "status": status}


inconsistency_service = InconsistencyService()
