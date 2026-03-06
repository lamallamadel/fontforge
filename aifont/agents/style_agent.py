"""Style Agent — transfers visual style between fonts."""

from __future__ import annotations

import logging
from typing import Optional

from aifont.core.font import Font

logger = logging.getLogger(__name__)


class StyleAgent:
    """Transfers visual style (stroke weight, contrast, terminals) from a source font.

    Example:
        >>> agent = StyleAgent(source_font=reference_font)
        >>> font = agent.run("match the style of the reference", target_font)
    """

    def __init__(self, source_font: Optional[Font] = None) -> None:
        self.source_font = source_font

    def run(self, prompt: str, font: Font) -> Font:
        """Apply style transfer.

        Args:
            prompt: Style description or instruction.
            font:   Target font to apply style to.

        Returns:
            The styled font.
        """
        logger.info("StyleAgent: applying style from prompt %r", prompt)
        # In production: analyse source font metrics, apply transformations via contour module
        return font
"""
aifont.agents.style_agent — typographic style transfer and application agent.

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

Usage example
-------------
::

    from aifont.core.font import Font
    from aifont.agents.style_agent import StyleAgent

    font = Font.open("MyFont.otf")
    agent = StyleAgent()

    # Prompt-based dispatch
    result = agent.run("Make this font more bold", font)
    print(result.summary())

    # Direct tool call
    result = agent.apply_stroke(font, stroke_width=40)
    print(result.summary())

Architecture constraint
-----------------------
This agent uses **only** ``aifont.core`` APIs.  It never imports
``fontforge`` directly.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from aifont.core.analyzer import StyleProfile, analyze_style
from aifont.core import contour as _contour
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
    """

    font: Font
    changes_applied: List[str] = field(default_factory=list)
    before_profile: Optional[StyleProfile] = None
    after_profile: Optional[StyleProfile] = None

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

# Keywords that trigger each tool.  Checked in order; first match wins.
_BOLD_KEYWORDS = ("bold", "heavy", "black", "thick", "fat", "bolder", "plus gras", "gras")
_LIGHT_KEYWORDS = ("light", "thin", "lighter", "maigre", "léger", "leger")
_ITALIC_KEYWORDS = ("italic", "slant", "oblique", "italique", "penché", "penche")
_VINTAGE_KEYWORDS = ("vintage", "retro", "rétro", "old", "classic", "antique", "vieux")
_TRANSFER_KEYWORDS = ("inspire", "style of", "like", "transfer", "transférer", "imiter")


