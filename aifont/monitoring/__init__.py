"""aifont.monitoring — Observability layer: Prometheus metrics, Sentry, structured logging."""

from .logging import get_logger, setup_logging
from .metrics import (
    ACTIVE_CONNECTIONS,
    AGENT_RUN_COUNT,
    AGENT_RUN_ERRORS,
    AGENT_RUN_LATENCY,
    FONT_EXPORT_COUNT,
    FONT_EXPORT_ERRORS,
    REQUEST_COUNT,
    REQUEST_IN_PROGRESS,
    REQUEST_LATENCY,
    setup_metrics,
    track_agent_run,
    track_font_export,
    track_request,
)
from .sentry import setup_sentry

__all__ = [
    # Prometheus metrics
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "REQUEST_IN_PROGRESS",
    "AGENT_RUN_COUNT",
    "AGENT_RUN_LATENCY",
    "AGENT_RUN_ERRORS",
    "FONT_EXPORT_COUNT",
    "FONT_EXPORT_ERRORS",
    "ACTIVE_CONNECTIONS",
    "setup_metrics",
    "track_request",
    "track_agent_run",
    "track_font_export",
    # Sentry
    "setup_sentry",
    # Logging
    "setup_logging",
    "get_logger",
]
