"""Metrics Agent — auto-optimizes spacing and kerning."""
"""Metrics agent — auto-optimises spacing and kerning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple
import logging

from aifont.core.font import Font
from aifont.core import auto_space
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font


@dataclass
class MetricsResult:
    """Result from the MetricsAgent."""

    font: Optional["Font"]
    kern_pairs_updated: int = 0
    spacing_adjusted: bool = False
    confidence: float = 1.0


class MetricsAgent:
    """Analyses and auto-optimises font spacing and kerning.

    Uses :mod:`aifont.core.metrics` for all font operations.
    An optional LLM client can interpret style intent (e.g.
    "airy spacing" vs "tight display").
    """

    def __init__(self, llm_client: Any = None) -> None:
        self._llm = llm_client

    def run(
        self,
        prompt: str,
        font: Optional["Font"] = None,
    ) -> MetricsResult:
        """Analyse *font* and apply spacing/kerning corrections."""
        from aifont.core.metrics import auto_space, get_kern_pairs

        if font is None:
            return MetricsResult(font=None, confidence=0.5)

        target_ratio = self._interpret_ratio(prompt)
        auto_space(font, target_ratio=target_ratio)
        pairs = get_kern_pairs(font)
        return MetricsResult(
            font=font,
            kern_pairs_updated=len(pairs),
            spacing_adjusted=True,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _interpret_ratio(self, prompt: str) -> float:
        """Map style keywords in *prompt* to a side-bearing ratio."""
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ("tight", "compact", "narrow")):
            return 0.08
        if any(w in prompt_lower for w in ("airy", "loose", "wide", "open")):
            return 0.22
        return 0.15
from aifont.agents.orchestrator import AgentResult

logger = logging.getLogger(__name__)


class MetricsAgent:
    """Automatically optimises spacing and kerning for a font.

    Example:
        >>> agent = MetricsAgent()
        >>> font = agent.run("airy spacing", font)
    """

    _SPACING_PRESETS = {
        "tight": 0.08,
        "normal": 0.12,
        "airy": 0.18,
        "display": 0.10,
    }

    def run(self, prompt: str, font: Font) -> Font:
        """Optimise metrics based on a style prompt.

        Args:
            prompt: Style hint (e.g. ``"airy spacing"``).
            font:   Font to optimise.

        Returns:
            The font with updated spacing.
        """
        logger.info("MetricsAgent: optimising metrics for prompt %r", prompt)
        ratio = 0.12  # default
        for keyword, preset_ratio in self._SPACING_PRESETS.items():
            if keyword in prompt.lower():
                ratio = preset_ratio
                break
        auto_space(font, target_ratio=ratio)
        return font
    """Analyses current font metrics via :mod:`aifont.core.metrics`,
    identifies issues (too tight, inconsistent sidebearings) and applies
    corrections.
    """

    def run(self, prompt: str, font: Font) -> AgentResult:
        logger.info("MetricsAgent: optimising metrics for prompt %r", prompt)
        return AgentResult(
            agent_name="MetricsAgent",
            success=True,
            confidence=0.85,
            message="Metrics optimisation deferred (font has no glyphs yet)",
        )
"""
aifont.agents.metrics_agent — automatic optimisation of kerning and spacing.

Tools exposed
-------------
- AnalyzeSpacing   — analyse current font metrics
- AutoKern         — generate kerning suggestions via fontforge AutoKern
- SetKernPair      — apply a single kern correction
- AutoSpace        — rebalance all side bearings
- SetSideBearings  — set side bearings for a specific glyph
- GenerateReport   — produce a structured before/after report

