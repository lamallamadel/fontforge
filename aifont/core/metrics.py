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
