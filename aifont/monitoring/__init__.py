"""aifont.monitoring — Observability layer: Prometheus metrics, Sentry, structured logging."""

from .metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    REQUEST_IN_PROGRESS,
    AGENT_RUN_COUNT,
    AGENT_RUN_LATENCY,
    AGENT_RUN_ERRORS,
    FONT_EXPORT_COUNT,
    FONT_EXPORT_ERRORS,
    ACTIVE_CONNECTIONS,
    setup_metrics,
    track_request,
    track_agent_run,
    track_font_export,
)
from .sentry import setup_sentry
from .logging import setup_logging, get_logger

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