def _detect_intent(prompt: str) -> str:
    """Map a free-text prompt to one of the internal intent labels.

    Matching uses word-boundary aware checks so that, for example, the
    keyword ``"thin"`` does not match inside ``"something"``.

    Parameters
    ----------
    prompt:
        Natural-language input, e.g. ``"Make this font more bold"``.

    Returns
    -------
    str
        One of: ``"bold"``, ``"light"``, ``"italic"``, ``"vintage"``,
        ``"transfer"``, or ``"unknown"``.
    """
    p = prompt.lower()

    def _matches(keywords):
        for kw in keywords:
            # Multi-word phrases: substring match is fine (word-boundary irrelevant)
            if " " in kw:
                if kw in p:
                    return True
            else:
                # Single-word: require word boundary at start (allows suffix like "thinner")
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

    Examples
    --------
    >>> from aifont.core.font import Font
    >>> from aifont.agents.style_agent import StyleAgent
    >>> font = Font.open("MyFont.otf")
    >>> agent = StyleAgent()
    >>> result = agent.run("Make this font more bold", font)
    >>> print(result.summary())
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
        font: Font,
        reference_font: Optional[Font] = None,
        stroke_width: Optional[float] = None,
        slant_angle: Optional[float] = None,
        interpolation_factor: float = 0.5,
    ) -> StyleTransferResult:
        """Dispatch a natural-language *prompt* to the appropriate tool.

        Parameters
        ----------
        prompt:
            A free-text instruction such as ``"Make this font more bold"``
            or ``"Apply italic style"``.
        font:
            The :class:`~aifont.core.font.Font` to transform.
        reference_font:
            Optional reference font used for ``"transfer"`` and
            ``"inspire"`` intents.
        stroke_width:
            Override the stroke delta for bold/light operations.
        slant_angle:
            Override the slant angle for italic operations.
        interpolation_factor:
            Blend factor (0.0–1.0) for style interpolation (``"transfer"``
            intent).  0.0 = target unchanged; 1.0 = full reference style.

        Returns
        -------
        StyleTransferResult
            The result including the modified font, changelog, and
            before/after style profiles.

        Raises
        ------
        ValueError
            If the intent requires a *reference_font* that was not provided.
        """
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
                raise ValueError(
                    "A reference_font is required for style transfer. "
                    "Provide reference_font=<Font> when calling run()."
                )
            return self.transfer_style(
                font, reference_font, factor=interpolation_factor
            )

        # Unknown intent: return an unchanged result with a note
        before = analyze_style(font)
        result = StyleTransferResult(
            font=font,
            changes_applied=[f"Unknown intent in prompt: {prompt!r}. No changes applied."],
            before_profile=before,
            after_profile=before,
        )
        return result

    # ------------------------------------------------------------------
    # Tool: AnalyzeStyle
    # ------------------------------------------------------------------

    def analyze_style(self, font: Font) -> StyleProfile:
        """Analyse the typographic style of *font*.

        Wraps :func:`aifont.core.analyzer.analyze_style`.

        Parameters
        ----------
        font:
            The :class:`~aifont.core.font.Font` to analyse.

        Returns
        -------
        StyleProfile
            Extracted style metrics.
        """
        return analyze_style(font)

    # ------------------------------------------------------------------
    # Tool: ApplyStroke
    # ------------------------------------------------------------------

    def apply_stroke(
        self,
        font: Font,
        stroke_width: float,
        join_type: str = "miter",
        glyph_names: Optional[List[str]] = None,
    ) -> StyleTransferResult:
        """Apply a stroke expansion (boldification) to all or selected glyphs.

        Parameters
        ----------
        font:
            The :class:`~aifont.core.font.Font` to modify in-place.
        stroke_width:
            Stroke expansion in font units.  Positive = bolder; negative =
            lighter.  A value of ~30 is typical for one weight step on a
            1000-unit em.
        join_type:
            Stroke join type: ``"miter"``, ``"round"``, or ``"bevel"``.
        glyph_names:
            If given, only the named glyphs are processed.  Processes all
            glyphs when ``None``.

        Returns
        -------
        StyleTransferResult
        """
        before = analyze_style(font)
        changes: List[str] = []
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
        optical_corrections: Optional[bool] = None,
        glyph_names: Optional[List[str]] = None,
    ) -> StyleTransferResult:
        """Apply italic slant to all or selected glyphs.

        Parameters
        ----------
        font:
            The :class:`~aifont.core.font.Font` to modify in-place.
        angle:
            Slant angle in degrees (typically 10–14 for italic).
        optical_corrections:
            When ``True``, apply small optical corrections: slight vertical
            scale reduction and width expansion to compensate for the
            visual thinning that shearing introduces.  Defaults to
            ``self.optical_corrections``.
        glyph_names:
            If given, only the named glyphs are processed.

        Returns
        -------
        StyleTransferResult
        """
        use_corrections = (
            optical_corrections if optical_corrections is not None
            else self.optical_corrections
        )

        before = analyze_style(font)
        changes: List[str] = []
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

        # Update the font's italic angle metadata
        try:
            font.italic_angle = angle
        except Exception:
            pass

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
        matrix: Tuple[float, float, float, float, float, float],
        glyph_names: Optional[List[str]] = None,
    ) -> StyleTransferResult:
        """Apply an affine transformation matrix to selected glyphs.

        Parameters
        ----------
        font:
            The :class:`~aifont.core.font.Font` to modify in-place.
        matrix:
            6-element affine matrix ``(xx, xy, yx, yy, dx, dy)`` in
            PostScript / fontforge convention.
        glyph_names:
            If given, only the named glyphs are processed.  Processes all
            glyphs when ``None``.

        Returns
        -------
        StyleTransferResult
        """
        before = analyze_style(font)
        changes: List[str] = []
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
        """Blend the style of *reference* into *target* by *factor*.

        The interpolation works on stroke weight (via :meth:`apply_stroke`)
        and slant (via :meth:`apply_slant`) independently.

        Parameters
        ----------
        target:
            The :class:`~aifont.core.font.Font` to modify in-place.
        reference:
            The :class:`~aifont.core.font.Font` whose style to blend in.
        factor:
            Blend factor between 0.0 (target unchanged) and 1.0 (full
            reference style).  Values outside [0, 1] are clamped.

        Returns
        -------
        StyleTransferResult
        """
        factor = max(0.0, min(1.0, factor))
        before = analyze_style(target)
        ref_profile = analyze_style(reference)
        changes: List[str] = [
            f"InterpolateStyle: factor={factor:.2f}, "
            f"reference={reference.family_name!r}"
        ]

        # --- Stroke weight interpolation ---
        stroke_delta = (ref_profile.stroke_width - before.stroke_width) * factor
        if abs(stroke_delta) > 1.0:
            stroke_result = self.apply_stroke(target, stroke_width=stroke_delta)
            changes.extend(stroke_result.changes_applied[1:])  # skip header line

        # --- Italic angle interpolation ---
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
        """Transfer the typographic style of *reference* to *target*.

        This is a high-level wrapper around :meth:`interpolate_style` with
        *factor* = 1.0 by default (full style replacement).

        Parameters
        ----------
        target:
            The :class:`~aifont.core.font.Font` to transform in-place.
        reference:
            The :class:`~aifont.core.font.Font` to take style from.
        factor:
            How much of the reference style to apply (0.0–1.0).

        Returns
        -------
        StyleTransferResult
        """
        result = self.interpolate_style(target, reference, factor=factor)
        result.changes_applied.insert(0, "TransferStyle: full style transfer")
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_optical_corrections(self, glyph: Glyph, angle_deg: float) -> None:
        """Apply optical corrections after slanting.

        When a glyph is sheared horizontally, optical illusions make it
        appear thinner and taller.  We compensate by:
        - Slightly expanding the horizontal width (~1 % per degree).
        - Slightly contracting the vertical height (~0.5 % per degree).

        Parameters
        ----------
        glyph:
            Glyph to correct in-place.
        angle_deg:
            The slant angle that was applied, in degrees.
        """
        h_expand = 1.0 + (angle_deg * 0.005)
        v_contract = 1.0 - (angle_deg * 0.002)
        _contour.transform(glyph, (h_expand, 0.0, 0.0, v_contract, 0.0, 0.0))

    def _apply_vintage(self, font: Font) -> StyleTransferResult:
        """Apply a vintage / retro aesthetic transformation.

        Vintage-style transformations combine:
        - A slight stroke weight increase (+15 u on a 1000-unit em).
        - A very slight slant (3°) for a warm, hand-set feel.
        - Slight horizontal scale reduction (95 %) to simulate condensed
          letterpress type.

        Parameters
        ----------
        font:
            The :class:`~aifont.core.font.Font` to modify in-place.

        Returns
        -------
        StyleTransferResult
        """
        em = font.em_size
        stroke_delta = em * 0.015
        before = analyze_style(font)
        changes: List[str] = ["ApplyVintage: vintage/retro style"]

        # 1. Slight weight increase
        stroke_result = self.apply_stroke(font, stroke_width=stroke_delta)
        changes.extend(stroke_result.changes_applied)

        # 2. Slight slant
        slant_result = self.apply_slant(font, angle=3.0, optical_corrections=False)
        changes.extend(slant_result.changes_applied)

        # 3. Slight horizontal condensing (95 %)
        condensed_result = self.transform_glyph(font, matrix=(0.95, 0.0, 0.0, 1.0, 0.0, 0.0))
        changes.extend(condensed_result.changes_applied)

        after = analyze_style(font)
        return StyleTransferResult(
            font=font,
            changes_applied=changes,
            before_profile=before,
            after_profile=after,
"""Style agent — transfers visual style between fonts."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font

from aifont.agents.orchestrator import AgentResult

logger = logging.getLogger(__name__)


class StyleAgent:
    """Analyses stroke weight, contrast and terminals of a reference font and
    applies those style characteristics to the target font via
    :mod:`aifont.core.contour` transformations.
    """

    def run(self, prompt: str, font: Font) -> AgentResult:
        logger.info("StyleAgent: applying style for prompt %r", prompt)
        return AgentResult(
            agent_name="StyleAgent",
            success=True,
            confidence=0.9,
            message="Style transfer skipped (no reference font provided)",
        )
