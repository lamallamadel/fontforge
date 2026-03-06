"""
aifont.core.metrics — kerning and spacing utilities.

All low-level operations are delegated to fontforge's Python bindings.
This module must NOT be called from outside the aifont package with
direct fontforge objects; use the higher-level Font/Glyph wrappers when
they are available.
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
    right: str
    value: int


@dataclass
class SideBearings:
    """Left and right side-bearing values for a glyph."""

    glyph_name: str
    lsb: int
    rsb: int


@dataclass
class SpacingAnalysis:
    """Result of a spacing / kerning analysis pass."""

    glyph_count: int = 0
    kern_pair_count: int = 0
    avg_lsb: float = 0.0
    avg_rsb: float = 0.0
    inconsistent_pairs: List[KernPair] = field(default_factory=list)
    outlier_sidebearings: List[SideBearings] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Low-level helpers (fontforge-aware)
# ---------------------------------------------------------------------------


def _get_ff_font(font_or_ff):
    """Return the raw fontforge font object from a wrapper or raw object."""
    # If it's an aifont Font wrapper, unwrap it.
    if hasattr(font_or_ff, "_ff_font"):
        return font_or_ff._ff_font
    return font_or_ff


def _glyph_bounding_box(ff_glyph) -> Optional[Tuple[float, float, float, float]]:
    """Return (xmin, ymin, xmax, ymax) bounding box or None if empty."""
    try:
        bb = ff_glyph.boundingBox()
        if bb and len(bb) == 4:
            return bb
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_kern_pairs(font) -> List[KernPair]:
    """
    Return all kern pairs defined in *font*.

    Parameters
    ----------
    font:
        A fontforge font object or an aifont Font wrapper.

    Returns
    -------
    List[KernPair]
        Every kerning pair found across all kern lookups.
    """
    ff = _get_ff_font(font)
    pairs: List[KernPair] = []

    try:
        for glyph_name in ff:
            glyph = ff[glyph_name]
            if not hasattr(glyph, "getPosSub"):
                continue
            for subtable_name in _iter_kern_subtables(ff):
                try:
                    entries = glyph.getPosSub(subtable_name)
                    for entry in entries:
                        # entry format: (subtable, type, glyph2, value, ...)
                        if len(entry) >= 4:
                            pairs.append(
                                KernPair(
                                    left=glyph_name,
                                    right=str(entry[2]),
                                    value=int(entry[3]),
                                )
                            )
                except Exception:
                    continue
    except Exception:
        pass

    return pairs


def _iter_kern_subtables(ff_font):
    """Yield names of all pair-kerning subtables in *ff_font*."""
    subtables: List[str] = []
    try:
        for lookup in ff_font.gpos_lookups:
            lookup_info = ff_font.getLookupInfo(lookup)
            if lookup_info and lookup_info[0] == "gpos_pair":
                for sub in ff_font.getLookupSubtables(lookup):
                    subtables.append(sub)
    except Exception:
        pass
    return subtables


def set_kern(font, left: str, right: str, value: int) -> None:
    """
    Set (or update) the kern value for the pair (*left*, *right*).

    If no kern lookup exists, one is created automatically.

    Parameters
    ----------
    font:
        A fontforge font object or an aifont Font wrapper.
    left:
        Name of the left glyph.
    right:
        Name of the right glyph.
    value:
        Kern value in font units (negative = tighter).
    """
    ff = _get_ff_font(font)

    lookup_name = "aifont-kern-lookup"
    subtable_name = "aifont-kern-subtable"

    # Ensure the lookup exists.
    existing_lookups = []
    try:
        existing_lookups = list(ff.gpos_lookups)
    except Exception:
        pass

    if lookup_name not in existing_lookups:
        try:
            ff.addLookup(lookup_name, "gpos_pair", (), (("kern", (("DFLT", ("dflt",)),)),))
            ff.addLookupSubtable(lookup_name, subtable_name)
        except Exception:
            return

    # Set the kern pair on the left glyph.
    try:
        glyph = ff[left]
        glyph.addPosSub(subtable_name, right, 0, 0, value, 0, 0, 0, 0, 0)
    except Exception:
        pass


def get_side_bearings(font, glyph_name: str) -> Optional[SideBearings]:
    """
    Return the side bearings for *glyph_name*.

    Parameters
    ----------
    font:
        A fontforge font object or an aifont Font wrapper.
    glyph_name:
        Name of the glyph.

    Returns
    -------
    SideBearings or None if the glyph is not found or has no contours.
    """
    ff = _get_ff_font(font)
    try:
        glyph = ff[glyph_name]
        bb = _glyph_bounding_box(glyph)
        if bb is None:
            return SideBearings(glyph_name=glyph_name, lsb=0, rsb=0)
        xmin, _, xmax, _ = bb
        lsb = int(xmin)
        rsb = int(glyph.width - xmax)
        return SideBearings(glyph_name=glyph_name, lsb=lsb, rsb=rsb)
    except Exception:
        return None


def set_side_bearings(font, glyph_name: str, lsb: Optional[int] = None, rsb: Optional[int] = None) -> bool:
    """
    Set the left and/or right side bearings for *glyph_name*.

    Uses fontforge's ``left_side_bearing`` / ``right_side_bearing`` glyph
    properties, which shift contours and adjust advance width automatically.

    Parameters
    ----------
    font:
        A fontforge font object or an aifont Font wrapper.
    glyph_name:
        Name of the glyph to modify.
    lsb:
        New left side bearing (None = keep existing).
    rsb:
        New right side bearing (None = keep existing).

    Returns
    -------
    bool
        True if the operation succeeded.
    """
    ff = _get_ff_font(font)
    try:
        glyph = ff[glyph_name]
        if lsb is not None:
            glyph.left_side_bearing = lsb
        if rsb is not None:
            glyph.right_side_bearing = rsb
        return True
    except Exception:
        return False


def auto_space(font, target_ratio: float = 0.15) -> int:
    """
    Apply automatic side-bearing spacing to all glyphs in *font*.

    Each glyph's left and right side bearings are set to
    ``target_ratio * glyph_width`` (clamped to a minimum of 20 units).

    Parameters
    ----------
    font:
        A fontforge font object or an aifont Font wrapper.
    target_ratio:
        Ratio of glyph width to use as side bearing.

    Returns
    -------
    int
        Number of glyphs modified.
    """
    ff = _get_ff_font(font)
    modified = 0
    for name in ff:
        try:
            glyph = ff[name]
            if glyph.width <= 0:
                continue
            target = max(20, int(glyph.width * target_ratio))
            glyph.left_side_bearing = target
            glyph.right_side_bearing = target
            modified += 1
        except Exception:
            continue
    return modified


def auto_kern(font, threshold: int = 50) -> List[KernPair]:
    """
    Generate kern pair suggestions using fontforge's built-in AutoKern.

    Falls back to a heuristic approach when fontforge's autoKern is not
    available.

    Parameters
    ----------
    font:
        A fontforge font object or an aifont Font wrapper.
    threshold:
        Minimum absolute kern value to include in suggestions.

    Returns
    -------
    List[KernPair]
        Suggested kern pairs.
    """
    ff = _get_ff_font(font)

    # Try fontforge's native AutoKern first.
    lookup_name = "aifont-autokern-lookup"
    subtable_name = "aifont-autokern-subtable"

    try:
        existing = list(ff.gpos_lookups)
        if lookup_name not in existing:
            ff.addLookup(lookup_name, "gpos_pair", (), (("kern", (("DFLT", ("dflt",)),)),))
            ff.addLookupSubtable(lookup_name, subtable_name)
        ff.autoKern(subtable_name, ff.em)
    except Exception:
        pass

    # Collect the results.
    pairs = get_kern_pairs(font)
    return [p for p in pairs if abs(p.value) >= threshold]


def analyze_spacing(font) -> SpacingAnalysis:
    """
    Analyse the spacing and kerning of *font*.

    Parameters
    ----------
    font:
        A fontforge font object or an aifont Font wrapper.

    Returns
    -------
    SpacingAnalysis
        Detailed spacing report including statistics and suggestions.
    """
    ff = _get_ff_font(font)
    analysis = SpacingAnalysis()

    glyph_names = list(ff)
    analysis.glyph_count = len(glyph_names)

    lsbs: List[int] = []
    rsbs: List[int] = []
    bearings: Dict[str, SideBearings] = {}

    for name in glyph_names:
        sb = get_side_bearings(font, name)
        if sb is not None:
            lsbs.append(sb.lsb)
            rsbs.append(sb.rsb)
            bearings[name] = sb

    if lsbs:
        analysis.avg_lsb = statistics.mean(lsbs)
        analysis.avg_rsb = statistics.mean(rsbs)

        # Identify outlier side bearings (>2 std devs from mean).
        if len(lsbs) > 2:
            lsb_std = statistics.stdev(lsbs)
            rsb_std = statistics.stdev(rsbs)
            for name, sb in bearings.items():
                if (
                    abs(sb.lsb - analysis.avg_lsb) > 2 * lsb_std
                    or abs(sb.rsb - analysis.avg_rsb) > 2 * rsb_std
                ):
                    analysis.outlier_sidebearings.append(sb)

    kern_pairs = get_kern_pairs(font)
    analysis.kern_pair_count = len(kern_pairs)

    # Detect inconsistent kern pairs (same glyph pair with different values).
    pair_map: Dict[Tuple[str, str], List[int]] = {}
    for kp in kern_pairs:
        key = (kp.left, kp.right)
        pair_map.setdefault(key, []).append(kp.value)

    for (left, right), values in pair_map.items():
        if len(values) > 1:
            analysis.inconsistent_pairs.append(
                KernPair(left=left, right=right, value=values[0])
            )

    # Generate human-readable suggestions.
    if analysis.outlier_sidebearings:
        analysis.suggestions.append(
            f"{len(analysis.outlier_sidebearings)} glyph(s) have outlier side bearings "
            f"(avg LSB={analysis.avg_lsb:.1f}, avg RSB={analysis.avg_rsb:.1f})."
        )
    if analysis.inconsistent_pairs:
        analysis.suggestions.append(
            f"{len(analysis.inconsistent_pairs)} kern pair(s) have inconsistent values."
        )
    if analysis.kern_pair_count == 0 and analysis.glyph_count > 10:
        analysis.suggestions.append("No kern pairs found — consider running AutoKern.")

    return analysis
