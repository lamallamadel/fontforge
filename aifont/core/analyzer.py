"""
aifont.core.analyzer — font analysis and style diagnostics.

This module provides functions to extract stylistic metrics from a font,
including stroke weight, contrast, serif detection, italic angle, and
key vertical proportions.  Results are returned as a :class:`StyleProfile`
dataclass that is consumed by :mod:`aifont.agents.style_agent`.

Architecture constraint
-----------------------
DO NOT modify FontForge source code.  All font access goes through
:class:`~aifont.core.font.Font` wrappers.

Typical usage
-------------
>>> from aifont.core.font import Font
>>> from aifont.core.analyzer import analyze_style
>>>
>>> font = Font.open("MyFont.otf")
>>> profile = analyze_style(font)
>>> print(profile.weight_class, profile.italic_angle)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from aifont.core.font import Font


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class StyleProfile:
    """Stylistic metrics extracted from a font.

    All measurements are in font units unless stated otherwise.

    Attributes
    ----------
    stroke_width:
        Estimated average stroke width (thin stems for high-contrast fonts).
    stroke_contrast:
        Ratio of thick to thin stroke: 0.0 = monolinear, approaching 1.0 =
        extreme contrast.
    italic_angle:
        Italic slant angle in degrees (0 = upright).
    x_height:
        Estimated x-height in font units.
    cap_height:
        Estimated cap-height in font units.
    ascender:
        Font ascender value in font units.
    descender:
        Font descender value in font units (positive number).
    em_size:
        Units-per-em for the font.
    has_serifs:
        Heuristic serif detection flag.
    weight_class:
        Estimated CSS weight class (100–900).
    glyph_count:
        Total number of glyphs analysed.
    notes:
        Free-text observations generated during analysis.
    """

    stroke_width: float = 0.0
    stroke_contrast: float = 0.0
    italic_angle: float = 0.0
    x_height: float = 0.0
    cap_height: float = 0.0
    ascender: float = 800.0
    descender: float = 200.0
    em_size: int = 1000
    has_serifs: bool = False
    weight_class: int = 400
    glyph_count: int = 0
    notes: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """Return a human-readable one-line summary."""
        serif_label = "serif" if self.has_serifs else "sans-serif"
        angle_label = f", italic {self.italic_angle:.1f}°" if self.italic_angle else ""
        return (
            f"Weight {self.weight_class}, {serif_label}{angle_label}, "
            f"stroke {self.stroke_width:.0f}u, "
            f"contrast {self.stroke_contrast:.2f}, "
            f"x-height {self.x_height:.0f}u"
        )


# ---------------------------------------------------------------------------
# Glyph helpers
# ---------------------------------------------------------------------------


def _bounding_box(ff_glyph: object):
    """Return the bounding box of a raw fontforge glyph or None."""
    bb = getattr(ff_glyph, "boundingBox", None)
    if callable(bb):
        try:
            return bb()
        except Exception:
            return None
    return None


def _glyph_width(ff_glyph: object) -> Optional[int]:
    """Return the advance width of a raw fontforge glyph or None."""
    w = getattr(ff_glyph, "width", None)
    if w is None:
        return None
    return int(w)


# ---------------------------------------------------------------------------
# Heuristic estimators
# ---------------------------------------------------------------------------


def _estimate_stroke_width(font: Font) -> float:
    """Estimate average stroke width from glyph bounding-box height ratios.

    We sample vertical extents for lowercase glyphs (a–z) and use the
    assumption that stroke width ≈ 10–15 % of cap-height for regular weight.
    """
    em = max(font.em_size, 1)
    # Use the 'o' glyph as a proxy: its inner counter height vs outer height
    # gives an approximation of stroke weight.
    for glyph_name in ("o", "O", "n", "H"):
        try:
            ff_g = font.raw[glyph_name]
        except (KeyError, TypeError):
            continue
        bb = _bounding_box(ff_g)
        if bb is None:
            continue
        xmin, ymin, xmax, ymax = bb
        height = ymax - ymin
        width = xmax - xmin
        if height > 0 and width > 0:
            # Stroke width heuristic: ~12 % of the smaller dimension
            return min(height, width) * 0.12
    # Fallback: estimate from em size
    return em * 0.08


def _estimate_x_height(font: Font) -> float:
    """Estimate x-height from the bounding box of lowercase 'x' or 'o'."""
    for glyph_name in ("x", "o", "n", "e"):
        try:
            ff_g = font.raw[glyph_name]
        except (KeyError, TypeError):
            continue
        bb = _bounding_box(ff_g)
        if bb is None:
            continue
        _, ymin, _, ymax = bb
        height = ymax - ymin
        if height > 0:
            return float(height)
    return font.em_size * 0.50


def _estimate_cap_height(font: Font) -> float:
    """Estimate cap-height from the bounding box of uppercase 'H' or 'I'."""
    for glyph_name in ("H", "I", "A", "E"):
        try:
            ff_g = font.raw[glyph_name]
        except (KeyError, TypeError):
            continue
        bb = _bounding_box(ff_g)
        if bb is None:
            continue
        _, ymin, _, ymax = bb
        height = ymax - ymin
        if height > 0:
            return float(height)
    return font.em_size * 0.70


def _estimate_stroke_contrast(font: Font, stroke_width: float) -> float:
    """Estimate stroke contrast ratio from thick/thin proportions.

    Uses the diagonal strokes of 'O' as a proxy: a monolinear font has
    nearly equal horizontal and vertical stroke widths; a high-contrast
    font has a much larger vertical stem.
    """
    em = max(font.em_size, 1)
    try:
        ff_g = font.raw["O"]
    except (KeyError, TypeError):
        ff_g = None

    if ff_g is not None:
        bb = _bounding_box(ff_g)
        if bb is not None:
            xmin, ymin, xmax, ymax = bb
            w = xmax - xmin
            h = ymax - ymin
            if w > 0 and h > 0:
                # Ratio of thin (horizontal) to thick (vertical) stems.
                # This is a rough heuristic based on counter proportions.
                ratio = abs(w - h) / max(w, h)
                return min(ratio, 1.0)
    # Fallback heuristic
    thick = stroke_width
    thin = thick * 0.4
    if thick > 0:
        return max(0.0, min(1.0, 1.0 - thin / thick))
    return 0.0


def _detect_serifs(font: Font) -> bool:
    """Heuristic serif detection.

    Serif fonts tend to have a font name or family name containing "serif",
    "times", "garamond", "palatino", "georgia" etc.  This is a simple
    name-based heuristic; point-level analysis would require much more code.
    """
    serif_keywords = {
        "serif", "times", "garamond", "palatino", "georgia", "roman",
        "caslon", "baskerville", "didot", "bodoni", "minion",
    }
    sans_keywords = {
        "sans", "gothic", "grotesque", "grotesk", "futura", "helvetica",
        "arial", "verdana", "trebuchet",
    }
    name = (font.family_name + " " + font.font_name).lower()
    if any(k in name for k in serif_keywords):
        return True
    if any(k in name for k in sans_keywords):
        return False
    # Default: assume sans-serif
    return False


def _weight_class_from_stroke(stroke_width: float, em_size: int) -> int:
    """Map a stroke width to the nearest CSS weight class (100–900)."""
    if em_size <= 0:
        return 400
    ratio = stroke_width / em_size
    # Approximate boundaries
    thresholds = [
        (0.04, 100),   # Thin
        (0.055, 200),  # ExtraLight
        (0.07, 300),   # Light
        (0.09, 400),   # Regular
        (0.11, 500),   # Medium
        (0.13, 600),   # SemiBold
        (0.16, 700),   # Bold
        (0.20, 800),   # ExtraBold
    ]
    for threshold, weight in thresholds:
        if ratio < threshold:
            return weight
    return 900  # Black


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_style(font: Font) -> StyleProfile:
    """Analyse the visual style of *font* and return a :class:`StyleProfile`.

    The analysis uses heuristics based on glyph bounding boxes and font
    metadata.  It does not perform point-level Bézier analysis.

    Parameters
    ----------
    font:
        The :class:`~aifont.core.font.Font` to analyse.

    Returns
    -------
    StyleProfile
        A dataclass containing the extracted stylistic metrics.

    Examples
    --------
    >>> from aifont.core.font import Font
    >>> from aifont.core.analyzer import analyze_style
    >>> profile = analyze_style(Font.open("Helvetica.otf"))
    >>> print(profile.summary())
    """
    notes: List[str] = []

    em = font.em_size
    italic_angle = font.italic_angle
    ascender = float(font.ascent)
    descender = float(font.descent)

    stroke_width = _estimate_stroke_width(font)
    x_height = _estimate_x_height(font)
    cap_height = _estimate_cap_height(font)
    stroke_contrast = _estimate_stroke_contrast(font, stroke_width)
    has_serifs = _detect_serifs(font)
    weight_class = _weight_class_from_stroke(stroke_width, em)

    # Count glyphs
    glyph_count = 0
    try:
        for _ in font.raw:
            glyph_count += 1
    except Exception:
        pass

    if italic_angle != 0.0:
        notes.append(f"Font is italic (angle={italic_angle:.1f}°)")
    if has_serifs:
        notes.append("Serif font detected (name heuristic)")
    else:
        notes.append("Sans-serif font detected (name heuristic)")

    return StyleProfile(
        stroke_width=stroke_width,
        stroke_contrast=stroke_contrast,
        italic_angle=italic_angle,
        x_height=x_height,
        cap_height=cap_height,
        ascender=ascender,
        descender=descender,
        em_size=em,
        has_serifs=has_serifs,
        weight_class=weight_class,
        glyph_count=glyph_count,
        notes=notes,
    )
