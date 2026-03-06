"""Multi-agent orchestrator for AIFont."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from aifont.core.font import Font


@dataclass
class AgentResult:
    """Result returned by a single agent step."""

    agent_name: str
    success: bool
    confidence: float  # 0.0 – 1.0
    data: Any = None
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Aggregated result from a full orchestrator run."""

    prompt: str
    steps: List[AgentResult] = field(default_factory=list)
    font: Optional["Font"] = None

    @property
    def success(self) -> bool:
        return all(s.success for s in self.steps)

    @property
    def errors(self) -> List[str]:
        return [s.error for s in self.steps if s.error]


class Orchestrator:
    """Central controller that dispatches tasks to specialised agents.

    Usage::

        orch = Orchestrator()
        result = orch.run("Create a bold geometric A", font=my_font)
    """

    # Minimum confidence threshold to proceed without re-running an agent
    CONFIDENCE_THRESHOLD = 0.6

    def __init__(self, max_retries: int = 2) -> None:
        self.max_retries = max_retries
        self._agents: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register(self, name: str, agent: Any) -> None:
        """Register a named agent."""
        self._agents[name] = agent

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        prompt: str,
        font: Optional["Font"] = None,
    ) -> PipelineResult:
        """Run the full agent pipeline for *prompt*.

        Returns a :class:`PipelineResult` with the modified font.
        """
        result = PipelineResult(prompt=prompt, font=font)
        pipeline = self._build_pipeline(prompt, font)
        for step_fn, agent_name in pipeline:
            step_result = self._run_step(step_fn, agent_name, prompt, font)
            result.steps.append(step_result)
            if not step_result.success:
                break
            if step_result.data is not None and hasattr(step_result.data, "glyphs"):
                result.font = step_result.data
                font = result.font
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_pipeline(
        self, prompt: str, font: Optional["Font"]
    ) -> List[tuple]:
        """Return the ordered list of ``(callable, name)`` steps."""
        from aifont.agents.design_agent import DesignAgent
        from aifont.agents.metrics_agent import MetricsAgent
        from aifont.agents.qa_agent import QAAgent
        from aifont.agents.export_agent import ExportAgent

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
        font: Optional["Font"],
    ) -> AgentResult:
        for attempt in range(self.max_retries + 1):
            try:
                data = step_fn(prompt=prompt, font=font)
                confidence = getattr(data, "confidence", 1.0)
                if confidence >= self.CONFIDENCE_THRESHOLD or attempt == self.max_retries:
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
