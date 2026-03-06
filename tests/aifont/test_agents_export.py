"""Unit tests for aifont.agents.export_agent."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aifont.agents.export_agent import ExportAgent, ExportResult, _TARGET_FORMATS


class TestExportAgent:
    def test_run_no_font(self):
        agent = ExportAgent()
        result = agent.run("export for web")
        assert isinstance(result, ExportResult)
        assert result.success is False
        assert "No font" in (result.error or "")

    def test_format_selection_web(self):
        agent = ExportAgent()
        assert agent._choose_format("export for web") == "woff2"

    def test_format_selection_app(self):
        agent = ExportAgent()
        assert agent._choose_format("mobile app font") == "otf"

    def test_format_selection_desktop(self):
        agent = ExportAgent()
        assert agent._choose_format("desktop font") == "ttf"

    def test_format_selection_default(self):
        agent = ExportAgent()
        assert agent._choose_format("just export it") == "otf"

    def test_run_with_font_calls_export(self, font, mock_ff_font, tmp_path):
        out = str(tmp_path / "out.otf")
        agent = ExportAgent()
        with patch("aifont.agents.export_agent.ExportAgent._export") as mock_exp:
            result = agent.run("export for app", font=font, output_path=out)
        mock_exp.assert_called_once_with(font, out, "otf")
        assert result.success is True

    def test_run_captures_export_error(self, font):
        agent = ExportAgent()
        with patch.object(agent, "_export", side_effect=Exception("disk full")):
            result = agent.run("export", font=font, output_path="/tmp/out.otf")
        assert result.success is False
        assert "disk full" in (result.error or "")

    def test_target_formats_coverage(self):
        assert "web" in _TARGET_FORMATS
        assert "print" in _TARGET_FORMATS
        assert "app" in _TARGET_FORMATS
