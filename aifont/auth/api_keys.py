"""API key generation, hashing, and revocation utilities."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from aifont.auth.models import APIKey, User
from aifont.auth.security import generate_api_key


def _hash_key(raw: str) -> str:
    """Return the SHA-256 hex digest of *raw*."""
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_api_key(
    user: User,
    name: str,
    db: AsyncSession,
    expires_at: datetime | None = None,
) -> tuple[APIKey, str]:
    """Create a new API key for *user*.

    The raw key value is returned only here and is never stored in plain text.

    Args:
        user: The owner of the new key.
        name: A human-readable label for the key.
        db: The active database session.
        expires_at: Optional expiry timestamp.

    Returns:
        A ``(APIKey, raw_key)`` tuple.  The caller must present *raw_key* to
        the end-user exactly once.
    """
    raw = generate_api_key()
    key_hash = _hash_key(raw)
    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        name=name,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key, raw


async def revoke_api_key(key_id: str, user: User, db: AsyncSession) -> bool:
    """Deactivate an API key owned by *user*.

    Args:
        key_id: UUID string of the key to revoke.
        user: The authenticated user (must own the key).
        db: The active database session.

    Returns:
        True if the key was found and revoked, False otherwise.
    """
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        return False
    api_key.is_active = False
    await db.commit()
    return True


async def lookup_api_key(raw: str, db: AsyncSession) -> APIKey | None:
    """Find an active, non-expired APIKey row matching *raw*.

    Updates ``last_used_at`` as a side-effect when a match is found.

    Args:
        raw: The plain-text API key supplied by the caller.
        db: The active database session.

    Returns:
        The matching :class:`APIKey` (with its ``user`` relationship loaded),
        or ``None`` if not found / revoked / expired.
    """
    key_hash = _hash_key(raw)
    result = await db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active.is_(True))
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        return None

    # Check expiry
    now = datetime.now(timezone.utc)
    if api_key.expires_at is not None:
        expires_at = api_key.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            return None

    # Record usage timestamp
    api_key.last_used_at = now
    await db.commit()
    await db.refresh(api_key)
    return api_key
