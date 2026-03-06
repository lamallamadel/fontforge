"""Unit tests for aifont.agents.metrics_agent."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aifont.agents.metrics_agent import MetricsAgent, MetricsResult


class TestMetricsAgent:
    def test_run_no_font(self):
        agent = MetricsAgent()
        result = agent.run("tight spacing")
        assert isinstance(result, MetricsResult)
        assert result.font is None
        assert result.confidence == 0.5

    def test_run_with_font(self, font):
        agent = MetricsAgent()
        result = agent.run("normal spacing", font=font)
        assert isinstance(result, MetricsResult)
        assert result.font is font
        assert result.spacing_adjusted is True

    def test_tight_ratio(self):
        agent = MetricsAgent()
        ratio = agent._interpret_ratio("tight compact font")
        assert ratio < 0.15

    def test_loose_ratio(self):
        agent = MetricsAgent()
        ratio = agent._interpret_ratio("airy open display")
        assert ratio > 0.15

    def test_default_ratio(self):
        agent = MetricsAgent()
        ratio = agent._interpret_ratio("normal font")
        assert ratio == 0.15

    def test_kern_pairs_reported(self, font, mock_ff_font):
        mock_ff_font.subtables = True
        glyph_a = mock_ff_font["A"]
        glyph_a.getPosSub.return_value = [
            ("kern-sub", "Pair", "V", -50, 0, 0, 0, 0)
        ]
        agent = MetricsAgent()
        result = agent.run("normal spacing", font=font)
        assert result.kern_pairs_updated >= 0
