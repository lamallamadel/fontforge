"""FastAPI router exposing all authentication and user-management endpoints."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from aifont.auth.api_keys import create_api_key, revoke_api_key
from aifont.auth.dependencies import (
    get_current_active_user,
    require_admin,
)
from aifont.auth.jwt import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from aifont.auth.models import APIKey, OAuthAccount, OAuthProvider, RefreshToken, User, UserRole
from aifont.auth.oauth2 import (
    exchange_github_code,
    exchange_google_code,
    get_github_user_info,
    get_google_user_info,
    github_auth_url,
    google_auth_url,
)
from aifont.auth.quota import (
    QuotaExceeded,
    apply_role_quota,
    check_api_key_quota,
    get_or_create_quota,
)
from aifont.auth.schemas import (
    AccessTokenResponse,
    APIKeyCreate,
    APIKeyCreated,
    APIKeyRead,
    LoginRequest,
    QuotaRead,
    RoleUpdate,
    TokenRefreshRequest,
    TokenResponse,
    UserCreate,
    UserRead,
    UserUpdate,
)
from aifont.auth.security import hash_password, verify_password
from aifont.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Registration / Login
# ---------------------------------------------------------------------------


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """Register a new local user account."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    # Provision default quota
    await get_or_create_quota(user, db)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Authenticate with email and password; return JWT access + refresh tokens."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user: User | None = result.scalar_one_or_none()

    # Constant-time-like check (always hash even on missing user to avoid timing leaks)
    dummy_hash = "$2b$12$invalidhashpadding000000000000000000000000000000000000000"
    stored_hash = user.hashed_password if user and user.hashed_password else dummy_hash
    password_ok = verify_password(payload.password, stored_hash)

    if not user or not user.is_active or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id, user.role)
    raw_refresh = create_refresh_token(user.id)
    _store_refresh_token(user, raw_refresh, db)
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_tokens(
    payload: TokenRefreshRequest, db: AsyncSession = Depends(get_db)
) -> AccessTokenResponse:
    """Exchange a valid refresh token for a new access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        data = decode_refresh_token(payload.refresh_token)
    except TokenError:
        raise credentials_exception

    token_hash = _hash_token(payload.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked.is_(False),
        )
    )
    stored: RefreshToken | None = result.scalar_one_or_none()
    if stored is None:
        raise credentials_exception

    # Rotate: revoke the old token and issue a new pair
    stored.is_revoked = True

    user_id = uuid.UUID(data["sub"])
    user_result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception

    new_access = create_access_token(user.id, user.role)
    new_raw_refresh = create_refresh_token(user.id)
    _store_refresh_token(user, new_raw_refresh, db)
    await db.commit()

    return AccessTokenResponse(access_token=new_access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: TokenRefreshRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke the supplied refresh token (server-side logout)."""
    token_hash = _hash_token(payload.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == current_user.id,
        )
    )
    stored: RefreshToken | None = result.scalar_one_or_none()
    if stored:
        stored.is_revoked = True
        await db.commit()


# ---------------------------------------------------------------------------
# Current-user profile
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_active_user)) -> User:
    """Return the authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Update the authenticated user's profile."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.password is not None:
        current_user.hashed_password = hash_password(payload.password)
    await db.commit()
    await db.refresh(current_user)
    return current_user


# ---------------------------------------------------------------------------
# Quota
# ---------------------------------------------------------------------------


@router.get("/me/quota", response_model=QuotaRead)
async def read_quota(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> QuotaRead:
    """Return the authenticated user's current quota status."""
    quota = await get_or_create_quota(current_user, db)
    return QuotaRead.model_validate(quota)


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


@router.post("/me/api-keys", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_key(
    payload: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeyCreated:
    """Generate a new API key for the authenticated user."""
    try:
        await check_api_key_quota(current_user, db)
    except QuotaExceeded as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.detail)

    api_key, raw = await create_api_key(
        current_user, payload.name, db, expires_at=payload.expires_at
    )
    return APIKeyCreated(
        id=api_key.id,
        name=api_key.name,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        key=raw,
    )


@router.get("/me/api-keys", response_model=list[APIKeyRead])
async def list_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[APIKeyRead]:
    """List all API keys belonging to the authenticated user."""
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id)
    )
    keys = result.scalars().all()
    return [APIKeyRead.model_validate(k) for k in keys]


@router.delete("/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke (deactivate) an API key owned by the authenticated user."""
    revoked = await revoke_api_key(str(key_id), current_user, db)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )


# ---------------------------------------------------------------------------
# Admin: role management
# ---------------------------------------------------------------------------


