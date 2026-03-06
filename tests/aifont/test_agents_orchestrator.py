"""Unit tests for aifont.agents.orchestrator."""

from __future__ import annotations

from unittest.mock import MagicMock

from aifont.agents.orchestrator import AgentResult, Orchestrator, PipelineResult


class TestAgentResult:
    def test_success_result(self):
        r = AgentResult(agent_name="design", success=True, confidence=0.9)
        assert r.success is True
        assert r.agent_name == "design"

    def test_failed_result(self):
        r = AgentResult(agent_name="qa", success=False, confidence=0.0, error="oops")
        assert r.success is False
        assert r.error == "oops"


class TestPipelineResult:
    def test_success_all_steps(self):
        result = PipelineResult(
            prompt="test",
            steps=[
                AgentResult("a", True, 1.0),
                AgentResult("b", True, 0.8),
            ],
        )
        assert result.success is True

    def test_failure_if_any_failed(self):
        result = PipelineResult(
            prompt="test",
            steps=[
                AgentResult("a", True, 1.0),
                AgentResult("b", False, 0.0, error="fail"),
            ],
        )
        assert result.success is False

    def test_errors_list(self):
        result = PipelineResult(
            prompt="test",
            steps=[
                AgentResult("a", False, 0.0, error="err1"),
                AgentResult("b", False, 0.0, error="err2"),
            ],
        )
        assert "err1" in result.errors
        assert "err2" in result.errors


class TestOrchestrator:
    def test_run_with_no_font(self):
        orch = Orchestrator()
        result = orch.run("Test prompt")
        assert isinstance(result, PipelineResult)
        assert result.prompt == "Test prompt"

    def test_run_with_mock_agents(self, font):
        orch = Orchestrator()

        mock_agent = MagicMock()
        mock_agent_result = MagicMock()
        mock_agent_result.confidence = 1.0
        mock_agent.run.return_value = mock_agent_result

        orch.register("design", mock_agent)
        orch.register("metrics", mock_agent)
        orch.register("qa", mock_agent)
        orch.register("export", mock_agent)

        result = orch.run("bold geometric A", font=font)
        assert isinstance(result, PipelineResult)

    def test_agent_exception_captured(self, font):
        orch = Orchestrator(max_retries=0)

        bad_agent = MagicMock()
        bad_agent.run.side_effect = RuntimeError("agent failed")

        orch.register("design", bad_agent)

        result = orch.run("test", font=font)
        assert any(s.error is not None for s in result.steps)

    def test_register_overrides_default(self):
        orch = Orchestrator()
        agent = MagicMock()
        orch.register("design", agent)
        assert orch._agents["design"] is agent

    def test_confidence_threshold(self, font):
        orch = Orchestrator(max_retries=1)

        low_conf_result = MagicMock()
        low_conf_result.confidence = 0.3  # below threshold → retry

        high_conf_result = MagicMock()
        high_conf_result.confidence = 0.9

        agent = MagicMock()
        agent.run.side_effect = [low_conf_result, high_conf_result]
        orch.register("design", agent)

        # Run just the first step by disabling others
        orch._build_pipeline = lambda p, f: [(agent.run, "design")]
        result = orch.run("test", font=font)
        assert result.steps[0].success is True

    def test_run_step_explicit_failure_no_retry(self, font):
        """_run_step: agent returns explicit success=False, no retries left."""
        orch = Orchestrator(max_retries=0)

        failure_result = MagicMock()
        failure_result.success = False
        failure_result.message = "explicit failure"
        failure_result.confidence = 0.0
        agent = MagicMock()
        agent.run.return_value = failure_result
        orch.register("design", agent)
        orch._build_pipeline = lambda p, f: [(agent.run, "design")]

        result = orch.run("test", font=font)
        assert result.steps[0].success is False

    def test_run_step_explicit_failure_with_retry(self, font):
        """_run_step: agent returns explicit success=False, retried once."""
        orch = Orchestrator(max_retries=1)

        failure = MagicMock()
        failure.success = False
        failure.message = "fail"
        failure.confidence = 0.0

        success = MagicMock()
        success.success = True
        success.confidence = 0.9

        agent = MagicMock()
        agent.run.side_effect = [failure, success]
        orch.register("design", agent)
        orch._build_pipeline = lambda p, f: [(agent.run, "design")]

        result = orch.run("test", font=font)
        assert result.steps[0].success is True

    def test_run_step_fallback_all_low_confidence(self, font):
        """When all retries are exhausted with low confidence, the orchestrator
        accepts the last result as successful (does not discard it)."""
        orch = Orchestrator(max_retries=1, confidence_threshold=0.9)

        low = MagicMock()
        low.success = True
        low.confidence = 0.3
        agent = MagicMock()
        agent.run.return_value = low  # always returns low confidence
        orch.register("design", agent)
        orch._build_pipeline = lambda p, f: [(agent.run, "design")]

        # After max_retries exhausted, last attempt always returns success=True
        result = orch.run("test", font=font)
        assert result.steps[0].success is True
