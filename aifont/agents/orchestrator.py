"""Multi-agent orchestrator for AIFont."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional
"""Multi-agent orchestrator — coordinates specialized AIFont agents."""
"""Multi-agent orchestrator for AIFont pipelines."""

from __future__ import annotations

import logging
from typing import Optional

from aifont.core.font import Font
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font


logger = logging.getLogger(__name__)


class Orchestrator:
    """Central coordinator that dispatches tasks to specialized agents.

    Example:
        >>> from aifont.agents import Orchestrator
        >>> orch = Orchestrator()
        >>> font = orch.run("Create a bold geometric sans-serif")
    """

    def __init__(self) -> None:
        self._agents: dict = {}

    def run(self, prompt: str, font: Optional[Font] = None) -> Font:
        """Process a natural language prompt and return the resulting font.

        The pipeline is:
        1. **DesignAgent** — generate glyph outlines from the prompt.
        2. **StyleAgent**  — apply consistent visual style.
        3. **MetricsAgent**— optimise spacing and kerning.
        4. **QAAgent**     — validate and auto-fix issues.
        5. **ExportAgent** — prepare for export.

        Args:
            prompt: Natural language description of the desired font.
            font:   Optional base font to modify instead of creating new.

        Returns:
            The resulting :class:`~aifont.core.font.Font`.
        """
        if font is None:
            font = Font.new("AIFont")

        logger.info("Orchestrator starting pipeline for prompt: %r", prompt)

        from aifont.agents.design_agent import DesignAgent
        from aifont.agents.style_agent import StyleAgent
        from aifont.agents.metrics_agent import MetricsAgent
        from aifont.agents.qa_agent import QAAgent

        pipeline = [
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
    confidence: float = 1.0
    message: str = ""
    data: dict = field(default_factory=dict)


class Orchestrator:
    """Central controller that coordinates the AIFont agent pipeline.

    Dispatches a natural-language *prompt* through a sequential pipeline:

        DesignAgent → StyleAgent → MetricsAgent → QAAgent → ExportAgent

    Each agent returns an :class:`AgentResult`; if *confidence* falls
    below the threshold the agent is retried up to *max_retries* times.

    Example::

        orch = Orchestrator()
        font = orch.run("Create a modern geometric sans-serif")
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        max_retries: int = 2,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.max_retries = max_retries

    # ------------------------------------------------------------------
    # Public API
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
        font: Font | None = None,
    ) -> Font:
        """Execute the full agent pipeline for *prompt*.

        Args:
            prompt: Natural-language design intent.
            font:   Optional seed font to modify. A blank font is created
                    when not provided.

        Returns:
            The modified (or newly created) :class:`~aifont.core.font.Font`.
        """
        from aifont.agents.design_agent import DesignAgent  # noqa: PLC0415
        from aifont.agents.export_agent import ExportAgent  # noqa: PLC0415
        from aifont.agents.metrics_agent import MetricsAgent  # noqa: PLC0415
        from aifont.agents.qa_agent import QAAgent  # noqa: PLC0415
        from aifont.agents.style_agent import StyleAgent  # noqa: PLC0415
        from aifont.core.font import Font  # noqa: PLC0415

        if font is None:
            font = Font.new()

        pipeline: list = [
            DesignAgent(),
            StyleAgent(),
            MetricsAgent(),
            QAAgent(),
        ]

        for agent in pipeline:
            logger.info("Running agent: %s", agent.__class__.__name__)
            font = agent.run(prompt, font)

        return font
            ExportAgent(),
        ]

        for agent in pipeline:
            result = self._run_agent(agent, prompt, font)
            if not result.success:
                logger.warning("Agent %s failed: %s", result.agent_name, result.message)
                raise RuntimeError(
                    f"Pipeline failed at agent '{result.agent_name}': {result.message}"
                )
            logger.info(
                "Agent %s completed (confidence=%.2f)",
                result.agent_name,
                result.confidence,
            )

        return font

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
    def _run_agent(self, agent, prompt: str, font: Font) -> AgentResult:
        name = type(agent).__name__
        for attempt in range(self.max_retries + 1):
            try:
                result: AgentResult = agent.run(prompt, font)
            except Exception as exc:  # noqa: BLE001
                result = AgentResult(
                    agent_name=name,
                    success=False,
                    message=str(exc),
                )
            if result.success and result.confidence >= self.confidence_threshold:
                return result
            if attempt < self.max_retries:
                logger.debug(
                    "Retrying agent %s (attempt %d/%d)",
                    name,
                    attempt + 1,
                    self.max_retries,
                )
        return result
