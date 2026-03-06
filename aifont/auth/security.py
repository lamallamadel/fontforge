"""Password hashing and OWASP-aligned security utilities."""

from __future__ import annotations

import hashlib
import secrets
import string

import bcrypt

# Work factor of 12 is the OWASP recommendation for bcrypt.
_BCRYPT_ROUNDS = 12

# Characters allowed in auto-generated API keys (URL-safe, no ambiguous chars).
_KEY_ALPHABET = string.ascii_letters + string.digits


def _prepare_password(plain: str) -> bytes:
    """SHA-256 pre-hash before bcrypt so passwords longer than bcrypt's
    72-byte limit are handled safely and deterministically.

    This is the approach recommended by OWASP Password Storage Cheat Sheet
    (https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
    for bcrypt when supporting passwords >72 bytes.

    Migration note: hashes produced by this function are NOT compatible with
    hashes produced by passlib's CryptContext, because passlib passes the raw
    password bytes to bcrypt whereas this function passes SHA-256(password).
    Any existing passlib-generated hashes must be re-hashed on next login or
    via a one-time migration before deploying this change to a system that
    already has users.
    """
    return hashlib.sha256(plain.encode("utf-8")).digest()

def hash_password(plain: str) -> str:
    """Return the bcrypt hash of *plain*."""
    return bcrypt.hashpw(_prepare_password(plain), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return bcrypt.checkpw(_prepare_password(plain), hashed.encode("utf-8"))


def generate_secure_token(nbytes: int = 32) -> str:
    """Return a URL-safe random token of *nbytes* bytes (base64-encoded)."""
    return secrets.token_urlsafe(nbytes)


def generate_api_key(length: int = 40) -> str:
    """Return a random API key of *length* characters from a safe alphabet."""
    return "".join(secrets.choice(_KEY_ALPHABET) for _ in range(length))


def constant_time_compare(a: str, b: str) -> bool:
    """Timing-safe string comparison (OWASP A07 — avoid timing attacks)."""
    return secrets.compare_digest(a.encode(), b.encode())
