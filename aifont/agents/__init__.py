"""
aifont.agents — AI agent layer built on top of the aifont.core SDK.

Agents orchestrate high-level tasks (QA validation, design generation,
metrics optimisation, etc.) by calling aifont.core APIs.  They never call
``fontforge`` directly.
"""

from aifont.agents.qa_agent import QAAgent, QAReport

__all__ = ["QAAgent", "QAReport"]
