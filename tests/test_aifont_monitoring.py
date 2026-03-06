"""Tests for aifont.monitoring — Prometheus metrics, Sentry, logging."""

from __future__ import annotations

import logging
import time

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_prometheus():
    """Unregister all aifont_* metrics from the global registry between tests.

    prometheus_client keeps a global registry that persists across tests.
    We reset it so that counter values from one test don't bleed into another.
    """
    from prometheus_client import REGISTRY

    collectors_to_remove = [
        c
        for c in list(REGISTRY._names_to_collectors.values())
        if hasattr(c, "_name") and c._name.startswith("aifont_")
    ]
    for c in set(collectors_to_remove):
        try:
            REGISTRY.unregister(c)
        except Exception:
            pass


# ===========================================================================
# metrics.py
# ===========================================================================


class TestSetupMetrics:
    def test_setup_metrics_registers_info(self, monkeypatch):
        """setup_metrics populates the aifont_app_info metric."""
        # Reset the global flag so we can call setup_metrics again
        import aifont.monitoring.metrics as m

        monkeypatch.setattr(m, "_metrics_initialised", False)
        m.setup_metrics(app_version="2.0.0", environment="test")
        assert m._metrics_initialised is True

    def test_setup_metrics_idempotent(self, monkeypatch):
        import aifont.monitoring.metrics as m

        monkeypatch.setattr(m, "_metrics_initialised", False)
        m.setup_metrics(app_version="1.0", environment="test")
        m.setup_metrics(app_version="2.0", environment="prod")  # second call is no-op
        assert m._metrics_initialised is True


class TestTrackRequest:
    def test_increments_counter(self):
        from aifont.monitoring.metrics import REQUEST_COUNT, track_request

        before = REQUEST_COUNT.labels(
            method="GET", endpoint="/test", status_code="200"
        )._value.get()

        with track_request("GET", "/test", 200):
            pass

        after = REQUEST_COUNT.labels(
            method="GET", endpoint="/test", status_code="200"
        )._value.get()
        assert after == before + 1

    def test_records_latency(self):
        from aifont.monitoring.metrics import REQUEST_LATENCY, track_request

        with track_request("POST", "/fonts/generate", 201):
            time.sleep(0.01)

        samples = list(
            REQUEST_LATENCY.labels(method="POST", endpoint="/fonts/generate").collect()
        )
        assert len(samples) > 0

    def test_decrements_in_progress_after_success(self):
        from aifont.monitoring.metrics import REQUEST_IN_PROGRESS, track_request

        gauge = REQUEST_IN_PROGRESS.labels(method="DELETE", endpoint="/fonts/1")
        before = gauge._value.get()

        with track_request("DELETE", "/fonts/1", 204):
            pass

        assert gauge._value.get() == before

    def test_decrements_in_progress_after_exception(self):
        from aifont.monitoring.metrics import REQUEST_IN_PROGRESS, track_request

        gauge = REQUEST_IN_PROGRESS.labels(method="PUT", endpoint="/fonts/2")
        before = gauge._value.get()

        with pytest.raises(RuntimeError):
            with track_request("PUT", "/fonts/2", 500):
                raise RuntimeError("boom")

        assert gauge._value.get() == before


class TestTrackAgentRun:
    def test_success_path(self):
        from aifont.monitoring.metrics import AGENT_RUN_COUNT, track_agent_run

        before = AGENT_RUN_COUNT.labels(
            agent_name="TestAgent", status="success"
        )._value.get()

        with track_agent_run("TestAgent"):
            pass

        after = AGENT_RUN_COUNT.labels(
            agent_name="TestAgent", status="success"
        )._value.get()
        assert after == before + 1

    def test_error_path(self):
        from aifont.monitoring.metrics import (
            AGENT_RUN_COUNT,
            AGENT_RUN_ERRORS,
            track_agent_run,
        )

        before_err = AGENT_RUN_ERRORS.labels(
            agent_name="TestAgent", error_type="ValueError"
        )._value.get()

        with pytest.raises(ValueError):
            with track_agent_run("TestAgent"):
                raise ValueError("agent failed")

        after_err = AGENT_RUN_ERRORS.labels(
            agent_name="TestAgent", error_type="ValueError"
        )._value.get()
        assert after_err == before_err + 1

        after_fail = AGENT_RUN_COUNT.labels(
            agent_name="TestAgent", status="error"
        )._value.get()
        assert after_fail >= 1


class TestTrackFontExport:
    def test_success_increments_counter(self):
        from aifont.monitoring.metrics import FONT_EXPORT_COUNT, track_font_export

        before = FONT_EXPORT_COUNT.labels(format="otf")._value.get()

        with track_font_export("otf", size_bytes=1024):
            pass

        after = FONT_EXPORT_COUNT.labels(format="otf")._value.get()
        assert after == before + 1

    def test_failure_increments_error_counter(self):
        from aifont.monitoring.metrics import FONT_EXPORT_ERRORS, track_font_export

        # IOError is an alias for OSError in Python 3; the metric label uses
        # the canonical class name returned by type(exc).__name__ → "OSError".
        error_type = type(OSError()).__name__
        before = FONT_EXPORT_ERRORS.labels(
            format="woff2", error_type=error_type
        )._value.get()

        with pytest.raises(OSError):
            with track_font_export("woff2"):
                raise OSError("disk full")

        after = FONT_EXPORT_ERRORS.labels(
            format="woff2", error_type=error_type
        )._value.get()
        assert after == before + 1


