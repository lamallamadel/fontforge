"""
aifont.core.metrics — Kerning and spacing utilities.

This module provides functions to read and write kern pairs, to set
individual kern values through FontForge's lookup system, and to
apply automatic sidebearing/spacing optimisation.

FontForge is used as a black-box dependency via ``import fontforge``.
No FontForge source code is modified.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .font import Font


# ---------------------------------------------------------------------------
# Public type aliases
# ---------------------------------------------------------------------------

KernPair = Tuple[str, str, int]
"""A 3-tuple ``(left_glyph_name, right_glyph_name, kern_value)``."""


# ---------------------------------------------------------------------------
# Kern pair read / write
# ---------------------------------------------------------------------------


def get_kern_pairs(font: "Font") -> List[KernPair]:
    """Return all kern pairs defined in *font*.

    Iterates over every lookup / subtable in the font and collects
    explicit glyph-to-glyph kern pairs.

    Parameters
    ----------
    font : Font
        An :class:`~aifont.core.font.Font` instance.

    Returns
    -------
    list of (str, str, int)
        Each element is ``(left_name, right_name, kern_value)``.

    Examples
    --------
    ::

        from aifont.core.font import Font
        from aifont.core.metrics import get_kern_pairs

        font = Font.open("MyFont.otf")
        for left, right, value in get_kern_pairs(font):
            print(f"{left} + {right} = {value}")
    """
    ff = font.ff_font
    pairs: List[KernPair] = []

    try:
        for glyph_name in ff:
            glyph = ff[glyph_name]
            # fontforge exposes kern pairs via glyph.kerns
            for pair_info in _iter_kerns(glyph):
                pairs.append((glyph_name, pair_info[0], pair_info[1]))
    except Exception:  # noqa: BLE001
        pass

    return pairs


def set_kern(
    font: "Font",
    left: str,
    right: str,
    value: int,
    lookup_name: Optional[str] = None,
) -> None:
    """Set (or create) a kern pair in *font*.

    If no *lookup_name* is given, the function looks for the first
    existing GPOS kerning lookup in the font; if none exists it creates
    a new one called ``"aifont-kern"``.

    Parameters
    ----------
    font : Font
        Target font.
    left : str
        Name of the left glyph.
    right : str
        Name of the right glyph.
    value : int
        Kern value in font units (negative = tighter, positive = looser).
    lookup_name : str, optional
        Name of an existing kern lookup.  When *None*, the function
        finds or creates a suitable lookup automatically.

    Raises
    ------
    KeyError
        If *left* or *right* glyph does not exist in the font.
    """
    ff = font.ff_font

    if left not in ff:
        raise KeyError(f"Glyph not found in font: {left!r}")
    if right not in ff:
        raise KeyError(f"Glyph not found in font: {right!r}")

    subtable = _ensure_kern_subtable(ff, lookup_name)
    ff[left].addPosSub(subtable, right, 0, 0, value, 0, 0, 0, 0, 0)


def remove_kern(font: "Font", left: str, right: str) -> bool:
    """Remove a kern pair from *font* if it exists.

    Parameters
    ----------
    font : Font
        Target font.
    left : str
        Name of the left glyph.
    right : str
        Name of the right glyph.

    Returns
    -------
    bool
        ``True`` if the pair was found and removed, ``False`` otherwise.
    """
    ff = font.ff_font
    try:
        ff[left].removePosSub("*", right)  # type: ignore[arg-type]
        return True
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Automatic spacing
# ---------------------------------------------------------------------------


def auto_space(
    font: "Font",
    target_ratio: float = 0.15,
    glyph_names: Optional[List[str]] = None,
) -> None:
    """Apply automatic sidebearing optimisation to *font*.

    Uses FontForge's built-in ``autoWidth`` / ``autoKern`` routines and
    then adjusts sidebearings to achieve a target ratio of
    ``sidebearing / cap_height``.

    Parameters
    ----------
    font : Font
        Target font.
    target_ratio : float, optional
        Target ratio of left/right sidebearing to the font's cap-height.
        Defaults to ``0.15`` (15 %).
    glyph_names : list of str, optional
        Restrict spacing to these glyphs.  When *None*, all glyphs are
        processed.
    """
    ff = font.ff_font
    cap_height = _estimate_cap_height(ff)
    target_sb = max(1, int(cap_height * target_ratio))

    names = glyph_names if glyph_names is not None else list(ff)

    for name in names:
        try:
            g = ff[name]
            # Skip non-spacing glyphs (marks, spaces, etc.)
            if g.width == 0:
                continue
            bb = g.boundingBox()
            if bb[0] == bb[2]:  # empty outline
                continue
            g.left_side_bearing = target_sb
            g.right_side_bearing = target_sb
        except Exception:  # noqa: BLE001
            pass


def auto_kern(
    font: "Font",
    separation: int = 0,
    min_kern: int = -200,
    only_closer: bool = True,
    touch: bool = False,
) -> None:
    """Invoke FontForge's automatic kerning algorithm.

    Parameters
    ----------
    font : Font
        Target font.
    separation : int, optional
        Desired optical separation between glyph pairs in font units.
    min_kern : int, optional
        Minimum allowed kern value (absolute).  Default ``-200``.
    only_closer : bool, optional
        When ``True`` (default), only generate negative kern values.
    touch : bool, optional
        When ``True``, kern glyphs so that they *touch* (overlap by 0).
    """
    ff = font.ff_font
    subtable = _ensure_kern_subtable(ff)
    try:
        ff.autoKern(subtable, separation, min_kern, only_closer, touch)
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Helpers (private)
# ---------------------------------------------------------------------------


def _iter_kerns(ff_glyph: object) -> List[Tuple[str, int]]:
    """Yield (right_glyph_name, value) tuples from a FontForge glyph."""
    result: List[Tuple[str, int]] = []
    try:
        pos_subs = ff_glyph.getPosSub("*")  # type: ignore[attr-defined]
        for entry in pos_subs:
            # Kern pair entries have tag 'Pair'
            if entry[1] == "Pair":
                result.append((entry[2], int(entry[5])))  # x_adv_kern
    except Exception:  # noqa: BLE001
        pass
    return result


def _ensure_kern_subtable(
    ff_font: object,
    lookup_name: Optional[str] = None,
) -> str:
    """Find or create a GPOS kerning lookup and return its first subtable name."""
    import fontforge  # noqa: PLC0415

    existing_lookups = ff_font.getLookupInfo  # type: ignore[attr-defined]

    # Try to find an existing pair-positioning (kern) lookup
    if lookup_name:
        try:
            subtables = ff_font.getLookupSubtables(lookup_name)  # type: ignore[attr-defined]
            if subtables:
                return subtables[0]
        except Exception:  # noqa: BLE001
            pass

    # Scan all lookups for a kerning lookup
    try:
        for lk in ff_font.gpos_lookups:  # type: ignore[attr-defined]
            info = ff_font.getLookupInfo(lk)  # type: ignore[attr-defined]
            if info and info[0] == "gpos_pair":
                subtables = ff_font.getLookupSubtables(lk)  # type: ignore[attr-defined]
                if subtables:
                    return subtables[0]
    except Exception:  # noqa: BLE001
        pass

    # Create a new kern lookup + subtable
    new_lookup = lookup_name or "aifont-kern"
    new_subtable = new_lookup + "-subtable"
    try:
        ff_font.addLookup(  # type: ignore[attr-defined]
            new_lookup,
            "gpos_pair",
            ("kern",),
            (("kern", (("DFLT", ("dflt",)),)),),
        )
        ff_font.addLookupSubtable(new_lookup, new_subtable)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass

    return new_subtable


def _estimate_cap_height(ff_font: object) -> int:
    """Return the cap-height of the font (from 'H' glyph bounding box)."""
    try:
        h = ff_font["H"]  # type: ignore[index]
        bb = h.boundingBox()
        return int(bb[3])  # ymax of 'H'
    except Exception:  # noqa: BLE001
        return int(ff_font.em * 0.7)  # type: ignore[attr-defined]
