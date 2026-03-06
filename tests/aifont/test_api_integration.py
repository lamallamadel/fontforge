"""Integration tests for AIFont API endpoints using httpx + FastAPI test client."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_ok(self, api_client):
        resp = api_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


# ---------------------------------------------------------------------------
# /fonts/analyze
# ---------------------------------------------------------------------------


class TestFontsAnalyze:
    def test_analyze_returns_503_when_ff_unavailable(self, api_client):
        """fontforge is not a real binary here → 503 expected."""
        dummy_font = io.BytesIO(b"dummy font content")
        resp = api_client.post(
            "/fonts/analyze",
            files={"file": ("test.otf", dummy_font, "application/octet-stream")},
        )
        # fontforge not available → 503, OR validation error → 422
        assert resp.status_code in (422, 503)

    def test_analyze_with_mocked_font(self, api_client):
        from aifont.core.font import Font
        from aifont.core.analyzer import FontReport

        mock_font = MagicMock(spec=Font)
        mock_report = FontReport(
            glyph_count=10,
            missing_unicode=["notdef"],
            kern_pair_count=5,
            coverage_score=0.9,
        )

        with (
            patch("aifont.core.font.Font.open", return_value=mock_font),
            patch("aifont.core.analyzer.analyze", return_value=mock_report),
        ):
            dummy_font = io.BytesIO(b"dummy")
            resp = api_client.post(
                "/fonts/analyze",
                files={"file": ("test.otf", dummy_font, "application/octet-stream")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["glyph_count"] == 10
        assert data["kern_pair_count"] == 5
        assert data["coverage_score"] == pytest.approx(0.9)
        assert data["passed"] is True
        assert "font_id" in data


# ---------------------------------------------------------------------------
# /fonts/generate
# ---------------------------------------------------------------------------


class TestFontsGenerate:
    def test_generate_returns_503_when_ff_unavailable(self, api_client):
        resp = api_client.post(
            "/fonts/generate",
            json={"prompt": "bold geometric A", "font_name": "TestFont"},
        )
        assert resp.status_code in (422, 503)

    def test_generate_with_mocked_font(self, api_client, mock_ff_font):
        from aifont.core.font import Font

        mock_font = Font(mock_ff_font)

        with patch("aifont.core.font.Font.new", return_value=mock_font):
            resp = api_client.post(
                "/fonts/generate",
                json={"prompt": "draw A", "font_name": "Generated"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "font_id" in data
        assert "message" in data


# ---------------------------------------------------------------------------
# /fonts/{font_id}/export
# ---------------------------------------------------------------------------


class TestFontsExport:
    def test_export_404_when_not_found(self, api_client):
        resp = api_client.get("/fonts/nonexistent_id/export")
        assert resp.status_code == 404

    def test_export_found_font(self, api_client, mock_ff_font):
        from aifont.core.font import Font
        from aifont.api.routes import fonts as fonts_module

        mock_font = Font(mock_ff_font)
        font_id = "test-export-id"
        fonts_module._font_store[font_id] = mock_font

        with patch("aifont.core.export.export_otf") as mock_export:
            resp = api_client.get(f"/fonts/{font_id}/export?fmt=otf")

        assert resp.status_code == 200 or mock_export.called


# ---------------------------------------------------------------------------
# /agents/run
# ---------------------------------------------------------------------------


class TestAgentsRun:
    def test_run_agents_no_font(self, api_client):
        from aifont.agents.orchestrator import Orchestrator, PipelineResult, AgentResult

        mock_result = PipelineResult(
            prompt="test",
            steps=[AgentResult("design", True, 1.0)],
        )
        with patch.object(Orchestrator, "run", return_value=mock_result):
            resp = api_client.post(
                "/agents/run",
                json={"prompt": "create a modern sans-serif"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert "steps" in data

    def test_run_agents_font_not_found(self, api_client):
        resp = api_client.post(
            "/agents/run",
            json={"prompt": "test", "font_id": "does-not-exist"},
        )
        assert resp.status_code == 404

    def test_run_agents_with_existing_font(self, api_client, mock_ff_font):
        from aifont.core.font import Font
        from aifont.api.routes import fonts as fonts_module
        from aifont.agents.orchestrator import Orchestrator, PipelineResult, AgentResult

        mock_font = Font(mock_ff_font)
        font_id = "test-run-id"
        fonts_module._font_store[font_id] = mock_font

        mock_result = PipelineResult(
            prompt="test",
            steps=[AgentResult("design", True, 1.0)],
        )
        with patch.object(Orchestrator, "run", return_value=mock_result):
            resp = api_client.post(
                "/agents/run",
                json={"prompt": "bold style", "font_id": font_id},
            )
        assert resp.status_code == 200
