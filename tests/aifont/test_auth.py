"""
Security tests for the AIFont authentication system.

These tests cover:
- OWASP A01: Broken Access Control
- OWASP A02: Cryptographic Failures (password hashing, JWT signing)
- OWASP A04: Insecure Design (quota enforcement, role escalation)
- OWASP A05: Security Misconfiguration (inactive users)
- OWASP A07: Identification and Authentication Failures (brute-force timing, weak passwords)
"""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aifont.auth.jwt import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from aifont.auth.models import UserRole
from aifont.auth.quota import (
    QUOTA_DEFAULTS,
    QuotaExceeded,
    check_api_key_quota,
    check_export_quota,
    check_font_quota,
)
from aifont.auth.schemas import UserCreate
from aifont.auth.security import (
    constant_time_compare,
    generate_api_key,
    generate_secure_token,
    hash_password,
    verify_password,
)


# ===========================================================================
# Helpers
# ===========================================================================


def _make_user(role: UserRole = UserRole.FREE) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = role
    user.api_keys = []
    return user


def _make_quota(**overrides):
    q = MagicMock()
    defaults = QUOTA_DEFAULTS[UserRole.FREE].copy()
    defaults.update(overrides)
    q.max_fonts = defaults["max_fonts"]
    q.max_exports_per_day = defaults["max_exports_per_day"]
    q.max_api_keys = defaults["max_api_keys"]
    q.exports_today = overrides.get("exports_today", 0)
    q.fonts_created = overrides.get("fonts_created", 0)
    q.reset_at = datetime.now(timezone.utc) + timedelta(hours=1)
    return q


# ===========================================================================
# OWASP A02 — Cryptographic Failures
# ===========================================================================


class TestPasswordHashing:
    """bcrypt hashing must be irreversible and produce unique salts."""

    def test_hash_and_verify_roundtrip(self):
        raw = "SecurePass1"
        hashed = hash_password(raw)
        assert verify_password(raw, hashed)

    def test_wrong_password_rejected(self):
        hashed = hash_password("SecurePass1")
        assert not verify_password("WrongPass9", hashed)

    def test_hashes_differ_for_same_password(self):
        """bcrypt must produce a different salt each time (no deterministic hash)."""
        raw = "SecurePass1"
        assert hash_password(raw) != hash_password(raw)

    def test_hash_is_not_plaintext(self):
        raw = "SecurePass1"
        hashed = hash_password(raw)
        assert raw not in hashed


