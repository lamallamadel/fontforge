"""Pydantic schemas for authentication request/response payloads."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from aifont.auth.models import UserRole


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    """Payload for registering a new local user."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        """Enforce minimum password complexity (OWASP recommendation)."""
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit."
            )
        return v


class UserRead(BaseModel):
    """Public-facing user representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    is_verified: bool
    role: UserRole
    created_at: datetime


class UserUpdate(BaseModel):
    """Partial update for a user profile."""

    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str | None) -> str | None:
        if v is None:
            return v
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit."
            )
        return v


# ---------------------------------------------------------------------------
# Token schemas
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    """JWT access + refresh token pair returned at login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """Request body for obtaining a new access token via refresh token."""

    refresh_token: str


class AccessTokenResponse(BaseModel):
    """New access token returned after a refresh."""

    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Credentials for local (email + password) login."""

    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# API Key schemas
# ---------------------------------------------------------------------------


class APIKeyCreate(BaseModel):
    """Payload for creating a new API key."""

    name: str = Field(min_length=1, max_length=255)
    expires_at: datetime | None = None


class APIKeyRead(BaseModel):
    """API key representation (key value never returned after creation)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None


class APIKeyCreated(APIKeyRead):
    """Returned only at creation — includes the raw key value."""

    key: str  # plain-text key shown exactly once


# ---------------------------------------------------------------------------
# Quota schemas
# ---------------------------------------------------------------------------


class QuotaRead(BaseModel):
    """Current quota state for the authenticated user."""

    model_config = ConfigDict(from_attributes=True)

    max_fonts: int
    max_exports_per_day: int
    max_api_keys: int
    exports_today: int
    fonts_created: int
    reset_at: datetime


# ---------------------------------------------------------------------------
# Role assignment (admin only)
# ---------------------------------------------------------------------------


class RoleUpdate(BaseModel):
    """Request body for changing a user's role (admin only)."""

    role: UserRole
