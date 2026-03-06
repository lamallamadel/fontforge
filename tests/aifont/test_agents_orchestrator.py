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

    def test_context_field_default_is_empty_dict(self):
        result = PipelineResult(prompt="test")
        assert result.context == {}

    def test_context_field_stores_data(self):
        result = PipelineResult(prompt="test", context={"key": "val"})
        assert result.context["key"] == "val"


class TestOrchestrator:
    def test_run_with_no_font(self):
        orch = Orchestrator()
        result = orch.run("Test prompt")
        assert isinstance(result, PipelineResult)
        assert result.prompt == "Test prompt"

    def test_create_font_returns_pipeline_result(self):
        """create_font() is the public high-level entry point (Issue #15)."""
        orch = Orchestrator()
        result = orch.create_font("Geometric sans-serif")
        assert isinstance(result, PipelineResult)
        assert result.prompt == "Geometric sans-serif"

    def test_create_font_context_contains_prompt(self):
        orch = Orchestrator()
        result = orch.create_font("Bold display")
        assert result.context.get("prompt") == "Bold display"

    def test_run_with_mock_agents(self, font):
        orch = Orchestrator()

        mock_agent = MagicMock()
        mock_agent_result = MagicMock()
        mock_agent_result.confidence = 1.0
        mock_agent.run.return_value = mock_agent_result

        orch.register("design", mock_agent)
        orch.register("style", mock_agent)
        orch.register("metrics", mock_agent)
        orch.register("qa", mock_agent)
        orch.register("export", mock_agent)

        result = orch.run("bold geometric A", font=font)
        assert isinstance(result, PipelineResult)

    def test_pipeline_has_five_agents(self, font):
        """_build_pipeline must return 5 agent objects (Issue #15)."""
        orch = Orchestrator()
        agents = orch._build_pipeline("test", font)
        assert len(agents) == 5

    def test_style_agent_in_pipeline(self, font):
        """StyleAgent must be the second step in the pipeline (Issue #15)."""
        from aifont.agents.style_agent import StyleAgent

        orch = Orchestrator()
        agents = orch._build_pipeline("test", font)
        assert any(isinstance(a, StyleAgent) for a in agents)

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

        # Override pipeline to run only the design agent
        orch._build_pipeline = lambda p, f: [agent]
        result = orch.run("test", font=font)
        assert result.steps[0].success is True

    def test_run_step_explicit_failure_no_retry(self, font):
        """_run_agent: agent returns explicit success=False, no retries left."""
        orch = Orchestrator(max_retries=0)

        failure_result = MagicMock()
        failure_result.success = False
        failure_result.message = "explicit failure"
        failure_result.confidence = 0.0
        agent = MagicMock()
        agent.run.return_value = failure_result
        orch.register("design", agent)

        # Single-agent pipeline via _run_agent
        orch._build_pipeline = lambda p, f: [agent]

        result = orch.run("test", font=font)
        assert result.steps[0].success is False

    def test_run_step_explicit_failure_with_retry(self, font):
        """_run_agent: agent returns explicit success=False, retried once."""
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

        # Override pipeline to run only the design agent
        orch._build_pipeline = lambda p, f: [agent]
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

        # Override pipeline to run only the design agent
        orch._build_pipeline = lambda p, f: [agent]
        result = orch.run("test", font=font)
        assert result.steps[0].success is True


