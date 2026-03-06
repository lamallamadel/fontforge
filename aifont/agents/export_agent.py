"""aifont.agents.export_agent — intelligent font export agent.

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
        font=ff_font,
        output_dir="/tmp/my-export",
        target=ExportTarget.WEB,
        family_name="MyFont",
    )

    print(result.css_snippet)
"""

from __future__ import annotations

import os
import textwrap
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

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
    issues: list[str] = field(default_factory=list)


@dataclass
class ExportResult:
    """Aggregated result returned by :meth:`ExportAgent.run`."""

    exported_files: dict[str, Path] = field(default_factory=dict)
    """Mapping from format name (``"otf"``, ``"ttf"``, etc.) to file path."""

    specimen_path: Path | None = None
    """Path to the generated HTML specimen file (if produced)."""

    css_snippet: str = ""
    """Ready-to-use CSS ``@font-face`` block referencing the exported files."""

    validation_report: list[FormatValidation] = field(default_factory=list)
    """Per-format validation outcomes."""

    @property
    def all_passed(self) -> bool:
        """Return ``True`` if every format passed validation."""
        return all(v.passed for v in self.validation_report)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

# Target → list of formats to produce
_TARGET_FORMATS_MAP: dict[str, list[str]] = {
    ExportTarget.WEB: ["woff2", "ttf"],
    ExportTarget.PRINT: ["otf"],
    ExportTarget.APP: ["ttf", "otf"],
    ExportTarget.VARIABLE: ["variable"],
    ExportTarget.FULL: ["otf", "ttf", "woff2"],
}


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
    output_dir:
        Default output directory (can be overridden in :meth:`run`).
    target:
        Default export target (can be overridden in :meth:`run`).
    """

    def __init__(
        self,
        output_dir: str | os.PathLike | None = None,
        target: ExportTarget | str = ExportTarget.WEB,
        *,
        generate_specimen: bool = True,
        generate_css: bool = True,
        validate: bool = True,
    ) -> None:
        self.output_dir = Path(output_dir) if output_dir else None
        self.target = target
        self.generate_specimen = generate_specimen
        self.generate_css = generate_css
        self.validate = validate

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        font: object,
        output_dir: str | os.PathLike | None = None,
        *,
        target: ExportTarget | str = ExportTarget.WEB,
        family_name: str = "MyFont",
        languages: Iterable[str] | None = None,
        extra_formats: Sequence[str] | None = None,
    ) -> ExportResult:
        """Run the export pipeline and return an :class:`ExportResult`.

        Parameters
        ----------
        font:
            A font object (fontforge.font or aifont.core.font.Font).
        output_dir:
            Directory where all output files will be written.
        target:
            Target use case — drives format selection and optimisations.
        family_name:
            Font family name used in specimen / CSS output.
        languages:
            IETF BCP-47 language tags for subsetting.
        extra_formats:
            Additional formats to export on top of the target defaults.
        """
        out_dir = output_dir or self.output_dir
        if out_dir is None:
            raise ValueError("output_dir must be provided")

        target = ExportTarget(target) if isinstance(target, str) else target
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)

        lang_list = list(languages) if languages else []
        formats = self._choose_formats(target, extra_formats)

        result = ExportResult()

        for fmt in formats:
            path = self._export_format(font, fmt, out, family_name, lang_list)
            if path is not None:
                result.exported_files[fmt] = path

        if self.generate_specimen and result.exported_files:
            result.specimen_path = self._write_specimen(out, family_name, result.exported_files)

        if self.generate_css and result.exported_files:
            result.css_snippet = self._build_css(family_name, result.exported_files)

        if self.validate:
            for fmt, path in result.exported_files.items():
                result.validation_report.append(self._validate_file(fmt, path))

        return result

    # ------------------------------------------------------------------
    # Format selection
    # ------------------------------------------------------------------

    def _choose_formats(
        self,
        target: ExportTarget,
        extra_formats: Sequence[str] | None,
    ) -> list[str]:
        base = list(_TARGET_FORMATS_MAP.get(target, ["otf"]))
        if extra_formats:
            for fmt in extra_formats:
                if fmt not in base:
                    base.append(fmt)
        return base

    # ------------------------------------------------------------------
    # Format export
    # ------------------------------------------------------------------

    def _export_format(
        self,
        font: object,
        fmt: str,
        out: Path,
        family_name: str,
        lang_list: list[str],
    ) -> Path | None:
        stem = family_name.replace(" ", "")
        path = out / f"{stem}.{fmt}"
        try:
            if fmt == "woff2":
                if lang_list:
                    subset_font(font, path, lang_list)
                else:
                    export_woff2(font, path)
            elif fmt == "ttf":
                export_ttf(font, path)
            elif fmt == "variable":
                export_variable(font, path)
            else:
                export_otf(font, path)
            return path
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Specimen generation
    # ------------------------------------------------------------------

    def _write_specimen(
        self,
        out: Path,
        family_name: str,
        exported_files: dict[str, Path],
    ) -> Path:
        """Write an HTML specimen page and return its path."""
        specimen_path = out / "specimen.html"
        css = self._build_css(family_name, exported_files, relative=True)

        pangrams = [
            "The quick brown fox jumps over the lazy dog.",
            "Sphinx of black quartz, judge my vow.",
        ]
        sizes = [12, 16, 24, 36, 48, 72]

        size_rows = ""
        for sz in sizes:
            size_rows += (
                f"    <tr>\n"
                f'      <td style="color:#888;font-size:11px;padding-right:12px;'
                f'white-space:nowrap">{sz}px</td>\n'
                f"      <td style=\"font-family:'{family_name}',sans-serif;"
                f'font-size:{sz}px;padding:4px 0">'
                f"{pangrams[0]}</td>\n"
                f"    </tr>\n"
            )

        style_rows = ""
        for weight, style_label in [(400, "Regular"), (700, "Bold")]:
            style_rows += (
                f"  <p style=\"font-family:'{family_name}',sans-serif;"
                f'font-size:28px;font-weight:{weight};margin:8px 0">'
                f"{style_label}: {pangrams[1]}</p>\n"
            )

        html = textwrap.dedent(f"""\
            <!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="UTF-8">
              <title>{family_name} — Font Specimen</title>
              <style>
            {textwrap.indent(css, "    ")}
                body {{ font-family: sans-serif; margin: 40px; }}
                h1   {{ font-family: '{family_name}', sans-serif; font-size: 64px; }}
                table {{ border-collapse: collapse; width: 100%; }}
              </style>
            </head>
            <body>
              <h1>{family_name}</h1>
              <table>
            {size_rows}  </table>
            {style_rows}
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
        exported_files: dict[str, Path],
        *,
        relative: bool = False,
    ) -> str:
        """Return a CSS ``@font-face`` block for the exported files."""
        format_order = ["woff2", "woff", "ttf", "otf", "variable"]
        format_labels = {
            "woff2": "woff2",
            "woff": "woff",
            "ttf": "truetype",
            "otf": "opentype",
            "variable": "truetype",
        }

        src_parts: list[str] = []
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
        issues: list[str] = []

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

        min_sizes = {"otf": 100, "ttf": 100, "woff2": 20, "variable": 100}
        min_sz = min_sizes.get(fmt, 50)
        if size < min_sz:
            issues.append(
                f"File size ({size} bytes) is suspiciously small "
                f"(expected ≥ {min_sz} bytes for {fmt})"
            )

        magic: dict[str, bytes] = {"woff2": b"wOF2", "otf": b"OTTO"}
        if fmt in magic:
            with open(path, "rb") as fh:
                header = fh.read(4)
            if header != magic[fmt]:
                issues.append(
                    f"Unexpected file magic bytes: {header!r} (expected {magic[fmt]!r} for {fmt})"
                )

        if fmt in ("ttf", "variable"):
            with open(path, "rb") as fh:
                header = fh.read(4)
            valid_ttf_magic = {b"\x00\x01\x00\x00", b"true", b"OTTO"}
            if header not in valid_ttf_magic:
                issues.append(f"Unexpected TTF magic bytes: {header!r}")

        return FormatValidation(
            format=fmt,
            path=path,
            file_size_bytes=size,
            passed=len(issues) == 0,
            issues=issues,
        )
