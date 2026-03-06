"""Sentry error-tracking integration for the AIFont platform.

Call :func:`setup_sentry` once at application startup with the DSN from your
environment.  The function is a no-op when the DSN is not provided so that
development environments do not require a Sentry account.

Usage::

    from aifont.monitoring.sentry import setup_sentry

    setup_sentry(
        dsn="https://...@sentry.io/...",
        environment="production",
        release="1.0.0",
        traces_sample_rate=0.1,
    )
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_sentry_initialised = False


def setup_sentry(
    dsn: str | None = None,
    environment: str = "production",
    release: str | None = None,
    traces_sample_rate: float = 0.05,
    profiles_sample_rate: float = 0.0,
) -> bool:
    """Initialise the Sentry SDK.

    Parameters
    ----------
    dsn:
        The Sentry Data Source Name.  When *None* or empty the call is a
        no-op and ``False`` is returned.
    environment:
        The deployment environment label (``"production"``, ``"staging"``, …).
    release:
        A release identifier such as a git SHA or semver string.  When
        *None* Sentry attempts to detect the release automatically.
    traces_sample_rate:
        Fraction of transactions to send for performance monitoring (0–1).
    profiles_sample_rate:
        Fraction of sampled transactions to profile (0–1).

    Returns
    -------
    bool
        ``True`` if Sentry was successfully initialised, ``False`` otherwise.
    """
    global _sentry_initialised

    if _sentry_initialised:
        return True

    if not dsn:
        logger.info("Sentry DSN not provided — error tracking disabled.")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    except ImportError:
        logger.warning(
            "sentry-sdk is not installed; error tracking disabled. "
            "Install it with: pip install sentry-sdk[fastapi]"
        )
        return False

    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR,
    )

    init_kwargs: dict = {
        "dsn": dsn,
        "environment": environment,
        "traces_sample_rate": traces_sample_rate,
        "profiles_sample_rate": profiles_sample_rate,
        "integrations": [
            sentry_logging,
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        "send_default_pii": False,
    }
    if release:
        init_kwargs["release"] = release

    sentry_sdk.init(**init_kwargs)
    _sentry_initialised = True
    logger.info("Sentry initialised (environment=%s).", environment)
    return True


def capture_exception(exc: BaseException, **extra: object) -> str | None:
    """Capture an exception in Sentry and return the event ID.

    This is a thin convenience wrapper that is a no-op when Sentry is not
    initialised.

    Parameters
    ----------
    exc:
        The exception to report.
    **extra:
        Additional key/value pairs attached to the Sentry scope for this
        event.

    Returns
    -------
    str | None
        The Sentry event ID, or ``None`` if Sentry is not active.
    """
    if not _sentry_initialised:
        return None

    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            for key, value in extra.items():
                scope.set_extra(key, value)
            return sentry_sdk.capture_exception(exc)
    except Exception:
        logger.debug("Failed to capture exception in Sentry.", exc_info=True)
        return None


def set_user(user_id: str | None, email: str | None = None) -> None:
    """Set the current user context for subsequent Sentry events.

    Safe to call when Sentry is not initialised.
    """
    if not _sentry_initialised:
        return
    try:
        import sentry_sdk

        sentry_sdk.set_user({"id": user_id, "email": email})
    except Exception:
        pass
