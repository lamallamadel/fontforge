"""
aifont.agents — AI agent layer for automated font optimisation.

Agents use aifont.core as their only interface to FontForge.
"""
"""AIFont agents package — multi-agent layer built on top of aifont.core."""

from aifont.agents.export_agent import ExportAgent

__all__ = ["ExportAgent"]
