"""Kerning and spacing utilities."""
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
    from aifont.core.font import Font


def get_kern_pairs(font: "Font") -> Dict[Tuple[str, str], int]:
    """Return all kerning pairs in *font* as ``{(left, right): value}``."""
    pairs: Dict[Tuple[str, str], int] = {}
    ff = font._ff
    if not hasattr(ff, "subtables"):
        return pairs
    try:
        for name in ff:  # type: ignore[union-attr]
            glyph = ff[name]  # type: ignore[index]
            if hasattr(glyph, "getPosSub"):
                for sub in glyph.getPosSub("*"):
                    # sub[0] = subtable name, sub[1] = type, rest varies
                    if len(sub) >= 4 and sub[1] == "Pair":
                        pairs[(name, sub[2])] = sub[3]
    except (TypeError, AttributeError):
        pass
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
"""Kerning and spacing utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple
"""
aifont.core.metrics — kerning and spacing utilities.

This module provides the :class:`Metrics` class, which wraps a FontForge
font object and exposes a clean Pythonic API for managing typographic
metrics: kerning pairs, side bearings, line metrics, and automated
spacing/kerning.

Usage::

    from aifont.core.metrics import Metrics

    # Wrap any fontforge font object (or an aifont Font wrapper)
    metrics = Metrics(font_or_ff_font)

    # Kerning
    metrics.set_kern("A", "V", -80)
    value = metrics.get_kern("A", "V")   # → -80
    metrics.auto_kern()

    # Spacing
    metrics.auto_space()
    metrics.set_sidebearings("A", left=50, right=50)

    # Line metrics
    metrics.ascent = 800
    metrics.descent = 200
    metrics.line_gap = 0

    # Full report
    report = metrics.report()

