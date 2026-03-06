"""aifont.agents.style_agent — typographic style transfer and application agent.

The :class:`StyleAgent` applies and transfers typographic styles.  It
exposes five *tools* that can be called individually or through a
natural-language prompt dispatcher:

Tools
-----
ApplyStroke
    Boldify / lighten glyphs by expanding or contracting outline strokes.
ApplySlant
    Apply an italic effect via horizontal shear + optical corrections.
TransformGlyph
    Apply arbitrary affine transformations to individual glyphs.
InterpolateStyle
    Blend the style of a *reference* font into a *target* font.
AnalyzeStyle
    Extract a :class:`~aifont.core.analyzer.StyleProfile` from a font.

Architecture constraint
-----------------------
This agent uses **only** ``aifont.core`` APIs.  It never imports
``fontforge`` directly.
"""

from __future__ import annotations

import contextlib
import math
import re
from dataclasses import dataclass, field

from aifont.core import contour as _contour
from aifont.core.analyzer import StyleProfile, analyze_style
from aifont.core.font import Font
from aifont.core.glyph import Glyph

# ---------------------------------------------------------------------------
# Result data structures
# ---------------------------------------------------------------------------


@dataclass
class StyleTransferResult:
    """Result returned by every :class:`StyleAgent` tool.

    Attributes
    ----------
    font:
        The modified :class:`~aifont.core.font.Font` (modified in-place).
    changes_applied:
        Human-readable list of transformations that were applied.
    before_profile:
        :class:`~aifont.core.analyzer.StyleProfile` captured *before* the
        transformations.
    after_profile:
        :class:`~aifont.core.analyzer.StyleProfile` captured *after* the
        transformations.
    confidence:
        Agent confidence in the result (0.0–1.0).
    target_font:
        Alias for :attr:`font` — the font that was modified.
    """

    font: Font | None = None
    changes_applied: list[str] = field(default_factory=list)
    before_profile: StyleProfile | None = None
    after_profile: StyleProfile | None = None
    confidence: float = 0.5
    target_font: Font | None = None

    def __post_init__(self) -> None:
        # Keep font and target_font in sync
        if self.target_font is None and self.font is not None:
            self.target_font = self.font
        elif self.font is None and self.target_font is not None:
            self.font = self.target_font

    def summary(self) -> str:
        """Return a human-readable summary of the result."""
        lines = ["StyleTransferResult"]
        lines.append(f"  Changes applied ({len(self.changes_applied)}):")
        for change in self.changes_applied:
            lines.append(f"    • {change}")
        if self.before_profile:
            lines.append(f"  Before: {self.before_profile.summary()}")
        if self.after_profile:
            lines.append(f"  After:  {self.after_profile.summary()}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt → tool mapping
# ---------------------------------------------------------------------------

_BOLD_KEYWORDS = ("bold", "heavy", "black", "thick", "fat", "bolder", "plus gras", "gras")
_LIGHT_KEYWORDS = ("light", "thin", "lighter", "maigre", "léger", "leger")
_ITALIC_KEYWORDS = ("italic", "slant", "oblique", "italique", "penché", "penche")
_VINTAGE_KEYWORDS = ("vintage", "retro", "rétro", "old", "classic", "antique", "vieux")
_TRANSFER_KEYWORDS = ("inspire", "style of", "like", "transfer", "transférer", "imiter")


def _detect_intent(prompt: str) -> str:
    """Map a free-text prompt to one of the internal intent labels."""
    p = prompt.lower()

    def _matches(keywords: tuple) -> bool:
        for kw in keywords:
            if " " in kw:
                if kw in p:
                    return True
            else:
                if re.search(r"\b" + re.escape(kw), p):
                    return True
        return False

    if _matches(_BOLD_KEYWORDS):
        return "bold"
    if _matches(_LIGHT_KEYWORDS):
        return "light"
    if _matches(_ITALIC_KEYWORDS):
        return "italic"
    if _matches(_VINTAGE_KEYWORDS):
        return "vintage"
    if _matches(_TRANSFER_KEYWORDS):
        return "transfer"
    return "unknown"


#: Alias for :class:`StyleTransferResult` (used by tests and external callers).
StyleResult = StyleTransferResult

# ---------------------------------------------------------------------------
# StyleAgent
# ---------------------------------------------------------------------------


class StyleAgent:
    """Agent that applies and transfers typographic styles.

    Parameters
    ----------
    default_stroke_delta:
        Default stroke expansion (in font units) used when
        :meth:`apply_stroke` is called without an explicit *stroke_width*.
    default_slant_angle:
        Default slant angle (degrees) used when :meth:`apply_slant` is
        called without an explicit *angle*.
    optical_corrections:
        When ``True`` (default) :meth:`apply_slant` applies small optical
        corrections (vertical scaling, width adjustment) to improve visual
        quality.
    """

    def __init__(
        self,
        default_stroke_delta: float = 30.0,
        default_slant_angle: float = 12.0,
        optical_corrections: bool = True,
    ) -> None:
        self.default_stroke_delta = default_stroke_delta
        self.default_slant_angle = default_slant_angle
        self.optical_corrections = optical_corrections

    # ------------------------------------------------------------------
    # Public dispatcher
    # ------------------------------------------------------------------

    def run(
        self,
        prompt: str,
        font: Font | None = None,
        reference_font: Font | None = None,
        source_font: Font | None = None,
        stroke_width: float | None = None,
        slant_angle: float | None = None,
        interpolation_factor: float = 0.5,
    ) -> StyleTransferResult:
        """Dispatch a natural-language *prompt* to the appropriate tool.

        Parameters
        ----------
        prompt:
            A free-text instruction such as ``"Make this font more bold"``.
        font:
            The :class:`~aifont.core.font.Font` to transform.
        reference_font:
            Optional reference font used for transfer/inspire intents.
        source_font:
            Alias for *reference_font*.
        stroke_width:
            Override the stroke delta for bold/light operations.
        slant_angle:
            Override the slant angle for italic operations.
        interpolation_factor:
            Blend factor (0.0–1.0) for style interpolation.

        Returns
        -------
        StyleTransferResult
        """
        # Normalise source_font → reference_font alias
        if source_font is not None and reference_font is None:
            reference_font = source_font

        if font is None:
            return StyleTransferResult(font=None, confidence=0.5)

        intent = _detect_intent(prompt)

        if intent == "bold":
            delta = stroke_width if stroke_width is not None else self.default_stroke_delta
            return self.apply_stroke(font, stroke_width=delta)

        if intent == "light":
            delta = stroke_width if stroke_width is not None else -self.default_stroke_delta
            return self.apply_stroke(font, stroke_width=delta)

        if intent == "italic":
            angle = slant_angle if slant_angle is not None else self.default_slant_angle
            return self.apply_slant(font, angle=angle)

        if intent == "vintage":
            return self._apply_vintage(font)

        if intent == "transfer":
            if reference_font is None:
                return StyleTransferResult(font=font, confidence=0.5)
            return self.transfer_style(font, reference_font, factor=interpolation_factor)

        if reference_font is not None:
            return self.transfer_style(font, reference_font, factor=interpolation_factor)

        before = analyze_style(font)
        return StyleTransferResult(
            font=font,
            changes_applied=[f"Unknown intent in prompt: {prompt!r}. No changes applied."],
            before_profile=before,
            after_profile=before,
            confidence=0.5,
            target_font=font,
        )

    def _compute_scale(self, source: Font, target: Font) -> float:
        """Compute the EM-size scale factor from *source* to *target*.

        Returns ``target.em / source.em``, defaulting to ``1.0`` on error.
        """
        try:
            src_ff = getattr(source, "_font", source)
            dst_ff = getattr(target, "_font", target)
            src_em = float(getattr(src_ff, "em", 1000) or 1000)
            dst_em = float(getattr(dst_ff, "em", 1000) or 1000)
            return dst_em / src_em if src_em > 0 else 1.0
        except Exception:  # noqa: BLE001
            return 1.0

    # ------------------------------------------------------------------
    # Tool: AnalyzeStyle
    # ------------------------------------------------------------------

    def analyze_style(self, font: Font) -> StyleProfile:
        """Analyse the typographic style of *font*."""
        return analyze_style(font)

    # ------------------------------------------------------------------
    # Tool: ApplyStroke
    # ------------------------------------------------------------------

    def apply_stroke(
        self,
        font: Font,
        stroke_width: float,
        join_type: str = "miter",
        glyph_names: list[str] | None = None,
    ) -> StyleTransferResult:
        """Apply a stroke expansion (boldification) to all or selected glyphs."""
        before = analyze_style(font)
        changes: list[str] = []
        processed = 0

        for glyph in font.glyphs:
            if glyph_names is not None and glyph.name not in glyph_names:
                continue
            try:
                _contour.apply_stroke(glyph, stroke_width, join_type)
                processed += 1
            except Exception as exc:
                changes.append(f"  ⚠ Skipped {glyph.name!r}: {exc}")

        direction = "expanded" if stroke_width > 0 else "contracted"
        changes.insert(
            0,
            f"ApplyStroke: {direction} {processed} glyph(s) by {abs(stroke_width):.1f}u "
            f"(join={join_type})",
        )

        after = analyze_style(font)
        return StyleTransferResult(
            font=font,
            changes_applied=changes,
            before_profile=before,
            after_profile=after,
        )

    # ------------------------------------------------------------------
    # Tool: ApplySlant
    # ------------------------------------------------------------------

    def apply_slant(
        self,
        font: Font,
        angle: float,
        optical_corrections: bool | None = None,
        glyph_names: list[str] | None = None,
    ) -> StyleTransferResult:
        """Apply italic slant to all or selected glyphs."""
        use_corrections = (
            optical_corrections if optical_corrections is not None else self.optical_corrections
        )

        before = analyze_style(font)
        changes: list[str] = []
        processed = 0

        for glyph in font.glyphs:
            if glyph_names is not None and glyph.name not in glyph_names:
                continue
            try:
                _contour.apply_slant(glyph, angle_deg=angle)
                if use_corrections:
                    self._apply_optical_corrections(glyph, angle)
                processed += 1
            except Exception as exc:
                changes.append(f"  ⚠ Skipped {glyph.name!r}: {exc}")

        changes.insert(
            0,
            f"ApplySlant: slanted {processed} glyph(s) by {angle:.1f}° "
            f"(optical_corrections={use_corrections})",
        )

        with contextlib.suppress(Exception):
            font.italic_angle = angle

        after = analyze_style(font)
        return StyleTransferResult(
            font=font,
            changes_applied=changes,
            before_profile=before,
            after_profile=after,
        )

    # ------------------------------------------------------------------
    # Tool: TransformGlyph
    # ------------------------------------------------------------------

    def transform_glyph(
        self,
        font: Font,
        matrix: tuple[float, float, float, float, float, float],
        glyph_names: list[str] | None = None,
    ) -> StyleTransferResult:
        """Apply an affine transformation matrix to selected glyphs."""
        before = analyze_style(font)
        changes: list[str] = []
        processed = 0

        for glyph in font.glyphs:
            if glyph_names is not None and glyph.name not in glyph_names:
                continue
            try:
                _contour.transform(glyph, matrix)
                processed += 1
            except Exception as exc:
                changes.append(f"  ⚠ Skipped {glyph.name!r}: {exc}")

        changes.insert(
            0,
            f"TransformGlyph: applied matrix {matrix} to {processed} glyph(s)",
        )

        after = analyze_style(font)
        return StyleTransferResult(
            font=font,
            changes_applied=changes,
            before_profile=before,
            after_profile=after,
        )

    # ------------------------------------------------------------------
    # Tool: InterpolateStyle
    # ------------------------------------------------------------------

    def interpolate_style(
        self,
        target: Font,
        reference: Font,
        factor: float = 0.5,
    ) -> StyleTransferResult:
        """Blend the style of *reference* into *target* by *factor*."""
        factor = max(0.0, min(1.0, factor))
        before = analyze_style(target)
        ref_profile = analyze_style(reference)
        changes: list[str] = [
            f"InterpolateStyle: factor={factor:.2f}, reference={reference.family_name!r}"
        ]

        stroke_delta = (ref_profile.stroke_width - before.stroke_width) * factor
        if abs(stroke_delta) > 1.0:
            stroke_result = self.apply_stroke(target, stroke_width=stroke_delta)
            changes.extend(stroke_result.changes_applied[1:])

        angle_delta = (ref_profile.italic_angle - before.italic_angle) * factor
        if abs(angle_delta) > 0.5:
            slant_result = self.apply_slant(target, angle=angle_delta)
            changes.extend(slant_result.changes_applied[1:])

        after = analyze_style(target)
        return StyleTransferResult(
            font=target,
            changes_applied=changes,
            before_profile=before,
            after_profile=after,
        )

    # ------------------------------------------------------------------
    # Style transfer
    # ------------------------------------------------------------------

    def transfer_style(
        self,
        target: Font,
        reference: Font,
        factor: float = 1.0,
    ) -> StyleTransferResult:
        """Transfer the typographic style of *reference* to *target*."""
        result = self.interpolate_style(target, reference, factor=factor)
        result.changes_applied.insert(0, "TransferStyle: full style transfer")
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_optical_corrections(self, glyph: Glyph, angle_deg: float) -> None:
        """Apply optical corrections after slanting."""
        h_expand = 1.0 + (angle_deg * 0.005)
        v_contract = 1.0 - (angle_deg * 0.002)
        _contour.transform(glyph, (h_expand, 0.0, 0.0, v_contract, 0.0, 0.0))

    def _apply_vintage(self, font: Font) -> StyleTransferResult:
        """Apply a vintage / retro aesthetic transformation."""
        em = font.em_size
        stroke_delta = em * 0.015
        before = analyze_style(font)
        changes: list[str] = ["ApplyVintage: vintage/retro style"]

        stroke_result = self.apply_stroke(font, stroke_width=stroke_delta)
        changes.extend(stroke_result.changes_applied)

        slant_result = self.apply_slant(font, angle=3.0, optical_corrections=False)
        changes.extend(slant_result.changes_applied)

        condensed_result = self.transform_glyph(font, matrix=(0.95, 0.0, 0.0, 1.0, 0.0, 0.0))
        changes.extend(condensed_result.changes_applied)

        after = analyze_style(font)
        return StyleTransferResult(
            font=font,
            changes_applied=changes,
            before_profile=before,
            after_profile=after,
        )


# Suppress unused import warnings for math (used in future extensions)
_ = math.pi
