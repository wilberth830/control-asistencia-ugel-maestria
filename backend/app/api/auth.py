"""TEC-D03 — auth routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import require_token
from app.services.auth_service import AuthStoreUnavailable, auth_service
from app.services.session_store import SessionStoreUnavailable

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/sessions")
def start_session(body: LoginBody):
    try:
        result = auth_service.login(body.username, body.password)
    except AuthStoreUnavailable as exc:
        raise HTTPException(
            status_code=503, detail="Authentication store unavailable"
        ) from exc
    except SessionStoreUnavailable as exc:
        raise HTTPException(
            status_code=503, detail="Session service unavailable"
        ) from exc
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return result


@router.get("/sessions/current")
def current_session(session: dict = Depends(require_token)):
    return {
        "username": session.get("username"),
        "role": session.get("role"),
        "access": session.get("access"),
    }


@router.delete("/sessions/current")
def end_session(session: dict = Depends(require_token)):
    auth_service.logout(session["token"])
    return {"message": "Session closed"}
