"""JWT access-token and refresh-token management."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from aifont.auth.models import UserRole

# ---------------------------------------------------------------------------
# Settings (resolved from environment variables with sane defaults)
# ---------------------------------------------------------------------------

SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------


def create_access_token(
    user_id: uuid.UUID,
    role: UserRole,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived JWT access token for *user_id*.

    Args:
        user_id: The subject of the token.
        role: The user's current role (embedded as a custom claim).
        expires_delta: Override the default expiry window.

    Returns:
        A signed JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role.value,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: uuid.UUID) -> str:
    """Create a long-lived opaque JWT used exclusively for token rotation.

    The returned token is also stored (as a hash) in the database so that
    it can be revoked server-side at any time.

    Args:
        user_id: The subject of the token.

    Returns:
        A signed JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------


class TokenError(Exception):
    """Raised when a token cannot be decoded or has invalid claims."""


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Args:
        token: The encoded JWT string.

    Returns:
        The decoded payload dictionary.

    Raises:
        TokenError: If the token is invalid, expired, or has wrong type.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise TokenError(f"Invalid token: {exc}") from exc

    if payload.get("type") != "access":
        raise TokenError("Token is not an access token.")

    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT refresh token.

    Args:
        token: The encoded JWT string.

    Returns:
        The decoded payload dictionary.

    Raises:
        TokenError: If the token is invalid, expired, or has wrong type.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise TokenError(f"Invalid token: {exc}") from exc

    if payload.get("type") != "refresh":
        raise TokenError("Token is not a refresh token.")

    return payload
