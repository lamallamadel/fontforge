"""FastAPI middleware for automatic Prometheus metrics collection.

Attach :class:`PrometheusMiddleware` to a FastAPI (Starlette) application to
instrument every incoming HTTP request with zero boilerplate in route
handlers.

Usage::

    from fastapi import FastAPI
    from aifont.monitoring.middleware import PrometheusMiddleware

    app = FastAPI()
    app.add_middleware(PrometheusMiddleware)
"""

from __future__ import annotations

import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match
from starlette.types import ASGIApp

from .metrics import (
    ACTIVE_CONNECTIONS,
    REQUEST_COUNT,
    REQUEST_IN_PROGRESS,
    REQUEST_LATENCY,
)


def _get_route_template(request: Request) -> str:
    """Return the matched route template, falling back to the raw path."""
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "path", request.url.path)
    return request.url.path


class PrometheusMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that records HTTP request metrics.

    Tracks:
    - ``aifont_http_requests_total``         — request count by method / endpoint / status
    - ``aifont_http_request_duration_seconds`` — request latency histogram
    - ``aifont_http_requests_in_progress``    — concurrent requests gauge
    - ``aifont_active_connections``           — open connections gauge
    """

    def __init__(self, app: ASGIApp, **kwargs: object) -> None:
        super().__init__(app, **kwargs)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        method = request.method
        # Resolve parameterised route template so labels remain low-cardinality.
        endpoint = _get_route_template(request)

        ACTIVE_CONNECTIONS.inc()
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
        start = time.perf_counter()

        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            raise
        finally:
            elapsed = time.perf_counter() - start
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
            ACTIVE_CONNECTIONS.dec()
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code),
            ).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(elapsed)