@router.patch(
    "/admin/users/{user_id}/role",
    response_model=UserRead,
    dependencies=[Depends(require_admin)],
)
async def update_user_role(
    user_id: uuid.UUID,
    payload: RoleUpdate,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Change a user's role (admin only).  Also adjusts their quota limits."""
    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.role = payload.role
    await db.commit()
    await apply_role_quota(user, db)
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# OAuth2 — Google
# ---------------------------------------------------------------------------


@router.get("/oauth2/google")
async def oauth2_google_redirect() -> RedirectResponse:
    """Redirect the browser to Google's OAuth2 consent screen."""
    state = secrets.token_urlsafe(16)
    return RedirectResponse(google_auth_url(state))


@router.get("/oauth2/google/callback", response_model=TokenResponse)
async def oauth2_google_callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Handle Google OAuth2 callback and return JWT tokens."""
    try:
        tokens = await exchange_google_code(code)
        user_info = await get_google_user_info(tokens["access_token"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth2 error: {exc}",
        )

    user = await _upsert_oauth_user(
        provider=OAuthProvider.GOOGLE,
        provider_user_id=user_info["sub"],
        email=user_info.get("email", ""),
        full_name=user_info.get("name"),
        access_token=tokens.get("access_token"),
        refresh_token_oauth=tokens.get("refresh_token"),
        db=db,
    )

    access = create_access_token(user.id, user.role)
    raw_refresh = create_refresh_token(user.id)
    _store_refresh_token(user, raw_refresh, db)
    await db.commit()
    return TokenResponse(access_token=access, refresh_token=raw_refresh)


# ---------------------------------------------------------------------------
# OAuth2 — GitHub
# ---------------------------------------------------------------------------


@router.get("/oauth2/github")
async def oauth2_github_redirect() -> RedirectResponse:
    """Redirect the browser to GitHub's OAuth2 consent screen."""
    state = secrets.token_urlsafe(16)
    return RedirectResponse(github_auth_url(state))


@router.get("/oauth2/github/callback", response_model=TokenResponse)
async def oauth2_github_callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Handle GitHub OAuth2 callback and return JWT tokens."""
    try:
        tokens = await exchange_github_code(code)
        user_info = await get_github_user_info(tokens["access_token"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub OAuth2 error: {exc}",
        )

    user = await _upsert_oauth_user(
        provider=OAuthProvider.GITHUB,
        provider_user_id=str(user_info["id"]),
        email=user_info.get("email") or "",
        full_name=user_info.get("name"),
        access_token=tokens.get("access_token"),
        refresh_token_oauth=None,
        db=db,
    )

    access = create_access_token(user.id, user.role)
    raw_refresh = create_refresh_token(user.id)
    _store_refresh_token(user, raw_refresh, db)
    await db.commit()
    return TokenResponse(access_token=access, refresh_token=raw_refresh)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _hash_token(raw: str) -> str:
    """Return the SHA-256 hex digest of *raw*."""
    return hashlib.sha256(raw.encode()).hexdigest()


def _store_refresh_token(user: User, raw: str, db: AsyncSession) -> None:
    """Persist a hashed refresh token row (not yet committed)."""
    from datetime import timedelta

    from aifont.auth.jwt import REFRESH_TOKEN_EXPIRE_DAYS

    token_hash = _hash_token(raw)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
    )


async def _upsert_oauth_user(
    *,
    provider: OAuthProvider,
    provider_user_id: str,
    email: str,
    full_name: str | None,
    access_token: str | None,
    refresh_token_oauth: str | None,
    db: AsyncSession,
) -> User:
    """Find or create a user based on their OAuth2 identity.

    If the email is already associated with a local account the OAuth identity
    is linked to that existing account.
    """
    # Check existing OAuth account
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )
    oauth_account: OAuthAccount | None = result.scalar_one_or_none()

    if oauth_account is not None:
        # Update tokens
        oauth_account.access_token = access_token
        oauth_account.refresh_token = refresh_token_oauth
        await db.commit()
        user_result = await db.execute(
            select(User).where(User.id == oauth_account.user_id)
        )
        return user_result.scalar_one()

    # Link to existing local user by email, or create a new one
    user_result = await db.execute(select(User).where(User.email == email))
    user: User | None = user_result.scalar_one_or_none()

    if user is None:
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not retrieve a verified email from the OAuth provider.",
            )
        user = User(email=email, full_name=full_name, is_verified=True)
        db.add(user)
        await db.flush()  # get user.id before creating quota
        await get_or_create_quota(user, db)

    db.add(
        OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=access_token,
            refresh_token=refresh_token_oauth,
        )
    )
    await db.commit()
    await db.refresh(user)
    return user
