"""Export Agent — intelligent font export with format-specific optimisation."""

from __future__ import annotations

import logging
from pathlib import Path

from aifont.core.font import Font
from aifont.core import export as core_export

logger = logging.getLogger(__name__)

_USE_CASES = {
    "web": ["woff2"],
    "print": ["otf"],
    "app": ["ttf", "otf"],
    "variable": ["ttf"],
}


class ExportAgent:
    """Exports a font in the optimal format(s) for a given use case.

    Example:
        >>> agent = ExportAgent(output_dir="dist/")
        >>> agent.run("web font", font)
        # Produces dist/MyFont.woff2
    """

    def __init__(self, output_dir: str | Path = ".") -> None:
        self.output_dir = Path(output_dir)

    def run(self, prompt: str, font: Font) -> Font:
        """Export the font based on the prompt's use-case hint.

        Args:
            prompt: Use-case hint (e.g. ``"web font"``, ``"print"``).
            font:   Font to export.

        Returns:
            The font (unchanged).
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stem = font.metadata.family_name.replace(" ", "") or "AIFont"

        formats: list[str] = ["otf"]  # default
        for use_case, fmts in _USE_CASES.items():
            if use_case in prompt.lower():
                formats = fmts
                break

        for fmt in formats:
            out_path = self.output_dir / f"{stem}.{fmt}"
            logger.info("ExportAgent: exporting %s as %s → %s", stem, fmt, out_path)
            try:
                if fmt == "woff2":
                    core_export.export_woff2(font, out_path)
                elif fmt == "ttf":
                    core_export.export_ttf(font, out_path)
                else:
                    core_export.export_otf(font, out_path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("ExportAgent: failed to export %s: %s", fmt, exc)

        return font
