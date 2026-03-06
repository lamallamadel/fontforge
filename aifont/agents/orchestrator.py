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