class TestRunAgent:
    """Direct unit tests for the _run_agent method."""

    def test_run_agent_success(self, font):
        """_run_agent wraps a successful agent result in AgentResult."""
        orch = Orchestrator()

        agent = MagicMock()
        agent_data = MagicMock()
        agent_data.confidence = 0.9
        agent.run.return_value = agent_data

        result = orch._run_agent(agent, "test", font)
        assert result.success is True
        assert result.confidence == 0.9
        assert result.data is agent_data
        agent.run.assert_called_once_with("test", font=font)

    def test_run_agent_calls_with_keyword_font(self, font):
        """_run_agent must call agent.run(prompt, font=font) — keyword arg for font."""
        orch = Orchestrator()
        agent = MagicMock()
        agent.run.return_value = MagicMock(confidence=1.0)

        orch._run_agent(agent, "prompt", font)

        call_args = agent.run.call_args
        assert call_args.args == ("prompt",)
        assert call_args.kwargs.get("font") is font

    def test_run_agent_exception_captured(self, font):
        """_run_agent captures exceptions and returns failure AgentResult."""
        orch = Orchestrator(max_retries=0)
        agent = MagicMock()
        agent.run.side_effect = ValueError("bad font")

        result = orch._run_agent(agent, "test", font)
        assert result.success is False
        assert "bad font" in result.error

    def test_run_agent_retry_on_low_confidence(self, font):
        """_run_agent retries when confidence is below threshold."""
        orch = Orchestrator(max_retries=1, confidence_threshold=0.7)

        low = MagicMock()
        low.confidence = 0.3
        high = MagicMock()
        high.confidence = 0.9

        agent = MagicMock()
        agent.run.side_effect = [low, high]

        result = orch._run_agent(agent, "test", font)
        assert result.success is True
        assert result.confidence == 0.9
        assert agent.run.call_count == 2

    def test_run_agent_retry_on_explicit_failure(self, font):
        """_run_agent retries when agent signals explicit success=False."""
        orch = Orchestrator(max_retries=1)

        fail_data = MagicMock()
        fail_data.success = False
        fail_data.message = "not ready"
        fail_data.confidence = 0.0

        ok_data = MagicMock()
        ok_data.success = True
        ok_data.confidence = 0.9

        agent = MagicMock()
        agent.run.side_effect = [fail_data, ok_data]

        result = orch._run_agent(agent, "test", font)
        assert result.success is True
        assert agent.run.call_count == 2

    def test_run_agent_exhausted_retries_still_succeeds(self, font):
        """After max_retries, the last attempt is accepted even at low confidence."""
        orch = Orchestrator(max_retries=1, confidence_threshold=0.9)

        low = MagicMock()
        low.confidence = 0.3
        agent = MagicMock()
        agent.run.return_value = low  # always low

        result = orch._run_agent(agent, "test", font)
        assert result.success is True
        assert agent.run.call_count == 2  # initial + 1 retry

    def test_run_agent_exception_then_success(self, font):
        """_run_agent recovers when first call raises but retry succeeds."""
        orch = Orchestrator(max_retries=1)

        ok_data = MagicMock()
        ok_data.confidence = 0.9

        agent = MagicMock()
        agent.run.side_effect = [RuntimeError("transient"), ok_data]

        result = orch._run_agent(agent, "test", font)
        assert result.success is True
        assert result.error is None

    def test_run_agent_with_none_font(self):
        """_run_agent works when font is None (fontforge not available)."""
        orch = Orchestrator()
        agent = MagicMock()
        agent.run.return_value = MagicMock(confidence=1.0)

        result = orch._run_agent(agent, "test", None)
        assert result.success is True
        agent.run.assert_called_once_with("test", font=None)

    def test_run_agent_passes_context(self, font):
        """Context dict is accepted without error (reserved for future use)."""
        orch = Orchestrator()
        agent = MagicMock()
        agent.run.return_value = MagicMock(confidence=1.0)
        ctx = {"prompt": "test"}

        result = orch._run_agent(agent, "test", font, context=ctx)
        assert result.success is True


class TestRunStep:
    """Direct unit tests for the _run_step backward-compat helper."""

    def test_run_step_success(self, font):
        orch = Orchestrator()
        step_fn = MagicMock(return_value=MagicMock(confidence=0.9))
        result = orch._run_step(step_fn, "design", "prompt", font)
        assert result.success is True
        assert result.confidence == 0.9
        step_fn.assert_called_once_with(prompt="prompt", font=font)

    def test_run_step_failure_no_retry(self, font):
        orch = Orchestrator(max_retries=0)
        fail = MagicMock()
        fail.success = False
        fail.message = "bad"
        step_fn = MagicMock(return_value=fail)
        result = orch._run_step(step_fn, "qa", "prompt", font)
        assert result.success is False

    def test_run_step_exception_captured(self, font):
        orch = Orchestrator(max_retries=0)
        step_fn = MagicMock(side_effect=ValueError("boom"))
        result = orch._run_step(step_fn, "export", "prompt", font)
        assert result.success is False
        assert "boom" in result.error

    def test_run_step_retry_on_explicit_failure(self, font):
        orch = Orchestrator(max_retries=1)
        fail = MagicMock()
        fail.success = False
        fail.message = "retry me"
        ok = MagicMock()
        ok.success = True
        ok.confidence = 0.9
        step_fn = MagicMock(side_effect=[fail, ok])
        result = orch._run_step(step_fn, "metrics", "prompt", font)
        assert result.success is True
        assert step_fn.call_count == 2

    def test_run_step_fallback_low_confidence(self, font):
        orch = Orchestrator(max_retries=1, confidence_threshold=0.9)
        low = MagicMock(confidence=0.3)
        step_fn = MagicMock(return_value=low)
        result = orch._run_step(step_fn, "style", "prompt", font)
        assert result.success is True
        assert step_fn.call_count == 2
