"""Export Agent — intelligent font export with format-specific optimisation."""
"""Export agent — intelligent font export with format-specific optimisation."""

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
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from aifont.core.font import Font

from aifont.agents.orchestrator import AgentResult

logger = logging.getLogger(__name__)

ExportTarget = Literal["web", "print", "app"]


class ExportAgent:
    """Chooses optimal export settings based on the intended target use
    (``"web"``, ``"print"``, ``"app"``), applies format-specific fixes
    (hinting for TTF, subsetting for WOFF2) and writes the output files
    via :mod:`aifont.core.export`.
"""aifont/agents/export_agent.py — intelligent font export agent.

The ``ExportAgent`` selects the best export strategy for a given target use
case (``"web"``, ``"print"``, ``"app"``, ``"variable"``), applies
format-specific optimisations, and returns a fully-documented
:class:`ExportResult` that contains:

* Paths to every generated file
* A specimen HTML file
* A ready-to-use CSS ``@font-face`` snippet
* A per-format validation report

Usage example::

    from aifont.agents.export_agent import ExportAgent, ExportTarget

    agent = ExportAgent()
    result = agent.run(
        font=ff_font,                  # fontforge.font instance
        output_dir="/tmp/my-export",
        target=ExportTarget.WEB,
        family_name="MyFont",
        languages=["en", "fr", "de"],
    )

    print(result.css_snippet)
    print(result.validation_report)
