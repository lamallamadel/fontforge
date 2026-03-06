"""
AIFont — a Pythonic SDK built on top of FontForge's Python bindings.

Usage::

    from aifont import AIFont

    font = AIFont.create("MyFont", family="Sans-Serif")
    font.save("output.sfd")
"""

from aifont.core.font import AIFont

__all__ = ["AIFont"]