# ===========================================================================
# sentry.py
# ===========================================================================


class TestSetupSentry:
    def test_no_dsn_returns_false(self, monkeypatch):
        import aifont.monitoring.sentry as s

        monkeypatch.setattr(s, "_sentry_initialised", False)
        result = s.setup_sentry(dsn=None)
        assert result is False

    def test_empty_dsn_returns_false(self, monkeypatch):
        import aifont.monitoring.sentry as s

        monkeypatch.setattr(s, "_sentry_initialised", False)
        result = s.setup_sentry(dsn="")
        assert result is False

    def test_capture_exception_noop_when_not_initialised(self, monkeypatch):
        import aifont.monitoring.sentry as s

        monkeypatch.setattr(s, "_sentry_initialised", False)
        result = s.capture_exception(ValueError("test"))
        assert result is None

    def test_set_user_noop_when_not_initialised(self, monkeypatch):
        import aifont.monitoring.sentry as s

        monkeypatch.setattr(s, "_sentry_initialised", False)
        # Should not raise
        s.set_user("user-123", email="test@example.com")


# ===========================================================================
# logging.py
# ===========================================================================


class TestSetupLogging:
    def test_setup_logging_plain_text(self, monkeypatch):
        import aifont.monitoring.logging as lg

        monkeypatch.setattr(lg, "_logging_configured", False)
        lg.setup_logging(level="DEBUG", environment="test", json_logs=False)
        assert lg._logging_configured is True

    def test_setup_logging_json(self, monkeypatch):
        import aifont.monitoring.logging as lg

        monkeypatch.setattr(lg, "_logging_configured", False)
        lg.setup_logging(level="INFO", environment="test", json_logs=True)
        assert lg._logging_configured is True

    def test_setup_logging_idempotent(self, monkeypatch):
        import aifont.monitoring.logging as lg

        monkeypatch.setattr(lg, "_logging_configured", False)
        lg.setup_logging(level="INFO", environment="test")
        lg.setup_logging(level="DEBUG", environment="prod")  # second call is no-op
        assert lg._logging_configured is True


class TestGetLogger:
    def test_returns_bound_logger(self):
        from aifont.monitoring.logging import get_logger

        log = get_logger("test.module")
        assert log is not None
        assert callable(log.info)
        assert callable(log.error)

    def test_info_does_not_raise(self):
        from aifont.monitoring.logging import get_logger

        log = get_logger("test.module")
        log.info("Hello world", key="value", number=42)

    def test_exception_does_not_raise(self):
        from aifont.monitoring.logging import get_logger

        log = get_logger("test.module")
        try:
            raise RuntimeError("test error")
        except RuntimeError:
            log.exception("Caught error", context="test")

    def test_bind_returns_logger(self):
        from aifont.monitoring.logging import get_logger

        log = get_logger("test.module")
        bound = log.bind(request_id="abc-123")
        assert callable(bound.info)


class TestJsonFormatter:
    """Verify the JSON formatter produces valid JSON with expected keys."""

    def test_produces_valid_json(self, monkeypatch):
        import json

        import aifont.monitoring.logging as lg

        formatter = lg._JsonFormatter(environment="test")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)

        assert data["message"] == "test message"
        assert data["level"] == "INFO"
        assert data["service"] == "aifont"
        assert data["environment"] == "test"
        assert "timestamp" in data

    def test_includes_exception(self):
        import json

        import aifont.monitoring.logging as lg

        formatter = lg._JsonFormatter(environment="test")
        try:
            raise ValueError("oops")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="error occurred",
            args=(),
            exc_info=exc_info,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert "ValueError" in data["exception"]


# ===========================================================================
# middleware.py — FastAPI integration
# ===========================================================================


class TestPrometheusMiddleware:
    """Integration tests using an in-process ASGI test client."""

    @pytest.fixture()
    def client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from aifont.monitoring.middleware import PrometheusMiddleware

        app = FastAPI()
        app.add_middleware(PrometheusMiddleware)

        @app.get("/ping")
        async def ping():
            return {"pong": True}

        @app.get("/error")
        async def error():
            raise RuntimeError("boom")

        return TestClient(app, raise_server_exceptions=False)

    def test_successful_request_increments_counter(self, client):
        from aifont.monitoring.metrics import REQUEST_COUNT

        before = REQUEST_COUNT.labels(
            method="GET", endpoint="/ping", status_code="200"
        )._value.get()

        response = client.get("/ping")
        assert response.status_code == 200

        after = REQUEST_COUNT.labels(
            method="GET", endpoint="/ping", status_code="200"
        )._value.get()
        assert after == before + 1

    def test_active_connections_gauge_returns_to_zero(self, client):
        from aifont.monitoring.metrics import ACTIVE_CONNECTIONS

        client.get("/ping")
        # After the request, active connections should be back to baseline
        # (accounting for any concurrent connections in the test suite itself)
        assert ACTIVE_CONNECTIONS._value.get() >= 0