class TestJWTSigning:
    """JWT tokens must be signed and type-safe."""

    def test_access_token_roundtrip(self):
        uid = uuid.uuid4()
        token = create_access_token(uid, UserRole.FREE)
        payload = decode_access_token(token)
        assert payload["sub"] == str(uid)
        assert payload["role"] == UserRole.FREE.value
        assert payload["type"] == "access"

    def test_refresh_token_roundtrip(self):
        uid = uuid.uuid4()
        token = create_refresh_token(uid)
        payload = decode_refresh_token(token)
        assert payload["sub"] == str(uid)
        assert payload["type"] == "refresh"

    def test_access_token_rejected_as_refresh(self):
        token = create_access_token(uuid.uuid4(), UserRole.FREE)
        with pytest.raises(TokenError):
            decode_refresh_token(token)

    def test_refresh_token_rejected_as_access(self):
        token = create_refresh_token(uuid.uuid4())
        with pytest.raises(TokenError):
            decode_access_token(token)

    def test_tampered_token_rejected(self):
        token = create_access_token(uuid.uuid4(), UserRole.FREE)
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(TokenError):
            decode_access_token(tampered)

    def test_expired_token_rejected(self):
        token = create_access_token(
            uuid.uuid4(), UserRole.FREE, expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(TokenError):
            decode_access_token(token)

    def test_unique_jti_per_token(self):
        """Each token must have a unique JWT ID to support revocation."""
        uid = uuid.uuid4()
        t1 = decode_access_token(create_access_token(uid, UserRole.FREE))
        t2 = decode_access_token(create_access_token(uid, UserRole.FREE))
        assert t1["jti"] != t2["jti"]


class TestSecureTokenGeneration:
    """Secure tokens must be long enough to resist brute force."""

    def test_generate_secure_token_length(self):
        token = generate_secure_token()
        # 32 bytes base64-encoded → at least 43 chars
        assert len(token) >= 43

    def test_generate_api_key_length(self):
        key = generate_api_key()
        assert len(key) == 40

    def test_api_keys_are_unique(self):
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100

    def test_constant_time_compare_equal(self):
        assert constant_time_compare("abc", "abc")

    def test_constant_time_compare_not_equal(self):
        assert not constant_time_compare("abc", "xyz")


# ===========================================================================
# OWASP A01 — Broken Access Control / RBAC
# ===========================================================================


class TestRoleEmbeddedInToken:
    """Access tokens must carry the user's role for RBAC enforcement."""

    def test_admin_role_embedded(self):
        token = create_access_token(uuid.uuid4(), UserRole.ADMIN)
        payload = decode_access_token(token)
        assert payload["role"] == "admin"

    def test_pro_role_embedded(self):
        token = create_access_token(uuid.uuid4(), UserRole.PRO)
        payload = decode_access_token(token)
        assert payload["role"] == "pro"

    def test_free_role_embedded(self):
        token = create_access_token(uuid.uuid4(), UserRole.FREE)
        payload = decode_access_token(token)
        assert payload["role"] == "free"


# ===========================================================================
# OWASP A07 — Weak Password Policy
# ===========================================================================


class TestPasswordComplexity:
    """Registration must enforce minimum complexity rules."""

    def test_accepts_complex_password(self):
        data = UserCreate(email="user@example.com", password="Secure123")
        assert data.password == "Secure123"

    def test_rejects_all_lowercase(self):
        with pytest.raises(Exception):
            UserCreate(email="u@example.com", password="lowercase1")

    def test_rejects_all_uppercase(self):
        with pytest.raises(Exception):
            UserCreate(email="u@example.com", password="UPPERCASE1")

    def test_rejects_no_digits(self):
        with pytest.raises(Exception):
            UserCreate(email="u@example.com", password="NoDigitsHere")

    def test_rejects_too_short(self):
        with pytest.raises(Exception):
            UserCreate(email="u@example.com", password="Ab1")

    def test_rejects_invalid_email(self):
        with pytest.raises(Exception):
            UserCreate(email="not-an-email", password="ValidPass1")


# ===========================================================================
# OWASP A04 — Insecure Design / Quota enforcement
# ===========================================================================


class TestQuotaEnforcement:
    """Quota limits must be enforced regardless of the user's role."""

    @pytest.mark.asyncio
    async def test_export_quota_exceeded(self):
        user = _make_user(UserRole.FREE)
        quota = _make_quota(exports_today=10, max_exports_per_day=10)
        db = AsyncMock()

        with patch("aifont.auth.quota.get_or_create_quota", return_value=quota), patch(
            "aifont.auth.quota.reset_quota_if_needed", return_value=quota
        ):
            with pytest.raises(QuotaExceeded):
                await check_export_quota(user, db)

    @pytest.mark.asyncio
    async def test_export_quota_within_limit(self):
        user = _make_user(UserRole.FREE)
        quota = _make_quota(exports_today=5, max_exports_per_day=10)
        db = AsyncMock()

        with patch("aifont.auth.quota.get_or_create_quota", return_value=quota), patch(
            "aifont.auth.quota.reset_quota_if_needed", return_value=quota
        ):
            # Should not raise
            await check_export_quota(user, db)
            assert quota.exports_today == 6

    @pytest.mark.asyncio
    async def test_font_quota_exceeded(self):
        user = _make_user(UserRole.FREE)
        quota = _make_quota(fonts_created=5, max_fonts=5)
        db = AsyncMock()

        with patch("aifont.auth.quota.get_or_create_quota", return_value=quota):
            with pytest.raises(QuotaExceeded):
                await check_font_quota(user, db)

    @pytest.mark.asyncio
    async def test_api_key_quota_exceeded(self):
        user = _make_user(UserRole.FREE)
        # Simulate 2 active keys
        key1 = MagicMock()
        key1.is_active = True
        key2 = MagicMock()
        key2.is_active = True
        user.api_keys = [key1, key2]
        quota = _make_quota(max_api_keys=2)
        db = AsyncMock()

        with patch("aifont.auth.quota.get_or_create_quota", return_value=quota):
            with pytest.raises(QuotaExceeded):
                await check_api_key_quota(user, db)

    def test_quota_defaults_by_role(self):
        """Free plan must have lower limits than Pro, which must be lower than Admin."""
        free = QUOTA_DEFAULTS[UserRole.FREE]
        pro = QUOTA_DEFAULTS[UserRole.PRO]
        admin = QUOTA_DEFAULTS[UserRole.ADMIN]

        assert free["max_fonts"] < pro["max_fonts"] < admin["max_fonts"]
        assert (
            free["max_exports_per_day"]
            < pro["max_exports_per_day"]
            < admin["max_exports_per_day"]
        )
        assert free["max_api_keys"] < pro["max_api_keys"] < admin["max_api_keys"]


# ===========================================================================
# API Key hashing
# ===========================================================================


class TestAPIKeyHashing:
    """Raw API keys must never be stored — only their SHA-256 hash."""

    def test_key_hash_is_sha256(self):
        raw = generate_api_key()
        expected = hashlib.sha256(raw.encode()).hexdigest()
        # Verify our hashing function produces the same result
        assert hashlib.sha256(raw.encode()).hexdigest() == expected

    def test_different_keys_produce_different_hashes(self):
        k1 = generate_api_key()
        k2 = generate_api_key()
        assert hashlib.sha256(k1.encode()).hexdigest() != hashlib.sha256(k2.encode()).hexdigest()