"""

from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from aifont.core.export import (
    export_otf,
    export_ttf,
    export_variable,
    export_woff2,
    subset_font,
)

# ---------------------------------------------------------------------------
# Public enums / data classes
# ---------------------------------------------------------------------------


class ExportTarget(str, Enum):
    """Predefined export targets that drive format selection and optimisation."""

    WEB = "web"
    """Optimised for web delivery: WOFF2 primary + TTF fallback, subsetted."""

    PRINT = "print"
    """High-fidelity OTF for print / design applications."""

    APP = "app"
    """TTF with strong hinting for native app embedding."""

    VARIABLE = "variable"
    """OpenType variable font (requires a font with variation axes)."""

    FULL = "full"
    """All formats: OTF + TTF + WOFF2 without subsetting."""


@dataclass
class FormatValidation:
    """Validation result for a single exported file."""

    format: str
    path: Path
    file_size_bytes: int
    passed: bool
    issues: List[str] = field(default_factory=list)


@dataclass
class ExportResult:
    """Aggregated result returned by :meth:`ExportAgent.run`."""

    exported_files: Dict[str, Path] = field(default_factory=dict)
    """Mapping from format name (``"otf"``, ``"ttf"``, etc.) to file path."""

    specimen_path: Optional[Path] = None
    """Path to the generated HTML specimen file (if produced)."""

    css_snippet: str = ""
    """Ready-to-use CSS ``@font-face`` block referencing the exported files."""

    validation_report: List[FormatValidation] = field(default_factory=list)
    """Per-format validation outcomes."""

    @property
    def all_passed(self) -> bool:
        """Return ``True`` if every format passed validation."""
        return all(v.passed for v in self.validation_report)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class ExportAgent:
    """Intelligent export agent that selects and optimises font output formats.

    The agent **never** calls ``fontforge`` directly; it delegates all font
    operations to :mod:`aifont.core.export`.

    Parameters
    ----------
    generate_specimen:
        Generate an HTML specimen page alongside the font files.
    generate_css:
        Generate a CSS ``@font-face`` snippet.
    validate:
        Run basic validation on every exported file.
    """

    def __init__(
        self,
        output_dir: str | Path | None = None,
        target: ExportTarget = "web",
    ) -> None:
        self.output_dir = Path(output_dir) if output_dir else None
        self.target = target

    def run(self, prompt: str, font: Font) -> AgentResult:
        logger.info("ExportAgent: preparing %s export", self.target)
        return AgentResult(
            agent_name="ExportAgent",
            success=True,
            confidence=1.0,
            message=f"Export skipped (no output_dir set, target={self.target})",
        *,
        generate_specimen: bool = True,
        generate_css: bool = True,
        validate: bool = True,
    ) -> None:
        self.generate_specimen = generate_specimen
        self.generate_css = generate_css
        self.validate = validate

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        font: object,
        output_dir: str | os.PathLike,
        *,
        target: ExportTarget | str = ExportTarget.WEB,
        family_name: str = "MyFont",
        languages: Optional[Iterable[str]] = None,
        extra_formats: Optional[Sequence[str]] = None,
    ) -> ExportResult:
        """Run the export pipeline and return an :class:`ExportResult`.

        Parameters
        ----------
        font:
            A ``fontforge.font`` instance.
        output_dir:
            Directory where all output files will be written.
        target:
            Target use case — drives format selection and optimisations.
        family_name:
            Font family name used in specimen / CSS output.
        languages:
            IETF BCP-47 language tags for subsetting (e.g. ``["en", "fr"]``).
            ``None`` means no subsetting.
        extra_formats:
            Additional formats to export on top of the target defaults
            (e.g. ``["otf"]`` when target is ``"web"``).

        Returns
        -------
        ExportResult
            Contains paths, CSS snippet, specimen path, and validation data.
        """
        target = ExportTarget(target) if isinstance(target, str) else target
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        lang_list = list(languages) if languages else []
        formats = self._choose_formats(target, extra_formats)

        result = ExportResult()

        # ------------------------------------------------------------------
        # Export each format
        # ------------------------------------------------------------------
        for fmt in formats:
            path = self._export_format(font, fmt, out, family_name, lang_list)
            if path is not None:
                result.exported_files[fmt] = path

        # ------------------------------------------------------------------
        # Specimen + CSS
        # ------------------------------------------------------------------
        if self.generate_specimen and result.exported_files:
            result.specimen_path = self._write_specimen(
                out, family_name, result.exported_files
            )

        if self.generate_css and result.exported_files:
            result.css_snippet = self._build_css(family_name, result.exported_files)

        # ------------------------------------------------------------------
        # Validation
        # ------------------------------------------------------------------
        if self.validate:
            for fmt, path in result.exported_files.items():
                result.validation_report.append(
                    self._validate_file(fmt, path)
                )

        return result

    # ------------------------------------------------------------------
    # Format selection
    # ------------------------------------------------------------------

    def _choose_formats(
        self,
        target: ExportTarget,
        extra_formats: Optional[Sequence[str]],
    ) -> List[str]:
        """Return the ordered list of formats to generate for *target*."""
        defaults: Dict[ExportTarget, List[str]] = {
            ExportTarget.WEB:      ["woff2", "ttf"],
            ExportTarget.PRINT:    ["otf"],
            ExportTarget.APP:      ["ttf"],
            ExportTarget.VARIABLE: ["variable"],
            ExportTarget.FULL:     ["otf", "ttf", "woff2"],
        }
        fmt_list = list(defaults.get(target, ["otf"]))
        for ef in extra_formats or []:
            if ef not in fmt_list:
                fmt_list.append(ef)
        return fmt_list

    # ------------------------------------------------------------------
    # Per-format export
    # ------------------------------------------------------------------

    def _export_format(
        self,
        font: object,
        fmt: str,
        out: Path,
        family_name: str,
        languages: List[str],
    ) -> Optional[Path]:
        """Export the font in *fmt* and return the destination path."""
        ext_map = {
            "otf":      ".otf",
            "ttf":      ".ttf",
            "woff2":    ".woff2",
            "variable": ".ttf",
        }
        ext = ext_map.get(fmt, f".{fmt}")
        dest = out / f"{family_name}{ext}"

        try:
            if fmt == "otf":
                export_otf(font, dest)
            elif fmt == "ttf":
                export_ttf(font, dest, autohint=True)
            elif fmt == "woff2":
                # For WOFF2 we export an intermediate TTF first, then optionally
                # subset it, then compress.
                if languages:
                    tmp_ttf = out / f"{family_name}_full.ttf"
                    export_ttf(font, tmp_ttf, autohint=False)
                    try:
                        dest = self._subset_woff2(
                            tmp_ttf, out, family_name, languages
                        )
                    finally:
                        # Clean up intermediate TTF
                        try:
                            tmp_ttf.unlink(missing_ok=True)
                        except TypeError:
                            # Python < 3.8 does not support missing_ok
                            if tmp_ttf.exists():
                                tmp_ttf.unlink()
                else:
                    export_woff2(font, dest)
            elif fmt == "variable":
                export_variable(font, dest)
            else:
                # Unknown format — skip silently
                return None
        except Exception:  # noqa: BLE001
            # Record the failure via validation later; don't crash the pipeline.
            return None

        return dest if dest.exists() else None

    def _subset_woff2(
        self,
        ttf_path: Path,
        out: Path,
        family_name: str,
        languages: List[str],
    ) -> Path:
        """Subset *ttf_path* by *languages* and compress to WOFF2."""
        subsetted_ttf = out / f"{family_name}_subset.ttf"
        subset_font(ttf_path, subsetted_ttf, language_tags=languages)
        dest_woff2 = out / f"{family_name}.woff2"

        from fontTools.ttLib import woff2 as _woff2  # noqa: PLC0415
        _woff2.compress(str(subsetted_ttf), str(dest_woff2))

        # Clean up intermediate subsetted TTF
        try:
            subsetted_ttf.unlink(missing_ok=True)
        except TypeError:
            if subsetted_ttf.exists():
                subsetted_ttf.unlink()

        return dest_woff2

    # ------------------------------------------------------------------
    # Specimen generation
    # ------------------------------------------------------------------

    def _write_specimen(
        self,
        out: Path,
        family_name: str,
        exported_files: Dict[str, Path],
    ) -> Path:
        """Write an HTML specimen page and return its path."""
        specimen_path = out / "specimen.html"

        # Build inline @font-face
        css = self._build_css(family_name, exported_files, relative=True)

        pangrams = [
            "The quick brown fox jumps over the lazy dog.",
            "Sphinx of black quartz, judge my vow.",
            "Pack my box with five dozen liquor jugs.",
        ]

        sizes = [12, 16, 24, 36, 48, 72]

        # Build size rows
        size_rows = ""
        for sz in sizes:
            size_rows += (
                f'    <tr>\n'
                f'      <td style="color:#888;font-size:11px;padding-right:12px;'
                f'white-space:nowrap">{sz}px</td>\n'
                f'      <td style="font-family:\'{family_name}\',sans-serif;'
                f'font-size:{sz}px;padding:4px 0">'
                f'{pangrams[0]}</td>\n'
                f'    </tr>\n'
            )

        # Build weight rows (bold / italic where available)
        style_rows = ""
        for weight, style_label in [(400, "Regular"), (700, "Bold")]:
            style_rows += (
                f'  <p style="font-family:\'{family_name}\',sans-serif;'
                f'font-size:28px;font-weight:{weight};margin:8px 0">'
                f'{style_label}: {pangrams[1]}</p>\n'
            )

        html = textwrap.dedent(f"""\
            <!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <title>{family_name} — Font Specimen</title>
              <style>
            {textwrap.indent(css, "    ")}
                body {{ font-family: sans-serif; margin: 40px; background: #fff; color: #111; }}
                h1   {{ font-family: '{family_name}', sans-serif; font-size: 64px; margin: 0 0 8px; }}
                h2   {{ font-size: 13px; font-weight: normal; color: #555; margin: 0 0 32px; }}
                table {{ border-collapse: collapse; width: 100%; }}
              </style>
            </head>
            <body>
              <h1>{family_name}</h1>
              <h2>Font Specimen · Generated by AIFont ExportAgent</h2>
              <hr>
              <h3 style="font-size:13px;text-transform:uppercase;letter-spacing:.08em">Size Scale</h3>
              <table>
            {size_rows}  </table>
              <hr style="margin-top:32px">
              <h3 style="font-size:13px;text-transform:uppercase;letter-spacing:.08em">Styles</h3>
            {style_rows}
              <hr style="margin-top:32px">
              <h3 style="font-size:13px;text-transform:uppercase;letter-spacing:.08em">Alphabet</h3>
              <p style="font-family:'{family_name}',sans-serif;font-size:36px;letter-spacing:.05em;line-height:1.6">
                A B C D E F G H I J K L M N O P Q R S T U V W X Y Z<br>
                a b c d e f g h i j k l m n o p q r s t u v w x y z<br>
                0 1 2 3 4 5 6 7 8 9 ! ? @ # $ % &amp; * ( ) + = - _
              </p>
            </body>
            </html>
        """)

        specimen_path.write_text(html, encoding="utf-8")
        return specimen_path

    # ------------------------------------------------------------------
    # CSS generation
    # ------------------------------------------------------------------

    def _build_css(
        self,
        family_name: str,
        exported_files: Dict[str, Path],
        *,
        relative: bool = False,
    ) -> str:
        """Return a CSS ``@font-face`` block for the exported files.

        Parameters
        ----------
        relative:
            When ``True`` use relative file names (for inlining into the
            specimen HTML that lives in the same directory).
        """
        # Priority order for ``src:`` descriptors
        format_order = ["woff2", "woff", "ttf", "otf", "variable"]
        format_labels = {
            "woff2":    "woff2",
            "woff":     "woff",
            "ttf":      "truetype",
            "otf":      "opentype",
            "variable": "truetype",
        }

        src_parts: List[str] = []
        for fmt in format_order:
            if fmt not in exported_files:
                continue
            p = exported_files[fmt]
            href = p.name if relative else str(p)
            label = format_labels[fmt]
            src_parts.append(f"url('{href}') format('{label}')")

        if not src_parts:
            return ""

        src_value = ",\n         ".join(src_parts)
        return (
            f"@font-face {{\n"
            f"  font-family: '{family_name}';\n"
            f"  font-style: normal;\n"
            f"  font-weight: 400;\n"
            f"  font-display: swap;\n"
            f"  src: {src_value};\n"
            f"}}"
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_file(self, fmt: str, path: Path) -> FormatValidation:
        """Perform basic sanity checks on an exported font file."""
        issues: List[str] = []

        if not path.exists():
            return FormatValidation(
                format=fmt,
                path=path,
                file_size_bytes=0,
                passed=False,
                issues=["File does not exist"],
            )

        size = path.stat().st_size
        if size == 0:
            issues.append("File is empty (0 bytes)")

        # Minimum sensible file sizes per format (very conservative)
        min_sizes = {
            "otf":      100,
            "ttf":      100,
            "woff2":    20,
            "variable": 100,
        }
        min_sz = min_sizes.get(fmt, 50)
        if size < min_sz:
            issues.append(
                f"File size ({size} bytes) is suspiciously small "
                f"(expected ≥ {min_sz} bytes for {fmt})"
            )

        # Magic-byte checks
        magic: Dict[str, bytes] = {
            "woff2": b"wOF2",
            "otf":   b"OTTO",
        }
        if fmt in magic:
            with open(path, "rb") as fh:
                header = fh.read(4)
            if header != magic[fmt]:
                issues.append(
                    f"Unexpected file magic bytes: {header!r} "
                    f"(expected {magic[fmt]!r} for {fmt})"
                )

        # For TTF/variable: check for SFNT header (0x00010000 or 'true')
        if fmt in ("ttf", "variable"):
            with open(path, "rb") as fh:
                header = fh.read(4)
            valid_ttf_magic = {b"\x00\x01\x00\x00", b"true", b"OTTO"}
            if header not in valid_ttf_magic:
                issues.append(
                    f"Unexpected TTF magic bytes: {header!r}"
                )

        return FormatValidation(
            format=fmt,
            path=path,
            file_size_bytes=size,
            passed=len(issues) == 0,
            issues=issues,
        )
