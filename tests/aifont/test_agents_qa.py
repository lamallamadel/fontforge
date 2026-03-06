"""Unit tests for aifont.agents.qa_agent."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aifont.agents.qa_agent import QAAgent, QAReport


class TestQAAgent:
    def test_run_no_font(self):
        agent = QAAgent()
        result = agent.run("check quality")
        assert isinstance(result, QAReport)
        assert result.passed is False
        assert result.confidence == 0.0

    def test_run_with_font(self, font):
        agent = QAAgent()
        result = agent.run("check font quality", font=font)
        assert isinstance(result, QAReport)

    def test_checks_populated(self, font):
        agent = QAAgent()
        result = agent.run("test", font=font)
        assert "glyph_count" in result.checks
        assert "no_errors" in result.checks
        assert "coverage" in result.checks

    def test_passed_with_valid_font(self, font):
        agent = QAAgent()
        result = agent.run("test", font=font)
        # Font has 3 glyphs, all with unicode
        assert result.checks["glyph_count"] is True

    def test_auto_fixed_list(self, font):
        agent = QAAgent()
        result = agent.run("test", font=font)
        assert isinstance(result.auto_fixed, list)

    def test_issues_remaining(self, font):
        agent = QAAgent()
        result = agent.run("test", font=font)
        assert isinstance(result.issues_remaining, list)
