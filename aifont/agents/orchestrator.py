"""Multi-agent orchestrator for AIFont pipelines."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aifont.core.font import Font

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result returned by a single agent step."""

    agent_name: str
    success: bool
    confidence: float = 0.0  # 0.0 – 1.0
    data: Any = None
    error: str | None = None
    message: str = ""


@dataclass
class PipelineResult:
    """Aggregated result from a full orchestrator run."""

    prompt: str
    steps: list[AgentResult] = field(default_factory=list)
    font: Font | None = None

    @property
    def success(self) -> bool:
        return all(s.success for s in self.steps)

    @property
    def errors(self) -> list[str]:
        return [s.error for s in self.steps if s.error]


class Orchestrator:
    """Central controller that coordinates the AIFont agent pipeline.

    Dispatches a natural-language *prompt* through a sequential pipeline:

        DesignAgent → StyleAgent → MetricsAgent → QAAgent → ExportAgent

    Each agent returns an :class:`AgentResult`; if *confidence* falls
    below the threshold the agent is retried up to *max_retries* times.

    Example::

        orch = Orchestrator()
        result = orch.run("Create a modern geometric sans-serif")
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        max_retries: int = 2,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.max_retries = max_retries
        self._agents: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register(self, name: str, agent: Any) -> None:
        """Register a named agent."""
        self._agents[name] = agent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        prompt: str,
        font: Font | None = None,
    ) -> PipelineResult:
        """Run the full agent pipeline for *prompt*.

        Creates a new :class:`~aifont.core.font.Font` when *font* is ``None``.
        Agent failures are captured inside :class:`PipelineResult` rather than
        raised, so callers can inspect individual step results.

        Returns:
            A :class:`PipelineResult` containing step results and the final font.
        """
        from aifont.core.font import Font as _Font  # noqa: PLC0415

        if font is None:
            try:
                font = _Font.new(prompt)
            except Exception:  # noqa: BLE001
                # fontforge bindings may be unavailable in test/CI environments.
                # Agents handle a None font gracefully; failures are captured per-step.
                logger.debug("Font.new() failed; continuing without a font object.", exc_info=True)
                font = None

        result = PipelineResult(prompt=prompt, font=font)
        pipeline = self._build_pipeline(prompt, font)
        for step_fn, agent_name in pipeline:
            step_result = self._run_step(step_fn, agent_name, prompt, font)
            result.steps.append(step_result)
            if step_result.data is not None and hasattr(step_result.data, "glyphs"):
                font = step_result.data
                result.font = font
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_pipeline(self, prompt: str, font: Font | None) -> list[tuple]:
        """Return the ordered list of ``(callable, name)`` steps."""
        from aifont.agents.design_agent import DesignAgent
        from aifont.agents.export_agent import ExportAgent
        from aifont.agents.metrics_agent import MetricsAgent
        from aifont.agents.qa_agent import QAAgent

        design = self._agents.get("design", DesignAgent())
        metrics = self._agents.get("metrics", MetricsAgent())
        qa = self._agents.get("qa", QAAgent())
        export_agent = self._agents.get("export", ExportAgent())

        return [
            (design.run, "design"),
            (metrics.run, "metrics"),
            (qa.run, "qa"),
            (export_agent.run, "export"),
        ]

    def _run_step(
        self,
        step_fn: Any,
        agent_name: str,
        prompt: str,
        font: Font | None,
    ) -> AgentResult:
        for attempt in range(self.max_retries + 1):
            try:
                data = step_fn(prompt=prompt, font=font)
                # Propagate explicit failure from agent result
                if hasattr(data, "success") and not data.success:
                    if attempt < self.max_retries:
                        continue
                    msg = getattr(data, "message", "") or getattr(data, "error", "") or ""
                    return AgentResult(
                        agent_name=agent_name,
                        success=False,
                        confidence=0.0,
                        message=msg,
                    )
                confidence = getattr(data, "confidence", 1.0)
                if confidence >= self.confidence_threshold or attempt == self.max_retries:
                    return AgentResult(
                        agent_name=agent_name,
                        success=True,
                        confidence=float(confidence),
                        data=data,
                    )
            except Exception as exc:  # noqa: BLE001
                if attempt == self.max_retries:
                    return AgentResult(
                        agent_name=agent_name,
                        success=False,
                        confidence=0.0,
                        error=str(exc),
                    )
        return AgentResult(agent_name=agent_name, success=False, confidence=0.0)
