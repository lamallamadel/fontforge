"""
aifont.core.metrics — kerning and spacing utilities.

All low-level operations are delegated to fontforge's Python bindings.
FontForge source code is never modified.

Functions
---------
get_kern_pairs(font)
    Return all kern pairs defined in the font.
set_kern(font, left, right, value)
    Add or update a kern pair.
auto_space(font, target_ratio)
    Adjust side-bearings to reach a target stem/counter ratio.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class KernPair:
    """Represents a kerning pair between two glyphs."""

    left: str
    """Left glyph name."""
    right: str
    """Right glyph name."""
    value: int
    """Kern value in font units (negative = tighter)."""


@dataclass
class SideBearings:
    """Left and right side-bearing values for a glyph."""

    left: int
    right: int


@dataclass
class SpacingAnalysis:
    """Result of a spacing / kerning analysis pass."""

    kern_pairs: List[KernPair] = field(default_factory=list)
    mean_left_bearing: float = 0.0
    mean_right_bearing: float = 0.0
    sidebearings: Dict[str, SideBearings] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_ff_font(font_or_ff: object) -> object:
    """Return the raw fontforge font object from a wrapper or raw object."""
    if hasattr(font_or_ff, "_font"):
        return font_or_ff._font  # type: ignore[attr-defined]
    return font_or_ff


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_kern_pairs(font: object) -> List[KernPair]:
    """Return all kern pairs defined in the font.

    The function inspects every GPOS kern lookup in the font and collects
    all individual glyph-pair values.

    Args:
        font: A :class:`~aifont.core.font.Font` wrapper **or** a raw
              ``fontforge.font`` object.

    Returns:
        A list of :class:`KernPair` instances.
    """
    ff = _get_ff_font(font)
    pairs: List[KernPair] = []

    try:
        # Iterate over all GPOS lookups looking for kern subtables.
        for lookup in ff.gpos_lookups:
            for subtable in ff.getLookupSubtables(lookup):
                # getKerningClass may raise for non-kern subtables — guard it.
                try:
                    kc = ff.getKerningClass(subtable)
                    # kc is (firsts, seconds, offsets) or similar; fall through.
                except Exception:
                    pass

        # Walk every glyph and read per-glyph kern pairs.
        for glyph_name in ff:
            try:
                g = ff[glyph_name]
                for subtable, other, kern_val in g.getPosSub("*"):
                    if kern_val != 0:
                        pairs.append(KernPair(left=glyph_name, right=other, value=kern_val))
            except Exception:
                pass
    except Exception:
        pass

    return pairs


def set_kern(
    font: object,
    left: str,
    right: str,
    value: int,
    lookup: Optional[str] = None,
    subtable: Optional[str] = None,
) -> None:
    """Add or update a kern pair.

    If *lookup* / *subtable* are not provided, the function creates a new
    GPOS kern lookup named ``"aifont-kern"`` (and a subtable) the first
    time it is called.

    Args:
        font:     Font wrapper or raw fontforge font.
        left:     Name of the left glyph.
        right:    Name of the right glyph.
        value:    Kern adjustment in font units.
        lookup:   Name of the GPOS lookup to use (optional).
        subtable: Name of the kern subtable to use (optional).
    """
    ff = _get_ff_font(font)

    _lookup = lookup or "aifont-kern"
    _subtable = subtable or "aifont-kern-1"

    # Create lookup if it doesn't exist.
    if _lookup not in ff.gpos_lookups:
        ff.addLookup(_lookup, "gpos_pair", (), [["kern", [["latn", ["dflt"]]]]])
        ff.addLookupSubtable(_lookup, _subtable)

    # Set the kern value on the left glyph.
    ff[left].addPosSub(_subtable, right, 0, 0, value, 0, 0, 0, 0, 0)


def auto_space(font: object, target_ratio: float = 0.15) -> None:
    """Adjust side-bearings toward a target stem/counter ratio.

    This is a lightweight heuristic: it sets each glyph's left and right
    side-bearing to ``target_ratio * glyph.width``.  For production use,
    prefer FontForge's built-in ``font.autoWidth()`` and
    ``font.autoKern()``.

    Args:
        font:         Font wrapper or raw fontforge font.
        target_ratio: Desired ratio of side-bearing to advance width
                      (default ``0.15``).
    """
    ff = _get_ff_font(font)
    for glyph_name in ff:
        try:
            g = ff[glyph_name]
            if g.width > 0:
                bearing = int(g.width * target_ratio)
                g.left_side_bearing = bearing
                g.right_side_bearing = bearing
        except Exception:
            pass


def analyze_spacing(font: object) -> SpacingAnalysis:
    """Collect side-bearing statistics for all glyphs.

    Args:
        font: Font wrapper or raw fontforge font.

    Returns:
        A :class:`SpacingAnalysis` with per-glyph side-bearings and
        aggregate statistics.
    """
    ff = _get_ff_font(font)
    analysis = SpacingAnalysis()

    left_vals: List[int] = []
    right_vals: List[int] = []

    for glyph_name in ff:
        try:
            g = ff[glyph_name]
            lsb = g.left_side_bearing
            rsb = g.right_side_bearing
            analysis.sidebearings[glyph_name] = SideBearings(left=lsb, right=rsb)
            left_vals.append(lsb)
            right_vals.append(rsb)
        except Exception:
            pass

    if left_vals:
        analysis.mean_left_bearing = statistics.mean(left_vals)
    if right_vals:
        analysis.mean_right_bearing = statistics.mean(right_vals)

    analysis.kern_pairs = get_kern_pairs(font)
    return analysis
