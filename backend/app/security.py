"""Authentication helpers for JWT token issuance and verification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from os import getenv

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60
security = HTTPBearer(auto_error=True)


def _secret_key() -> str:
    return getenv("JWT_SECRET", "dev-only-change-me")


def create_access_token(user_id: str) -> str:
    """Create a signed JWT for a user ID."""

    expiry = datetime.now(tz=UTC) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    payload = {"sub": user_id, "exp": int(expiry.timestamp())}
    return jwt.encode(payload, _secret_key(), algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Validate bearer token and return authenticated user ID."""

    token = credentials.credentials
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        ) from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return subject
