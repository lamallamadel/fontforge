"""Prometheus metrics for the AIFont platform.

Exposes counters, histograms and gauges used across the API and agent
layers so that a Prometheus scrape endpoint can collect them.

Usage::

    from aifont.monitoring.metrics import setup_metrics, track_request

    # Call once at startup (no-op if already called)
    setup_metrics(app_version="1.0.0", environment="production")

    # Manual tracking helpers
    with track_request("POST", "/fonts/generate", 201):
        ...
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Generator

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# Use the global registry by default so that the /metrics endpoint served by
# prometheus_client.make_asgi_app() can reach all metrics without extra wiring.
_registry: CollectorRegistry = REGISTRY

# ---------------------------------------------------------------------------
# HTTP request metrics
# ---------------------------------------------------------------------------

REQUEST_COUNT: Counter = Counter(
    "aifont_http_requests_total",
    "Total number of HTTP requests handled by the AIFont API.",
    ["method", "endpoint", "status_code"],
    registry=_registry,
)

REQUEST_LATENCY: Histogram = Histogram(
    "aifont_http_request_duration_seconds",
    "Latency of HTTP requests in seconds.",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=_registry,
)

REQUEST_IN_PROGRESS: Gauge = Gauge(
    "aifont_http_requests_in_progress",
    "Number of HTTP requests currently being processed.",
    ["method", "endpoint"],
    registry=_registry,
)

# ---------------------------------------------------------------------------
# Agent metrics
# ---------------------------------------------------------------------------

AGENT_RUN_COUNT: Counter = Counter(
    "aifont_agent_runs_total",
    "Total number of agent pipeline executions.",
    ["agent_name", "status"],
    registry=_registry,
)

AGENT_RUN_LATENCY: Histogram = Histogram(
    "aifont_agent_run_duration_seconds",
    "Latency of a single agent run in seconds.",
    ["agent_name"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
    registry=_registry,
)

AGENT_RUN_ERRORS: Counter = Counter(
    "aifont_agent_run_errors_total",
    "Total number of agent run failures.",
    ["agent_name", "error_type"],
    registry=_registry,
)

# ---------------------------------------------------------------------------
# Font export metrics
# ---------------------------------------------------------------------------

FONT_EXPORT_COUNT: Counter = Counter(
    "aifont_font_exports_total",
    "Total number of font files generated.",
    ["format"],
    registry=_registry,
)

FONT_EXPORT_ERRORS: Counter = Counter(
    "aifont_font_export_errors_total",
    "Total number of failed font exports.",
    ["format", "error_type"],
    registry=_registry,
)

FONT_EXPORT_SIZE_BYTES: Histogram = Histogram(
    "aifont_font_export_size_bytes",
    "Size of exported font files in bytes.",
    ["format"],
    buckets=(
        1_024,
        10_240,
        51_200,
        102_400,
        512_000,
        1_048_576,
        5_242_880,
        10_485_760,
    ),
    registry=_registry,
)

# ---------------------------------------------------------------------------
# Resource / system metrics
# ---------------------------------------------------------------------------

ACTIVE_CONNECTIONS: Gauge = Gauge(
    "aifont_active_connections",
    "Number of currently open client connections.",
    registry=_registry,
)

# ---------------------------------------------------------------------------
# App info
# ---------------------------------------------------------------------------

APP_INFO: Info = Info(
    "aifont_app",
    "AIFont application metadata.",
    registry=_registry,
)

_metrics_initialised = False


def setup_metrics(app_version: str = "unknown", environment: str = "production") -> None:
    """Record static app metadata into the info metric.

    Call this **once** during application startup.  Subsequent calls are
    silently ignored so that the function is safe to call from tests or
    multiple entry points.
    """
    global _metrics_initialised
    if _metrics_initialised:
        return
    APP_INFO.info({"version": app_version, "environment": environment})
    _metrics_initialised = True


# ---------------------------------------------------------------------------
# Context-manager helpers
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def track_request(
    method: str,
    endpoint: str,
    status_code: int = 200,
) -> Generator[None, None, None]:
    """Context manager that records HTTP request count and latency.

    The *status_code* label is applied on exit so that callers can update it
    after the response has been produced::

        with track_request("POST", "/fonts/generate") as req:
            ...

    Example tracking a non-200 outcome::

        status = 200
        with track_request("GET", "/fonts/1", status):
            try:
                result = do_work()
            except NotFound:
                status = 404
                raise
    """
    REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code),
        ).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(elapsed)


@contextlib.contextmanager
def track_agent_run(agent_name: str) -> Generator[None, None, None]:
    """Context manager that records agent run count, latency and errors.

    Example::

        with track_agent_run("DesignAgent"):
            result = design_agent.run(prompt)
    """
    start = time.perf_counter()
    try:
        yield
        AGENT_RUN_COUNT.labels(agent_name=agent_name, status="success").inc()
    except Exception as exc:
        AGENT_RUN_COUNT.labels(agent_name=agent_name, status="error").inc()
        AGENT_RUN_ERRORS.labels(agent_name=agent_name, error_type=type(exc).__name__).inc()
        raise
    finally:
        elapsed = time.perf_counter() - start
        AGENT_RUN_LATENCY.labels(agent_name=agent_name).observe(elapsed)


@contextlib.contextmanager
def track_font_export(
    fmt: str,
    size_bytes: int = 0,
) -> Generator[None, None, None]:
    """Context manager that records font export metrics.

    Example::

        with track_font_export("otf", size_bytes=len(data)):
            export_otf(font, path)
    """
    try:
        yield
        FONT_EXPORT_COUNT.labels(format=fmt).inc()
        if size_bytes > 0:
            FONT_EXPORT_SIZE_BYTES.labels(format=fmt).observe(size_bytes)
    except Exception as exc:
        FONT_EXPORT_ERRORS.labels(format=fmt, error_type=type(exc).__name__).inc()
        raise