Acceptance criteria (Issue #17)
--------------------------------
- Automatic font analysis
- Context-based kerning suggestions
- Automatic correction application
- Detailed before/after report
- Tests on reference fonts (see tests/test_metrics_agent.py)
"""

from __future__ import annotations

import copy
import datetime
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from aifont.core.metrics import (
    KernPair,
    SideBearings,
    SpacingAnalysis,
    analyze_spacing,
    auto_kern,
    auto_space,
    get_kern_pairs,
    get_side_bearings,
    set_kern,
    set_side_bearings,
)


# ---------------------------------------------------------------------------
# Report data structures
# ---------------------------------------------------------------------------


@dataclass
class GlyphMetricsSnapshot:
    """Snapshot of a single glyph's spacing metrics."""

    glyph_name: str
    lsb: int
    rsb: int
    width: int


@dataclass
class MetricsReport:
    """
    Detailed before/after report produced by :class:`MetricsAgent`.

    Attributes
    ----------
    font_name:
        Name of the font that was processed.
    generated_at:
        ISO-8601 timestamp of report generation.
    style_intent:
        Free-text style intent provided by the caller (e.g. ``"airy"``).
    before:
        Spacing analysis captured *before* corrections.
    after:
        Spacing analysis captured *after* corrections.
    kern_pairs_added:
        Kern pairs that were added or updated.
    sidebearings_changed:
        Glyphs whose side bearings were modified.
    corrections_applied:
        Human-readable list of corrections applied.
    summary:
        One-line summary of the result.
    """

    font_name: str = ""
    generated_at: str = ""
    style_intent: str = ""
    before: Optional[SpacingAnalysis] = None
    after: Optional[SpacingAnalysis] = None
    kern_pairs_added: List[KernPair] = field(default_factory=list)
    sidebearings_changed: List[GlyphMetricsSnapshot] = field(default_factory=list)
    corrections_applied: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        """Return a plain-dict representation (suitable for JSON serialisation)."""
        d = {
            "font_name": self.font_name,
            "generated_at": self.generated_at,
            "style_intent": self.style_intent,
            "before": asdict(self.before) if self.before else None,
            "after": asdict(self.after) if self.after else None,
            "kern_pairs_added": [asdict(kp) for kp in self.kern_pairs_added],
            "sidebearings_changed": [asdict(sb) for sb in self.sidebearings_changed],
            "corrections_applied": self.corrections_applied,
            "summary": self.summary,
        }
        return d

    def __str__(self) -> str:  # pragma: no cover
        lines = [
            "=" * 60,
            f"MetricsAgent Report — {self.font_name}",
            f"Generated : {self.generated_at}",
            f"Intent    : {self.style_intent or '(none)'}",
            "=" * 60,
        ]
        if self.before:
            lines += [
                "BEFORE",
                f"  Glyphs        : {self.before.glyph_count}",
                f"  Kern pairs    : {self.before.kern_pair_count}",
                f"  Avg LSB       : {self.before.avg_lsb:.1f}",
                f"  Avg RSB       : {self.before.avg_rsb:.1f}",
                f"  Outliers      : {len(self.before.outlier_sidebearings)}",
                f"  Suggestions   : {'; '.join(self.before.suggestions) or 'none'}",
            ]
        if self.after:
            lines += [
                "AFTER",
                f"  Kern pairs    : {self.after.kern_pair_count}",
                f"  Avg LSB       : {self.after.avg_lsb:.1f}",
                f"  Avg RSB       : {self.after.avg_rsb:.1f}",
                f"  Outliers      : {len(self.after.outlier_sidebearings)}",
            ]
        if self.corrections_applied:
            lines.append("CORRECTIONS APPLIED")
            for c in self.corrections_applied:
                lines.append(f"  • {c}")
        lines += ["=" * 60, self.summary]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Style intent → spacing parameters
# ---------------------------------------------------------------------------

_STYLE_PROFILES: Dict[str, Dict] = {
    "airy": {"target_ratio": 0.20, "kern_threshold": 30},
    "tight": {"target_ratio": 0.08, "kern_threshold": 20},
    "display": {"target_ratio": 0.10, "kern_threshold": 40},
    "text": {"target_ratio": 0.15, "kern_threshold": 35},
    "default": {"target_ratio": 0.15, "kern_threshold": 50},
}


def _resolve_style_profile(style_intent: str) -> Dict:
    """Map a free-text intent to a numeric spacing profile."""
    intent_lower = style_intent.lower()
    for key in _STYLE_PROFILES:
        if key in intent_lower:
            return _STYLE_PROFILES[key]
    return _STYLE_PROFILES["default"]


# ---------------------------------------------------------------------------
# MetricsAgent
# ---------------------------------------------------------------------------


class MetricsAgent:
    """
    AI agent that automatically analyses and optimises font metrics.

    The agent operates entirely through :mod:`aifont.core.metrics` and never
    calls fontforge directly.

    Parameters
    ----------
    style_intent:
        Optional free-text hint describing the desired spacing feel,
        e.g. ``"airy"``, ``"tight display"``, ``"text"``.
        When not supplied the *default* profile is used.
    apply_autospace:
        If ``True`` (default) the agent will rebalance all side bearings.
    apply_autokern:
        If ``True`` (default) the agent will run AutoKern to generate or
        refresh kern pairs.
    kern_threshold:
        Minimum absolute kern value (in font units) to retain.
        Overridden by the style profile when *style_intent* is set.
    """

    def __init__(
        self,
        style_intent: str = "",
        apply_autospace: bool = True,
        apply_autokern: bool = True,
        kern_threshold: int = 50,
    ) -> None:
        self.style_intent = style_intent
        self.apply_autospace = apply_autospace
        self.apply_autokern = apply_autokern

        profile = _resolve_style_profile(style_intent)
        self._target_ratio: float = profile["target_ratio"]
        self._kern_threshold: int = profile.get("kern_threshold", kern_threshold)

    # ------------------------------------------------------------------
    # Tool: AnalyzeSpacing
    # ------------------------------------------------------------------

    def analyze_spacing(self, font) -> SpacingAnalysis:
        """
        Analyse the current spacing and kerning of *font*.

        Returns a :class:`~aifont.core.metrics.SpacingAnalysis` with glyph
        statistics, outlier side bearings, and human-readable suggestions.
        """
        return analyze_spacing(font)

    # ------------------------------------------------------------------
    # Tool: AutoKern
    # ------------------------------------------------------------------

    def auto_kern(self, font) -> List[KernPair]:
        """
        Run fontforge's AutoKern and return the resulting kern pairs.

        Only pairs whose absolute value is ≥ ``self._kern_threshold`` are
        returned.
        """
        return auto_kern(font, threshold=self._kern_threshold)

    # ------------------------------------------------------------------
    # Tool: SetKernPair
    # ------------------------------------------------------------------

    def set_kern_pair(self, font, left: str, right: str, value: int) -> None:
        """
        Set (or update) the kern value for the pair (*left*, *right*).
        """
        set_kern(font, left, right, value)

    # ------------------------------------------------------------------
    # Tool: AutoSpace
    # ------------------------------------------------------------------

    def auto_space(self, font) -> int:
        """
        Rebalance all glyph side bearings using the current style profile.

        Returns the number of glyphs modified.
        """
        return auto_space(font, target_ratio=self._target_ratio)

    # ------------------------------------------------------------------
    # Tool: SetSideBearings
    # ------------------------------------------------------------------

    def set_side_bearings(
        self,
        font,
        glyph_name: str,
        lsb: Optional[int] = None,
        rsb: Optional[int] = None,
    ) -> bool:
        """
        Set the left and/or right side bearings for *glyph_name*.
        """
        return set_side_bearings(font, glyph_name, lsb=lsb, rsb=rsb)

    # ------------------------------------------------------------------
    # Tool: GenerateReport
    # ------------------------------------------------------------------

    def generate_report(
        self,
        font,
        before: SpacingAnalysis,
        after: SpacingAnalysis,
        kern_pairs_added: List[KernPair],
        sidebearings_changed: List[GlyphMetricsSnapshot],
        corrections_applied: List[str],
    ) -> MetricsReport:
        """
        Produce a structured before/after :class:`MetricsReport`.
        """
        try:
            font_name = font.fontname
        except Exception:
            font_name = str(font)

        delta_pairs = after.kern_pair_count - before.kern_pair_count
        delta_outliers = len(before.outlier_sidebearings) - len(after.outlier_sidebearings)
        summary = (
            f"Processed '{font_name}': "
            f"{delta_pairs:+d} kern pairs, "
            f"{delta_outliers} outlier(s) resolved, "
            f"{len(corrections_applied)} correction(s) applied."
        )

        return MetricsReport(
            font_name=font_name,
            generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            style_intent=self.style_intent,
            before=before,
            after=after,
            kern_pairs_added=kern_pairs_added,
            sidebearings_changed=sidebearings_changed,
            corrections_applied=corrections_applied,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # High-level: run (full pipeline)
    # ------------------------------------------------------------------

    def run(self, font) -> MetricsReport:
        """
        Execute the full metrics optimisation pipeline on *font*.

        Steps
        -----
        1. **AnalyzeSpacing** — capture before-state.
        2. **AutoSpace** (optional) — rebalance side bearings.
        3. **AutoKern** (optional) — generate or refresh kern pairs.
        4. **SetKernPair** — apply any extra corrections derived from
           the before-analysis (e.g. fixing inconsistent pairs).
        5. **AnalyzeSpacing** — capture after-state.
        6. **GenerateReport** — return the structured report.

        Returns
        -------
        MetricsReport
            Detailed before/after report.
        """
        corrections: List[str] = []
        kern_pairs_added: List[KernPair] = []
        sidebearings_changed: List[GlyphMetricsSnapshot] = []

        # Step 1 — before snapshot.
        before = self.analyze_spacing(font)

        # Step 2 — AutoSpace.
        if self.apply_autospace:
            n = self.auto_space(font)
            if n:
                corrections.append(f"AutoSpace: rebalanced side bearings on {n} glyph(s).")
                # Record which glyphs changed.
                ff = _get_ff_font(font)
                for name in list(ff)[:n]:
                    sb = get_side_bearings(font, name)
                    if sb:
                        try:
                            width = ff[name].width
                        except Exception:
                            width = 0
                        sidebearings_changed.append(
                            GlyphMetricsSnapshot(
                                glyph_name=name,
                                lsb=sb.lsb,
                                rsb=sb.rsb,
                                width=width,
                            )
                        )

        # Step 3 — AutoKern.
        if self.apply_autokern:
            pairs = self.auto_kern(font)
            kern_pairs_added.extend(pairs)
            if pairs:
                corrections.append(f"AutoKern: generated {len(pairs)} kern pair(s).")

        # Step 4 — Fix inconsistent pairs from before-analysis.
        if before.inconsistent_pairs:
            for kp in before.inconsistent_pairs:
                self.set_kern_pair(font, kp.left, kp.right, kp.value)
            corrections.append(
                f"Fixed {len(before.inconsistent_pairs)} inconsistent kern pair(s)."
            )

        # Step 5 — after snapshot.
        after = self.analyze_spacing(font)

        # Step 6 — report.
        return self.generate_report(
            font,
            before=before,
            after=after,
            kern_pairs_added=kern_pairs_added,
            sidebearings_changed=sidebearings_changed,
            corrections_applied=corrections,
        )


# ---------------------------------------------------------------------------
# Module-level convenience helper (import fontforge not required at top level)
# ---------------------------------------------------------------------------


def _get_ff_font(font_or_wrapper):
    """Unwrap an aifont Font wrapper to its raw fontforge object."""
    if hasattr(font_or_wrapper, "_ff_font"):
        return font_or_wrapper._ff_font
    return font_or_wrapper
