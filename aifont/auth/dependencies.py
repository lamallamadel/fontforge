"""FastAPI dependency functions for authentication and authorization."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from aifont.auth.jwt import TokenError, decode_access_token
from aifont.auth.models import APIKey, User, UserRole
from aifont.db import get_db

# ---------------------------------------------------------------------------
# FastAPI security schemes
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# Current-user helpers
# ---------------------------------------------------------------------------


async def _get_user_by_id(user_id: uuid.UUID, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_current_user(
    token: str | None = Depends(_oauth2_scheme),
    bearer: HTTPAuthorizationCredentials | None = Security(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the JWT bearer token (or API key) to a ``User`` instance.

    Raises ``HTTP 401`` if authentication fails.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Prefer the raw Bearer header if present (allows API key auth too)
    raw_token: str | None = token
    if bearer is not None:
        raw_token = bearer.credentials

    if not raw_token:
        raise credentials_exception

    # --- JWT path ---
    try:
        payload = decode_access_token(raw_token)
        user_id = uuid.UUID(payload["sub"])
    except (TokenError, KeyError, ValueError):
        # --- API key fallback ---
        user = await _resolve_api_key(raw_token, db)
        if user is None:
            raise credentials_exception
        return user

    user = await _get_user_by_id(user_id, db)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def _resolve_api_key(raw: str, db: AsyncSession) -> User | None:
    """Validate a plain-text API key and return its owner."""
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    result = await db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active.is_(True))
    )
    api_key: APIKey | None = result.scalar_one_or_none()
    if api_key is None:
        return None
    now = datetime.now(timezone.utc)
    if api_key.expires_at is not None:
        expires_at = api_key.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            return None
    api_key.last_used_at = now
    await db.commit()
    return await _get_user_by_id(api_key.user_id, db)


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Raise HTTP 400 if the authenticated user is inactive."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user.")
    return current_user


# ---------------------------------------------------------------------------
# Role-based access control (RBAC)
# ---------------------------------------------------------------------------


def require_role(*roles: UserRole):
    """Return a dependency that enforces one of the given *roles*."""

    async def _check(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return _check


require_admin = require_role(UserRole.ADMIN)
require_pro_or_admin = require_role(UserRole.PRO, UserRole.ADMIN)
