"""Multi-agent orchestrator for AIFont pipelines."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aifont.core.font import Font

# Attributes extracted from agent results and stored in the shared context.
# Keys are formatted as "<AgentClassName>.<attr>", e.g. "DesignAgent.glyph_name".
_CONTEXT_ATTRS = (
    "confidence",
    "agent_name",
    "glyph_name",
    "svg_data",
    "report",
    "score",
    "formats",
)

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
    context: dict[str, Any] = field(default_factory=dict)

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

    Each agent is executed via :meth:`_run_agent`, which handles retry logic
    and confidence thresholding.  Results are accumulated in a
    :class:`PipelineResult` along with a shared *context* dict that agents
    can propagate data through.

    Example::

        orch = Orchestrator()

        # High-level: create a font from scratch
        result = orch.create_font("A modern geometric sans-serif")

        # Lower-level: run the pipeline on an existing font
        result = orch.run("Make it bolder", font=my_font)
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
        """Register a named agent, overriding the default for *name*.

        Args:
            name:  Slot name – one of ``"design"``, ``"style"``,
                   ``"metrics"``, ``"qa"``, ``"export"``.
            agent: Agent instance with a ``run(prompt, font=font)`` method.
        """
        self._agents[name] = agent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_font(self, prompt: str) -> PipelineResult:
        """Create a brand-new font from a natural-language *prompt*.

        This is the primary high-level entry point for the AIFont pipeline.
        It creates a fresh :class:`~aifont.core.font.Font` and runs the
        complete agent sequence (Design → Style → Metrics → QA → Export).

        Args:
            prompt: A free-text description such as
                    ``"A modern geometric sans-serif with rounded corners"``.

        Returns:
            A :class:`PipelineResult` with step results, the final font, and
            a shared context dict accumulated across all agents.

        Example::

            orch = Orchestrator()
            result = orch.create_font("Bold condensed display typeface")
            if result.success:
                print("Font created:", result.font)
        """
        return self.run(prompt, font=None)

    def run(
        self,
        prompt: str,
        font: Font | None = None,
    ) -> PipelineResult:
        """Run the full agent pipeline for *prompt*.

        Creates a new :class:`~aifont.core.font.Font` when *font* is ``None``.
        Each agent is executed via :meth:`_run_agent`; failures are captured
        in :attr:`PipelineResult.steps` rather than raised, so callers can
        inspect individual step results.

        Args:
            prompt: Natural-language instruction for this pipeline run.
            font:   An existing font to transform.  When ``None`` a new font
                    is created from *prompt* before the pipeline starts.

        Returns:
            A :class:`PipelineResult` containing per-step :class:`AgentResult`
            objects, the (possibly updated) font, and a shared context dict.
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

        # Shared memory context — accumulated across all pipeline steps.
        context: dict[str, Any] = {"prompt": prompt}

        result = PipelineResult(prompt=prompt, font=font, context=context)

        for agent in self._build_pipeline(prompt, font):
            step_result = self._run_agent(agent, prompt, font, context=context)
            result.steps.append(step_result)

            # If an agent returned an updated font, propagate it forward.
            if step_result.data is not None:
                agent_data = step_result.data
                updated_font = getattr(agent_data, "font", None)
                if updated_font is not None and hasattr(updated_font, "glyphs"):
                    font = updated_font
                    result.font = font

            # Merge any context data the agent produced into shared memory.
            if step_result.data is not None:
                agent_data = step_result.data
                for attr in _CONTEXT_ATTRS:
                    val = getattr(agent_data, attr, None)
                    if val is not None:
                        context[f"{step_result.agent_name}.{attr}"] = val

            logger.info(
                "Pipeline step %-10s  success=%-5s  confidence=%.2f",
                step_result.agent_name,
                step_result.success,
                step_result.confidence,
            )

        return result

    # ------------------------------------------------------------------
    # Core single-agent runner
    # ------------------------------------------------------------------

    def _run_agent(
        self,
        agent: Any,
        prompt: str,
        font: Font | None,
        *,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Run a single *agent* with retry and confidence-threshold logic.

        This is the canonical method for executing one agent in the pipeline.
        It calls ``agent.run(prompt, font=font)`` and wraps the returned
        domain-specific result (e.g. :class:`~aifont.agents.design_agent.DesignResult`,
        :class:`~aifont.agents.qa_agent.QAReport`, …) in a uniform
        :class:`AgentResult`.

        If the agent's result carries a ``confidence`` below
        :attr:`confidence_threshold`, the call is retried up to
        :attr:`max_retries` times.  If the agent itself raises an exception,
        that is also retried; on the last attempt the error is captured in
        the returned :class:`AgentResult` rather than re-raised.

        Args:
            agent:   Any agent with a ``run(prompt, font=font)`` method.
            prompt:  Natural-language prompt for this step.
            font:    Current font being built (may be ``None``).
            context: Shared memory dict accumulated across pipeline steps
                     (read-only from the agent's perspective; the orchestrator
                     merges agent outputs back in after each step).

        Returns:
            An :class:`AgentResult` capturing success, confidence, the raw
            agent data, and any error message.
        """
        name = type(agent).__name__
        # `context` is reserved for future LLM-memory injection; unused for now.

        for attempt in range(self.max_retries + 1):
            try:
                data = agent.run(prompt, font=font)

                # Propagate explicit failure signalled by the agent.
                if hasattr(data, "success") and not data.success:
                    if attempt < self.max_retries:
                        logger.debug(
                            "Agent %s reported failure (attempt %d/%d); retrying.",
                            name,
                            attempt + 1,
                            self.max_retries,
                        )
                        continue
                    msg = getattr(data, "message", "") or getattr(data, "error", "") or ""
                    return AgentResult(
                        agent_name=name,
                        success=False,
                        confidence=0.0,
                        data=data,
                        message=msg,
                    )

                confidence = float(getattr(data, "confidence", 1.0))
                if confidence >= self.confidence_threshold or attempt == self.max_retries:
                    return AgentResult(
                        agent_name=name,
                        success=True,
                        confidence=confidence,
                        data=data,
                    )

                logger.debug(
                    "Agent %s confidence %.2f below threshold %.2f (attempt %d/%d); retrying.",
                    name,
                    confidence,
                    self.confidence_threshold,
                    attempt + 1,
                    self.max_retries,
                )

            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "Agent %s raised %r (attempt %d/%d).",
                    name,
                    exc,
                    attempt + 1,
                    self.max_retries,
                )
                if attempt == self.max_retries:
                    return AgentResult(
                        agent_name=name,
                        success=False,
                        confidence=0.0,
                        error=str(exc),
                    )

        return AgentResult(agent_name=name, success=False, confidence=0.0)  # pragma: no cover

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_pipeline(self, prompt: str, font: Font | None) -> list[Any]:
        """Return the ordered list of agent objects for this pipeline run.

        The five-agent sequence defined in Issue #15:
        DesignAgent → StyleAgent → MetricsAgent → QAAgent → ExportAgent.

        Any agent may be overridden via :meth:`register` before calling
        :meth:`run` or :meth:`create_font`.
        """
        from aifont.agents.design_agent import DesignAgent
        from aifont.agents.export_agent import ExportAgent
        from aifont.agents.metrics_agent import MetricsAgent
        from aifont.agents.qa_agent import QAAgent
        from aifont.agents.style_agent import StyleAgent

        return [
            self._agents.get("design", DesignAgent()),
            self._agents.get("style", StyleAgent()),
            self._agents.get("metrics", MetricsAgent()),
            self._agents.get("qa", QAAgent()),
            self._agents.get("export", ExportAgent()),
        ]

    def _run_step(
        self,
        step_fn: Any,
        agent_name: str,
        prompt: str,
        font: Font | None,
    ) -> AgentResult:
        """Low-level runner that calls a bare *step_fn* with keyword args.

        This helper exists for backward compatibility with tests that
        monkey-patch :meth:`_build_pipeline` to return ``(fn, name)`` tuples.
        New code should prefer :meth:`_run_agent`.
        """
        for attempt in range(self.max_retries + 1):
            try:
                data = step_fn(prompt=prompt, font=font)
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