Architecture constraint
-----------------------
FontForge is the underlying engine — DO NOT modify any FontForge source code.
All operations delegate to ``fontforge``'s Python bindings.
"""Kerning and spacing utilities for AIFont fonts."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font


def get_kern_pairs(font: "Font") -> List[Tuple[str, str, int]]:
    """Return all kern pairs defined in the font.

    Args:
        font: The :class:`~aifont.core.font.Font` to inspect.

    Returns:
        A list of ``(left_glyph, right_glyph, kern_value)`` tuples.
    """
    pairs: List[Tuple[str, str, int]] = []
    if font._ff is None:
        return pairs
    for glyph in font._ff.glyphs():
        for subtable, kern in glyph.getPosSub("*"):
            # Only process kern lookups
            if "kern" in subtable.lower():
                pairs.append((glyph.glyphname, subtable, kern))
    return pairs


def set_kern(font: "Font", left: str, right: str, value: int) -> None:
    """Set a kern pair value.

    Args:
        font:  The font to modify.
        left:  Name of the left glyph.
        right: Name of the right glyph.
        value: Kern value in font units (negative = tighter).
    """
    if font._ff is None:
        return
    # Ensure a kern lookup/subtable exists
    lookup = "kern-pairs"
    subtable = "kern-pairs-1"
    lookup_exists = False
    if hasattr(font._ff, "getLookupInfo"):
        try:
            font._ff.getLookupInfo(lookup)
            lookup_exists = True
        except Exception:
            lookup_exists = False
    if not lookup_exists:
        font._ff.addLookup(lookup, "gpos_pair", (), [["kern", [["latn", ["dflt"]]]]])
        font._ff.addLookupSubtable(lookup, subtable)
    font._ff[left].addPosSub(subtable, right, 0, 0, value, 0, 0, 0, 0, 0)


def auto_space(font: "Font", target_ratio: float = 0.15) -> None:
    """Apply automatic sidebearing spacing to all glyphs.

    Args:
        font:         The font to space.
        target_ratio: Target ratio of sidebearing to em-size (default 0.15).
    """
    if font._ff is None:
        return
    em = font._ff.em
    target = int(em * target_ratio)
    for glyph in font._ff.glyphs():
        if glyph.width > 0:
            glyph.left_side_bearing = target
            glyph.right_side_bearing = target
KernPair = tuple[str, str, int]


def get_kern_pairs(font: Font) -> list[KernPair]:
    """Return all kern pairs defined in *font* as ``(left, right, value)`` triples.

    Iterates over all GPOS kern lookups via fontforge's lookup API.
    """
    pairs: list[KernPair] = []
    ff = font._raw
    for lookup in ff.gpos_lookups:
        linfo = ff.getLookupInfo(lookup)
        if linfo[0] != "kern":
            continue
        for subtable in ff.getLookupSubtables(lookup):
            for glyph_name in ff:
                glyph = ff[glyph_name]
                kerns: dict = {}
                try:
                    kerns = dict(glyph.getPosSub(subtable) or {})
                except Exception:  # noqa: BLE001
                    continue
                for right, value in kerns.items():
                    pairs.append((glyph_name, right, value))
    return pairs


def set_kern(font: Font, left: str, right: str, value: int) -> None:
    """Set a kern pair *value* for (*left*, *right*) in *font*.

    Creates a dedicated kern lookup/subtable if none exists.
    """
    ff = font._raw
    lookup_name = "aifont-kern"
    subtable_name = "aifont-kern-1"

    if lookup_name not in (ff.gsub_lookups + ff.gpos_lookups):
        ff.addLookup(lookup_name, "gpos_pair", 0, [["kern", [["latn", ["dflt"]]]]])
        ff.addLookupSubtable(lookup_name, subtable_name)

    ff[left].addPosSub(subtable_name, right, 0, 0, value, 0, 0, 0, 0, 0)


def auto_space(font: Font, target_ratio: float = 0.15) -> None:
    """Apply automatic sidebearing spacing to all glyphs in *font*.

    Uses fontforge's built-in :meth:`~fontforge.glyph.autoWidth` to set
    sidebearings so that the whitespace-to-em ratio approximates
    *target_ratio*.

    Args:
        font: The :class:`~aifont.core.font.Font` to space.
        target_ratio: Target ratio of sidebearing to em size (0–1).
    """
    ff = font._raw
    em = ff.em
    separation = int(em * target_ratio)
    ff.autoWidth(separation)
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
This module must NOT be called from outside the aifont package with
direct fontforge objects; use the higher-level Font/Glyph wrappers when
they are available.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Internal constants — lookup/subtable names used for kern pairs
# ---------------------------------------------------------------------------

_KERN_LOOKUP_NAME = "aifont-kern"
_KERN_SUBTABLE_NAME = "aifont-kern-pairs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unwrap(font_or_wrapper):
    """Return the raw fontforge font object from a wrapper or raw object.

    An *aifont* Font wrapper exposes its underlying fontforge font via the
    ``_ff_font`` attribute.  If the object is already a raw fontforge font
    (or any other object), it is returned unchanged.
    """
    if hasattr(font_or_wrapper, "_ff_font"):
        return font_or_wrapper._ff_font
    return font_or_wrapper


def _ensure_kern_lookup(ff_font) -> None:
    """Create the kern GPOS lookup and subtable if they do not exist yet.

    The lookup uses a flat pair-positioning (``gpos_pair``) approach with
    per-glyph kern pairs stored in a single subtable.  The lookup is
    registered for both the ``DFLT`` and ``latn`` scripts.
    """
    existing = getattr(ff_font, "lookups", None)
    if existing is not None and _KERN_LOOKUP_NAME in existing:
        return

    try:
        ff_font.addLookup(
            _KERN_LOOKUP_NAME,
            "gpos_pair",
            (),
            [
                ["kern", [["DFLT", ["dflt"]], ["latn", ["dflt"]]]],
            ],
        )
        ff_font.addLookupSubtable(_KERN_LOOKUP_NAME, _KERN_SUBTABLE_NAME)
    except Exception:
        # Lookup may already exist (race condition or pre-existing data).
        pass


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------


class Metrics:
    """Typographic metrics manager for a FontForge font.
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
    right: str
    value: int


@dataclass
class SideBearings:
    """Left and right side-bearing values for a glyph."""

    left: int
    right: int
    glyph_name: str
    lsb: int
    rsb: int


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


