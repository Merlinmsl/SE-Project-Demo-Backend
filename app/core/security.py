from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any
import httpx
from jose import jwt

@dataclass(frozen=True)
class AuthUser:
    clerk_user_id: str
    email: Optional[str] = None

class ClerkJWTVerifier:
    def __init__(self, jwks_url: str, issuer: str):
        self.jwks_url = jwks_url
        self.issuer = issuer
        self._jwks: dict[str, Any] | None = None

    def _get_jwks(self) -> dict[str, Any]:
        if self._jwks is None:
            r = httpx.get(self.jwks_url, timeout=10)
            r.raise_for_status()
            self._jwks = r.json()
        return self._jwks

    def verify(self, token: str) -> AuthUser:
        jwks = self._get_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            issuer=self.issuer,
            options={"verify_aud": False},
        )
        sub = payload.get("sub")
        email = payload.get("email") or payload.get("primary_email_address")
        if not sub:
            raise ValueError("Missing sub in JWT")
        return AuthUser(clerk_user_id=sub, email=email)
