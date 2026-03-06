"""Unit tests for aifont.agents.style_agent."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aifont.agents.style_agent import StyleAgent, StyleResult


class TestStyleAgent:
    def test_run_no_font(self):
        agent = StyleAgent()
        result = agent.run("modern sans-serif")
        assert isinstance(result, StyleResult)
        assert result.confidence == 0.5

    def test_run_no_source(self, font):
        agent = StyleAgent()
        result = agent.run("modern", font=font)
        assert result.confidence == 0.5

    def test_compute_scale_same_em(self, font):
        agent = StyleAgent()
        scale = agent._compute_scale(font, font)
        assert scale == 1.0

    def test_compute_scale_different_em(self, mock_ff_font):
        from aifont.core.font import Font

        src_ff = MagicMock()
        src_ff.em = 1000
        src_ff.__iter__ = MagicMock(return_value=iter([]))
        src_font = Font(src_ff)

        dst_ff = MagicMock()
        dst_ff.em = 2000
        dst_ff.__iter__ = MagicMock(return_value=iter([]))
        dst_font = Font(dst_ff)

        agent = StyleAgent()
        scale = agent._compute_scale(src_font, dst_font)
        assert scale == 2.0

    def test_run_copies_glyphs(self, font):
        agent = StyleAgent()
        result = agent.run("bold style", font=font, source_font=font)
        assert isinstance(result, StyleResult)
        assert result.target_font is font
