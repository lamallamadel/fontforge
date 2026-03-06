"""Unit tests for aifont.auth.security — password hashing and token generation."""

from __future__ import annotations

import pytest


def test_hash_password_returns_bcrypt_hash():
    from aifont.auth.security import hash_password

    h = hash_password("correct horse battery staple")
    assert h.startswith("$2b$")


def test_verify_password_correct():
    from aifont.auth.security import hash_password, verify_password

    plain = "my_secret_password"
    h = hash_password(plain)
    assert verify_password(plain, h) is True


def test_verify_password_wrong():
    from aifont.auth.security import hash_password, verify_password

    h = hash_password("correct_password")
    assert verify_password("wrong_password", h) is False


def test_verify_password_long_password():
    """Passwords longer than 72 bytes should be handled via SHA-256 pre-hashing."""
    from aifont.auth.security import hash_password, verify_password

    long_pw = "x" * 100
    h = hash_password(long_pw)
    assert verify_password(long_pw, h) is True
    assert verify_password("y" * 100, h) is False


def test_generate_secure_token_default_length():
    from aifont.auth.security import generate_secure_token

    token = generate_secure_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_generate_secure_token_custom_length():
    from aifont.auth.security import generate_secure_token

    short = generate_secure_token(nbytes=8)
    long_ = generate_secure_token(nbytes=64)
    assert len(long_) > len(short)


def test_generate_secure_token_uniqueness():
    from aifont.auth.security import generate_secure_token

    tokens = {generate_secure_token() for _ in range(10)}
    assert len(tokens) == 10


def test_generate_api_key_length():
    from aifont.auth.security import generate_api_key

    key = generate_api_key(length=40)
    assert len(key) == 40


def test_generate_api_key_custom_length():
    from aifont.auth.security import generate_api_key

    key = generate_api_key(length=20)
    assert len(key) == 20


def test_generate_api_key_charset():
    from aifont.auth.security import generate_api_key

    key = generate_api_key(length=100)
    assert key.isalnum()


def test_generate_api_key_uniqueness():
    from aifont.auth.security import generate_api_key

    keys = {generate_api_key() for _ in range(10)}
    assert len(keys) == 10


def test_constant_time_compare_equal():
    from aifont.auth.security import constant_time_compare

    assert constant_time_compare("abc", "abc") is True


def test_constant_time_compare_unequal():
    from aifont.auth.security import constant_time_compare

    assert constant_time_compare("abc", "xyz") is False


def test_constant_time_compare_empty():
    from aifont.auth.security import constant_time_compare

    assert constant_time_compare("", "") is True


def test_prepare_password_returns_bytes():
    from aifont.auth.security import _prepare_password

    result = _prepare_password("password")
    assert isinstance(result, bytes)
    assert len(result) == 64  # SHA-256 hex digest = 64 hex chars
