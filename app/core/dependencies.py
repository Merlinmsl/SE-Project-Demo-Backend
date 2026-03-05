from __future__ import annotations

from fastapi import Header, HTTPException, status
from app.core.config import settings
from app.core.security import AuthUser, ClerkJWTVerifier

_clerk_verifier: ClerkJWTVerifier | None = None


def get_current_user(
    authorization: str | None = Header(default=None),
    x_clerk_user_id: str | None = Header(default=None),
    x_email: str | None = Header(default=None),
) -> AuthUser:
    """Verify a Clerk JWT passed as Authorization: Bearer <token>, but allow dev bypass."""
    if settings.auth_mode == "dev" and x_clerk_user_id:
        return AuthUser(clerk_user_id=x_clerk_user_id, email=x_email)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected: Bearer <clerk_jwt>",
        )
    token = authorization.split(" ", 1)[1].strip()

    global _clerk_verifier
    if _clerk_verifier is None:
        _clerk_verifier = ClerkJWTVerifier(settings.clerk_jwks_url, settings.clerk_issuer)

    try:
        return _clerk_verifier.verify(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Clerk token: {e}",
        )


def require_admin_api_key(x_admin_api_key: str | None = Header(default=None)) -> None:
    if not x_admin_api_key or x_admin_api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Admin only")
