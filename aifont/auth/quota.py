"""Quota defaults per plan and enforcement helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from aifont.auth.models import Quota, User, UserRole

# ---------------------------------------------------------------------------
# Quota limits per plan (role)
# ---------------------------------------------------------------------------

QUOTA_DEFAULTS: dict[UserRole, dict[str, int]] = {
    UserRole.FREE: {
        "max_fonts": 5,
        "max_exports_per_day": 10,
        "max_api_keys": 2,
    },
    UserRole.PRO: {
        "max_fonts": 100,
        "max_exports_per_day": 500,
        "max_api_keys": 20,
    },
    UserRole.ADMIN: {
        "max_fonts": 10_000,
        "max_exports_per_day": 10_000,
        "max_api_keys": 100,
    },
}


# ---------------------------------------------------------------------------
# Quota creation / retrieval
# ---------------------------------------------------------------------------


async def get_or_create_quota(user: User, db: AsyncSession) -> Quota:
    """Return the user's Quota row, creating it with plan defaults if absent."""
    result = await db.execute(select(Quota).where(Quota.user_id == user.id))
    quota = result.scalar_one_or_none()
    if quota is None:
        defaults = QUOTA_DEFAULTS.get(user.role, QUOTA_DEFAULTS[UserRole.FREE])
        quota = Quota(
            user_id=user.id,
            **defaults,
            reset_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(quota)
        await db.commit()
        await db.refresh(quota)
    return quota


async def reset_quota_if_needed(quota: Quota, db: AsyncSession) -> Quota:
    """Reset rolling daily counters if the reset window has passed."""
    now = datetime.now(timezone.utc)
    reset_at = quota.reset_at
    if reset_at.tzinfo is None:
        reset_at = reset_at.replace(tzinfo=timezone.utc)
    if now >= reset_at:
        quota.exports_today = 0
        quota.reset_at = now + timedelta(days=1)
        await db.commit()
        await db.refresh(quota)
    return quota


# ---------------------------------------------------------------------------
# Quota enforcement
# ---------------------------------------------------------------------------


class QuotaExceededError(Exception):
    """Raised when a user exceeds one of their plan limits."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


#: Alias for :class:`QuotaExceededError` (backward-compatible name).
QuotaExceeded = QuotaExceededError


async def check_export_quota(user: User, db: AsyncSession) -> None:
    """Raise QuotaExceeded if the user has exhausted their daily export quota."""
    quota = await get_or_create_quota(user, db)
    quota = await reset_quota_if_needed(quota, db)
    if quota.exports_today >= quota.max_exports_per_day:
        raise QuotaExceededError(
            f"Daily export quota exhausted ({quota.max_exports_per_day}/day). "
            "Upgrade your plan for a higher limit."
        )
    quota.exports_today += 1
    await db.commit()


async def check_font_quota(user: User, db: AsyncSession) -> None:
    """Raise QuotaExceeded if the user has reached their maximum font count."""
    quota = await get_or_create_quota(user, db)
    if quota.fonts_created >= quota.max_fonts:
        raise QuotaExceededError(
            f"Font quota exhausted ({quota.max_fonts} fonts). "
            "Upgrade your plan to create more fonts."
        )
    quota.fonts_created += 1
    await db.commit()


async def check_api_key_quota(user: User, db: AsyncSession) -> None:
    """Raise QuotaExceeded if the user has reached their maximum API key count."""
    quota = await get_or_create_quota(user, db)
    active_keys = sum(1 for k in user.api_keys if k.is_active)
    if active_keys >= quota.max_api_keys:
        raise QuotaExceededError(
            f"API key quota exhausted ({quota.max_api_keys} active keys). "
            "Revoke an existing key or upgrade your plan."
        )


async def apply_role_quota(user: User, db: AsyncSession) -> None:
    """Update the user's quota to match their current role defaults."""
    quota = await get_or_create_quota(user, db)
    defaults = QUOTA_DEFAULTS.get(user.role, QUOTA_DEFAULTS[UserRole.FREE])
    quota.max_fonts = defaults["max_fonts"]
    quota.max_exports_per_day = defaults["max_exports_per_day"]
    quota.max_api_keys = defaults["max_api_keys"]
    await db.commit()
