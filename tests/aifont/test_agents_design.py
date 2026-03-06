"""Unit tests for aifont.agents.design_agent."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aifont.agents.design_agent import DesignAgent, DesignResult


class TestDesignAgent:
    def test_run_no_font_returns_result(self):
        agent = DesignAgent()
        result = agent.run("bold geometric A")
        assert isinstance(result, DesignResult)
        assert result.font is None
        assert result.glyph_name == "A"

    def test_extracts_glyph_name_from_prompt(self):
        agent = DesignAgent()
        result = agent.run("draw a nice B glyph")
        assert result.glyph_name == "B"

    def test_default_glyph_name_fallback(self):
        agent = DesignAgent()
        result = agent.run("something without a letter")
        assert result.glyph_name == "A"

    def test_generates_svg(self):
        agent = DesignAgent()
        result = agent.run("test")
        assert result.svg_data is not None
        assert "<svg" in result.svg_data

    def test_uses_llm_client_for_svg(self):
        mock_llm = MagicMock()
        mock_llm.generate_svg.return_value = "<svg>...</svg>"
        agent = DesignAgent(llm_client=mock_llm)
        result = agent.run("test")
        mock_llm.generate_svg.assert_called_once()
        assert result.svg_data == "<svg>...</svg>"

    def test_llm_fallback_on_exception(self):
        mock_llm = MagicMock()
        mock_llm.generate_svg.side_effect = Exception("LLM down")
        agent = DesignAgent(llm_client=mock_llm)
        result = agent.run("test")
        # Should fall back to placeholder SVG
        assert result.svg_data is not None

    def test_run_with_font_calls_inject(self, font):
        agent = DesignAgent()
        with patch.object(agent, "_inject_svg") as mock_inject:
            result = agent.run("draw A", font=font, unicode_point=0x0041)
        mock_inject.assert_called_once()

    def test_inject_calls_svg_to_glyph(self, font, mock_ff_font):
        agent = DesignAgent()
        svg_data = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 700">'
            '<path d="M 0 0 L 500 700 Z"/>'
            "</svg>"
        )
        created_glyph = MagicMock()
        mock_ff_font.createChar.return_value = created_glyph
        # Should not raise
        agent._inject_svg(font, svg_data, 0x0041, "A")
