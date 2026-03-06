"""Structured logging configuration for the AIFont platform.

Produces JSON log lines that are consumable by Loki + Promtail without
additional parsing.  Each log record carries:

- ``timestamp``  — ISO-8601 UTC timestamp
- ``level``      — log level string
- ``logger``     — logger name
- ``message``    — human-readable message
- ``environment`` — deployment environment
- ``service``    — always ``"aifont"``
- plus any extra fields passed to the logger

Usage::

    from aifont.monitoring.logging import setup_logging, get_logger

    setup_logging(level="INFO", environment="production")
    log = get_logger(__name__)
    log.info("Font exported", format="otf", glyph_count=42)
"""

from __future__ import annotations

import logging
import logging.config
import sys
from typing import Any

# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------

try:
    import json as _json

    class _JsonFormatter(logging.Formatter):
        """Minimal JSON log formatter — no extra dependencies required."""

        def __init__(self, environment: str = "production") -> None:
            super().__init__()
            self._environment = environment

        def format(self, record: logging.LogRecord) -> str:  # noqa: A003
            import datetime

            payload: dict[str, Any] = {
                "timestamp": datetime.datetime.fromtimestamp(
                    record.created, tz=datetime.timezone.utc
                ).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "service": "aifont",
                "environment": self._environment,
            }
            # Attach extra fields added via Logger.info("msg", extra={...})
            for key, value in record.__dict__.items():
                if key not in (
                    "name",
                    "msg",
                    "args",
                    "created",
                    "filename",
                    "funcName",
                    "levelname",
                    "levelno",
                    "lineno",
                    "message",
                    "module",
                    "msecs",
                    "pathname",
                    "process",
                    "processName",
                    "relativeCreated",
                    "stack_info",
                    "thread",
                    "threadName",
                    "exc_info",
                    "exc_text",
                ):
                    try:
                        _json.dumps(value)  # skip non-serialisable values
                        payload[key] = value
                    except (TypeError, ValueError):
                        payload[key] = str(value)

            if record.exc_info:
                payload["exception"] = self.formatException(record.exc_info)

            return _json.dumps(payload, ensure_ascii=False)

except Exception:  # pragma: no cover
    _JsonFormatter = None  # type: ignore[misc, assignment]


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

_logging_configured = False


def setup_logging(
    level: str = "INFO",
    environment: str = "production",
    json_logs: bool = True,
) -> None:
    """Configure root logging for the AIFont platform.

    Parameters
    ----------
    level:
        Minimum log level string (``"DEBUG"``, ``"INFO"``, ``"WARNING"``…).
    environment:
        Deployment environment label used in every log record.
    json_logs:
        When ``True`` (default) emit JSON lines suitable for Loki ingestion.
        When ``False`` emit plain-text logs (useful in development).
    """
    global _logging_configured

    if _logging_configured:
        return

    handler = logging.StreamHandler(sys.stdout)

    if json_logs and _JsonFormatter is not None:
        handler.setFormatter(_JsonFormatter(environment=environment))
    else:
        fmt = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
        handler.setFormatter(logging.Formatter(fmt))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=[handler],
        force=True,
    )

    # Silence overly chatty third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _logging_configured = True


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------


class _BoundLogger:
    """Thin wrapper that attaches keyword arguments as *extra* fields."""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    # ------------------------------------------------------------------
    # Log-level methods
    # ------------------------------------------------------------------

    def debug(self, message: str, **kwargs: Any) -> None:
        self._logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self._logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._logger.critical(message, extra=kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        self._logger.exception(message, extra=kwargs)

    def bind(self, **kwargs: Any) -> _BoundLogger:
        """Return a child logger with permanent extra context."""
        child = _BoundLogger(self._logger.name)

        # Create new bound methods that always include kwargs
        _kwargs = kwargs

        def _make_method(level_method):  # type: ignore[no-untyped-def]
            def method(message: str, **extra: Any) -> None:
                merged = {**_kwargs, **extra}
                level_method(message, extra=merged)

            return method

        child.debug = _make_method(self._logger.debug)  # type: ignore[method-assign]
        child.info = _make_method(self._logger.info)  # type: ignore[method-assign]
        child.warning = _make_method(self._logger.warning)  # type: ignore[method-assign]
        child.error = _make_method(self._logger.error)  # type: ignore[method-assign]
        child.critical = _make_method(self._logger.critical)  # type: ignore[method-assign]
        child.exception = _make_method(self._logger.exception)  # type: ignore[method-assign]
        return child


def get_logger(name: str) -> _BoundLogger:
    """Return a structured logger for *name*.

    Example::

        log = get_logger(__name__)
        log.info("Processing request", request_id="abc-123", user_id=42)
    """
    return _BoundLogger(name)
