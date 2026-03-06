"""AIFont agents — AI-powered font operations built on aifont.core."""

from aifont.agents.orchestrator import Orchestrator

__all__ = ["Orchestrator"]
"""
aifont.agents — AI agent layer built on top of the aifont.core SDK.

Agents orchestrate high-level tasks (QA validation, design generation,
metrics optimisation, etc.) by calling aifont.core APIs.  They never call
``fontforge`` directly.
"""

from aifont.agents.qa_agent import QAAgent, QAReport

__all__ = ["QAAgent", "QAReport"]
aifont.agents — AI agent layer for automated font optimisation.

Agents use aifont.core as their only interface to FontForge.
"""
"""AIFont agents package — multi-agent layer built on top of aifont.core."""

from aifont.agents.export_agent import ExportAgent

__all__ = ["ExportAgent"]
