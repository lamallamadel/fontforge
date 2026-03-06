"""OAuth2 (Google & GitHub) integration helpers."""

from __future__ import annotations

import os

import httpx

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI: str = os.environ.get(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/oauth2/google/callback"
)

GITHUB_CLIENT_ID: str = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET: str = os.environ.get("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI: str = os.environ.get(
    "GITHUB_REDIRECT_URI", "http://localhost:8000/auth/oauth2/github/callback"
)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"
GITHUB_EMAIL_URL = "https://api.github.com/user/emails"


# ---------------------------------------------------------------------------
# Authorization URL helpers
# ---------------------------------------------------------------------------


def google_auth_url(state: str) -> str:
    """Return the Google OAuth2 authorization redirect URL."""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


def github_auth_url(state: str) -> str:
    """Return the GitHub OAuth2 authorization redirect URL."""
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "read:user user:email",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GITHUB_AUTH_URL}?{query}"


# ---------------------------------------------------------------------------
# Token exchange
# ---------------------------------------------------------------------------


async def exchange_google_code(code: str) -> dict:
    """Exchange an authorization *code* for Google OAuth2 tokens.

    Returns a dict with ``access_token``, ``id_token``, etc.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def exchange_github_code(code: str) -> dict:
    """Exchange an authorization *code* for a GitHub access token.

    Returns a dict with ``access_token``, ``token_type``, etc.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "code": code,
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "redirect_uri": GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# User-info fetchers
# ---------------------------------------------------------------------------


async def get_google_user_info(access_token: str) -> dict:
    """Fetch the authenticated user's profile from Google."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


async def get_github_user_info(access_token: str) -> dict:
    """Fetch the authenticated user's profile from GitHub.

    Also resolves the primary email when the ``email`` field is ``None``
    (common for users with private email settings).
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GITHUB_USERINFO_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        resp.raise_for_status()
        info = resp.json()

        if not info.get("email"):
            email_resp = await client.get(
                GITHUB_EMAIL_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            email_resp.raise_for_status()
            emails = email_resp.json()
            primary = next(
                (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                None,
            )
            info["email"] = primary

    return info