def get_kern_pairs(font: object) -> List[KernPair]:
    """Return all kern pairs defined in the font.

    The function inspects every GPOS kern lookup in the font and collects
    all individual glyph-pair values.

    Args:
        font: A :class:`~aifont.core.font.Font` wrapper **or** a raw
              ``fontforge.font`` object.

    Returns:
        A list of :class:`KernPair` instances.
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
        for glyph_name in ff:
            glyph = ff[glyph_name]
            # fontforge exposes kern pairs via glyph.kerns
            for pair_info in _iter_kerns(glyph):
                pairs.append((glyph_name, pair_info[0], pair_info[1]))
    except Exception:  # noqa: BLE001
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
    font: "Font",
    left: str,
    right: str,
    value: int,
    subtable: str = "aifont-kern",
) -> None:
    """Set a kern pair value between *left* and *right* glyphs.

    Creates a kern lookup and subtable named *subtable* if it does not
    already exist.
    """
    ff = font._ff
    # Ensure the lookup/subtable exists
    lookups = getattr(ff, "gpos_lookups", None)
    existing = list(lookups) if lookups is not None else []
    if subtable not in existing:
        try:
            ff.addLookup(  # type: ignore[union-attr]
                subtable,
                "gpos_pair",
                (),
                [["kern", [["DFLT", ["dflt"]], ["latn", ["dflt"]]]]],
            )
            ff.addLookupSubtable(subtable, subtable + "-1")  # type: ignore[union-attr]
        except (AttributeError, Exception):
            pass
    # Set the kern value on the left glyph
    try:
        glyph = ff[left]  # type: ignore[index]
        glyph.addPosSub(subtable + "-1", right, value, 0, 0, 0, 0, 0)  # type: ignore[union-attr]
    except (KeyError, AttributeError, Exception):
        pass


def auto_space(font: "Font", target_ratio: float = 0.15) -> None:
    """Adjust sidebearings so that the side-bearing/width ratio is roughly
    *target_ratio* for each glyph.

    This is a simple heuristic; for production use prefer
    ``fontforge.font.autoWidth()``.
    """
    ff = font._ff
    if hasattr(ff, "autoWidth"):
        try:
            ff.autoWidth(0, 0)  # type: ignore[union-attr]
            return
        except (AttributeError, Exception):
            pass
    # Fallback: iterate and set bearings manually
    try:
        for name in ff:  # type: ignore[union-attr]
            glyph = ff[name]  # type: ignore[index]
            w = getattr(glyph, "width", 0)
            if w > 0:
                bearing = int(w * target_ratio)
                glyph.left_side_bearing = bearing
                glyph.right_side_bearing = bearing
    except (TypeError, AttributeError):
        pass
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
        A fontforge font object **or** an *aifont* ``Font`` wrapper.
        The class stores only a reference — it never owns the font.

    Examples
    --------
    >>> metrics = Metrics(ff_font)
    >>> metrics.set_kern("A", "V", -80)
    >>> metrics.get_kern("A", "V")
    -80
    >>> metrics.ascent = 800
    >>> metrics.descent = 200
    >>> report = metrics.report()
    """

    def __init__(self, font) -> None:
        self._font = _unwrap(font)

    # ------------------------------------------------------------------
    # Kern pair management
    # ------------------------------------------------------------------

    def set_kern(self, left: str, right: str, value: int) -> None:
        """Set a kern pair value between *left* and *right* glyph names.

        A positive *value* moves the glyphs apart; a negative value
        brings them closer together (standard kerning convention).

        Parameters
        ----------
        left:
            Name of the left glyph in the pair (e.g. ``"A"``).
        right:
            Name of the right glyph in the pair (e.g. ``"V"``).
        value:
            Kern adjustment in font units.

        Raises
        ------
        KeyError
            If either glyph does not exist in the font.
        """
        ff = self._font
        if left not in ff or right not in ff:
            missing = left if left not in ff else right
            raise KeyError(f"Glyph '{missing}' not found in font")

        _ensure_kern_lookup(ff)
        left_glyph = ff[left]
        # Remove any existing pair first to avoid duplicates.
        self._remove_kern_entry(left_glyph, right)
        # GPOS pair: adjust first glyph's advance by *value*.
        left_glyph.addPosSub(
            _KERN_SUBTABLE_NAME,
            right,
            0, 0, value, 0,   # dx1, dy1, dwidth1, dheight1
            0, 0, 0, 0,       # dx2, dy2, dwidth2, dheight2
        )

    def get_kern(self, left: str, right: str) -> Optional[int]:
        """Return the kern value for the pair (*left*, *right*), or ``None``.

        Parameters
        ----------
        left:
            Name of the left glyph.
        right:
            Name of the right glyph.

        Returns
        -------
        int or None
            Kern value in font units, or ``None`` if no pair is defined.
        """
        ff = self._font
        if left not in ff:
            return None
        left_glyph = ff[left]
        try:
            pos_subs = left_glyph.getPosSub(_KERN_SUBTABLE_NAME)
        except Exception:
            return None
        for entry in pos_subs:
            # entry format: (subtable_name, glyph_name, dx1, dy1, dwidth1, dheight1, ...)
            if len(entry) >= 3 and entry[1] == right:
                # dwidth1 is the kern value (index 4 in the tuple)
                if len(entry) >= 5:
                    return int(entry[4])
        return None

    def kern_pairs(self) -> Dict[Tuple[str, str], int]:
        """Return all kern pairs as a mapping ``{(left, right): value}``.

        Only pairs stored in the *aifont* kern subtable are returned.
        """
        ff = self._font
        result: Dict[Tuple[str, str], int] = {}
        for glyph_name in ff:
            glyph = ff[glyph_name]
            try:
                pos_subs = glyph.getPosSub(_KERN_SUBTABLE_NAME)
            except Exception:
                continue
            for entry in pos_subs:
                if len(entry) >= 5:
                    right_name = entry[1]
                    kern_val = int(entry[4])
                    result[(glyph_name, right_name)] = kern_val
        return result

    # ------------------------------------------------------------------
    # Auto operations
    # ------------------------------------------------------------------

    def auto_kern(
        self,
        separation: int = 0,
        min_kern: int = -200,
        touching: bool = False,
    ) -> None:
        """Run FontForge's built-in auto-kerning algorithm.

        This creates or refreshes kern pairs in the *aifont* kern subtable
        using FontForge's optical spacing engine.

        Parameters
        ----------
        separation:
            Target spacing between glyph bounding boxes in font units.
            ``0`` means touching (optical kern only).
        min_kern:
            Minimum kern value to retain (pairs with smaller absolute
            values are discarded).
        touching:
            If ``True``, kern glyphs until they are optically touching.
        """
        ff = self._font
        _ensure_kern_lookup(ff)
        try:
            ff.autoKern(
                _KERN_SUBTABLE_NAME,
                separation,
                (),  # left glyphs — empty means all
                (),  # right glyphs — empty means all
                min_kern,
                touching,
            )
        except (AttributeError, TypeError):
            # Older fontforge builds use a shorter signature.
            try:
                ff.autoKern(_KERN_SUBTABLE_NAME, separation)
            except Exception:
                pass

    def auto_space(
        self,
        separation: int = 50,
        min_side: int = 0,
        max_side: int = 0,
    ) -> None:
        """Apply automatic side-bearing calculation to all glyphs.

        Uses FontForge's ``autoWidth`` engine to set left and right
        bearings so that the *optical* inter-glyph space equals
        *separation* font units.

        Parameters
        ----------
        separation:
            Target optical spacing between adjacent glyphs.
        min_side:
            Minimum allowed side-bearing value (``0`` = no minimum).
        max_side:
            Maximum allowed side-bearing value (``0`` = no maximum).
        """
        ff = self._font
        try:
            ff.autoWidth(separation, min_side, max_side)
        except (AttributeError, TypeError):
            # Per-glyph fallback for older FontForge builds.
            for glyph_name in ff:
                try:
                    ff[glyph_name].autoWidth(separation, min_side, max_side)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Side bearings
    # ------------------------------------------------------------------

    def set_sidebearings(
        self,
        glyph_name: str,
        *,
        left: Optional[int] = None,
        right: Optional[int] = None,
    ) -> None:
        """Set left and/or right side bearings for a glyph.

        Parameters
        ----------
        glyph_name:
            Name of the glyph to modify.
        left:
            New left side-bearing in font units.  ``None`` leaves it
            unchanged.
        right:
            New right side-bearing in font units.  ``None`` leaves it
            unchanged.

        Raises
        ------
        KeyError
            If the glyph does not exist in the font.
        """
        ff = self._font
        if glyph_name not in ff:
            raise KeyError(f"Glyph '{glyph_name}' not found in font")
        glyph = ff[glyph_name]
        if left is not None:
            glyph.left_side_bearing = int(left)
        if right is not None:
            glyph.right_side_bearing = int(right)

    def get_sidebearings(self, glyph_name: str) -> Tuple[int, int]:
        """Return the ``(left, right)`` side bearings of a glyph.

        Parameters
        ----------
        glyph_name:
            Name of the glyph.

        Returns
        -------
        tuple[int, int]
            ``(left_side_bearing, right_side_bearing)`` in font units.

        Raises
        ------
        KeyError
            If the glyph does not exist in the font.
        """
        ff = self._font
        if glyph_name not in ff:
            raise KeyError(f"Glyph '{glyph_name}' not found in font")
        glyph = ff[glyph_name]
        return (int(glyph.left_side_bearing), int(glyph.right_side_bearing))

    # ------------------------------------------------------------------
    # Line metrics (properties)
    # ------------------------------------------------------------------

    @property
    def ascent(self) -> int:
        """EM ascent in font units."""
        return int(self._font.ascent)

    @ascent.setter
    def ascent(self, value: int) -> None:
        self._font.ascent = int(value)

    @property
    def descent(self) -> int:
        """EM descent in font units (positive value)."""
        return int(self._font.descent)

    @descent.setter
    def descent(self, value: int) -> None:
        self._font.descent = int(value)

    @property
    def line_gap(self) -> int:
        """OS/2 typographic line gap in font units."""
        ff = self._font
        # Prefer the OS/2 typographic line gap; fall back gracefully.
        for attr in ("os2_typolinegap", "os2_linegap"):
            if hasattr(ff, attr):
                return int(getattr(ff, attr))
        return 0

    @line_gap.setter
    def line_gap(self, value: int) -> None:
        ff = self._font
        for attr in ("os2_typolinegap", "os2_linegap"):
            if hasattr(ff, attr):
                setattr(ff, attr, int(value))
                return

    # ------------------------------------------------------------------
    # Analysis / report
    # ------------------------------------------------------------------

    def report(self) -> dict:
        """Return a dictionary summarising all font metrics.

        The returned dict has the following top-level keys:

        ``line_metrics``
            A sub-dict with ``ascent``, ``descent``, ``units_per_em``, and
            ``line_gap``.

        ``kern_pairs``
            A list of ``{"left": str, "right": str, "value": int}`` dicts
            for every kern pair stored in the *aifont* kern subtable.

        ``glyph_sidebearings``
            A dict mapping glyph name → ``{"left": int, "right": int}``
            with the side-bearing values for every glyph in the font.

        Returns
        -------
        dict
            Structured metrics report.
        """
        ff = self._font

        # Line metrics
        line_metrics = {
            "ascent": self.ascent,
            "descent": self.descent,
            "units_per_em": self.ascent + self.descent,
            "line_gap": self.line_gap,
        }

        # Kern pairs
        kern_list = [
            {"left": left, "right": right, "value": value}
            for (left, right), value in self.kern_pairs().items()
        ]

        # Side bearings per glyph
        glyph_bearings: Dict[str, dict] = {}
        for glyph_name in ff:
            try:
                lsb, rsb = self.get_sidebearings(glyph_name)
                glyph_bearings[glyph_name] = {"left": lsb, "right": rsb}
            except Exception:
                pass

        return {
            "line_metrics": line_metrics,
            "kern_pairs": kern_list,
            "glyph_sidebearings": glyph_bearings,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _remove_kern_entry(self, left_glyph, right_name: str) -> None:
        """Remove an existing kern entry for *right_name* from *left_glyph*."""
        try:
            pos_subs = left_glyph.getPosSub(_KERN_SUBTABLE_NAME)
        except Exception:
            return
        for entry in pos_subs:
            if len(entry) >= 2 and entry[1] == right_name:
                try:
                    left_glyph.removePosSub(_KERN_SUBTABLE_NAME, right_name)
                except Exception:
                    pass
                return
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
