"""Multi-agent orchestrator — coordinates specialized AIFont agents."""

from __future__ import annotations

import logging
from typing import Optional

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
            DesignAgent(),
            StyleAgent(),
            MetricsAgent(),
            QAAgent(),
        ]

        for agent in pipeline:
            logger.info("Running agent: %s", agent.__class__.__name__)
            font = agent.run(prompt, font)

        return font
