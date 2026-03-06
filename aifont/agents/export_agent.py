"""Export agent — intelligent font export with format-specific optimisation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from aifont.core.font import Font

# Supported export targets and the recommended format for each
_TARGET_FORMATS: Dict[str, str] = {
    "web": "woff2",
    "app": "otf",
    "print": "otf",
    "desktop": "ttf",
    "variable": "otf",
}


@dataclass
class ExportResult:
    """Result from the ExportAgent."""

    path: str
    fmt: str
    success: bool
    confidence: float = 1.0
    error: Optional[str] = None


class ExportAgent:
    """Exports a font to the optimal format based on the intended use.

    Uses :mod:`aifont.core.export` for all output operations.
    """

    def __init__(self) -> None:
        pass

    def run(
        self,
        prompt: str,
        font: Optional["Font"] = None,
        output_path: Optional[str] = None,
    ) -> ExportResult:
        """Choose the best export format from *prompt* and write the file."""
        import tempfile

        if font is None:
            return ExportResult(
                path="",
                fmt="",
                success=False,
                confidence=0.0,
                error="No font provided",
            )

        fmt = self._choose_format(prompt)
        if output_path is None:
            import tempfile as _tempfile

            fd, output_path = _tempfile.mkstemp(suffix=f".{fmt}")
            os.close(fd)

        try:
            self._export(font, output_path, fmt)
            return ExportResult(path=output_path, fmt=fmt, success=True)
        except Exception as exc:  # noqa: BLE001
            return ExportResult(
                path=output_path,
                fmt=fmt,
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _choose_format(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        for target, fmt in _TARGET_FORMATS.items():
            if target in prompt_lower:
                return fmt
        return "otf"  # sensible default

    def _export(self, font: "Font", path: str, fmt: str) -> None:
        from aifont.core.export import export_otf, export_ttf, export_woff2

        if fmt == "woff2":
            export_woff2(font, path)
        elif fmt == "ttf":
            export_ttf(font, path)
        else:
            export_otf(font, path)
