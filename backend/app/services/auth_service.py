"""TEC-D03 — authentication and access map."""

from __future__ import annotations

import secrets
from typing import Any, Optional

from app.core.config import settings
from app.core.security import verify_password
from app.repositories.oracle import OracleRepositoryError
from app.repositories.user_account_repository import user_account_repository
from app.services.session_store import session_store


class AuthStoreUnavailable(RuntimeError):
    """Raised when user authentication storage is unavailable."""


def _access_for_role(role: str) -> dict[str, Any]:
    return {
        "modules": [
            "dashboard",
            "personal",
            "asistencia_biometrica",
            "administracion_asistencia",
            "reportes_oficiales",
        ],
        "operations": {
            "gestionar_personal": True,
            "cargar_biometrico": True,
            "revisar_inconsistencias": True,
            "gestionar_justificaciones": True,
            "corregir_marcas": True,
            "generar_reportes": True,
            "ver_dashboard": True,
        },
    }


class AuthService:
    def login(self, username: str, password: str) -> Optional[dict[str, Any]]:
        user = self._find_user(username)
        if not user or user["is_active"] != "Y":
            return None
        if not verify_password(password, user["password_hash"]):
            return None
        token = secrets.token_urlsafe(32)
        access = _access_for_role(user["role_name"])
        payload = {
            "user_id": user["id"],
            "username": user["username"],
            "role": user["role_name"],
            "access": access,
        }
        session_store.save(token, payload, settings.access_token_expire_minutes * 60)
        return {
            "token": token,
            "role": user["role_name"],
            "username": user["username"],
            "access": access,
        }

    def current(self, token: str) -> Optional[dict[str, Any]]:
        return session_store.get(token)

    def logout(self, token: str) -> None:
        session_store.delete(token)

    def _find_user(self, username: str) -> Optional[dict[str, Any]]:
        try:
            return user_account_repository.find_active_by_username(username)
        except OracleRepositoryError as exc:
            raise AuthStoreUnavailable("Authentication store unavailable") from exc


auth_service = AuthService()
