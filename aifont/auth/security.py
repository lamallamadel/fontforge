"""Password hashing and OWASP-aligned security utilities."""

from __future__ import annotations

import secrets
import string

from passlib.context import CryptContext

# bcrypt with a work factor of 12 (OWASP recommendation for bcrypt).
_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)

# Characters allowed in auto-generated API keys (URL-safe, no ambiguous chars).
_KEY_ALPHABET = string.ascii_letters + string.digits


def hash_password(plain: str) -> str:
    """Return the bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


def generate_secure_token(nbytes: int = 32) -> str:
    """Return a URL-safe random token of *nbytes* bytes (base64-encoded)."""
    return secrets.token_urlsafe(nbytes)


def generate_api_key(length: int = 40) -> str:
    """Return a random API key of *length* characters from a safe alphabet."""
    return "".join(secrets.choice(_KEY_ALPHABET) for _ in range(length))


def constant_time_compare(a: str, b: str) -> bool:
    """Timing-safe string comparison (OWASP A07 — avoid timing attacks)."""
    return secrets.compare_digest(a.encode(), b.encode())
