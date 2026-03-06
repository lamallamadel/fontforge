"""Design agent — generates glyph outlines from natural-language prompts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aifont.core.font import Font


@dataclass
class DesignResult:
    """Result from the DesignAgent."""

    font: Font | None
    glyph_name: str
    svg_data: str | None = None
    confidence: float = 1.0


class DesignAgent:
    """Generates glyphs from natural language prompts.

    The agent interprets a text prompt, produces an SVG description of
    the requested glyph(s), then injects them into the font via
    :mod:`aifont.core.svg_parser`.

    LLM integration is optional; when no LLM client is configured the
    agent performs a best-effort structural generation.
    """

    def __init__(self, llm_client: Any = None) -> None:
        self._llm = llm_client

    def run(
        self,
        prompt: str,
        font: Font | None = None,
        unicode_point: int = 0x0041,
    ) -> DesignResult:
        """Process *prompt* and inject the resulting glyph into *font*.

        Returns a :class:`DesignResult`.
        """
        glyph_name = self._extract_glyph_name(prompt)
        svg_data = self._generate_svg(prompt)
        if font is not None and svg_data:
            self._inject_svg(font, svg_data, unicode_point, glyph_name)
        return DesignResult(
            font=font,
            glyph_name=glyph_name,
            svg_data=svg_data,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _extract_glyph_name(self, prompt: str) -> str:
        """Heuristically extract a glyph name from *prompt*."""
        for token in prompt.split():
            if len(token) == 1 and token.isupper():
                return token
        for token in prompt.split():
            if len(token) == 1 and token.isalpha():
                return token.upper()
        return "A"

    def _generate_svg(self, prompt: str) -> str | None:
        """Generate an SVG path string for the requested glyph.

        When an LLM client is configured it is used; otherwise a
        placeholder rectangle is returned.
        """
        if self._llm is not None:
            try:
                return self._llm.generate_svg(prompt)
            except Exception:  # noqa: BLE001
                pass
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 700">'
            '<path d="M 50 0 L 450 0 L 450 700 L 50 700 Z"/>'
            "</svg>"
        )

    def _inject_svg(
        self,
        font: Font,
        svg_data: str,
        unicode_point: int,
        glyph_name: str,
    ) -> None:
        """Write *svg_data* to a temp file and import it via svg_to_glyph."""
        import os
        import tempfile

        from aifont.core.svg_parser import svg_to_glyph

        with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as tmp:
            tmp.write(svg_data)
            tmp_path = tmp.name
        try:
            svg_to_glyph(tmp_path, font, unicode_point, glyph_name)
        finally:
            os.unlink(tmp_path)
