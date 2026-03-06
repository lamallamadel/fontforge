"""
aifont.core.font — High-level Font wrapper around FontForge.

This module provides the :class:`Font` class, which wraps
``fontforge.font`` objects and exposes a clean, Pythonic API for
opening, inspecting, modifying and saving font files.

FontForge is used as a black-box dependency via ``import fontforge``.
No FontForge source code is modified.
"""

from __future__ import annotations

import os
from typing import Dict, Iterable, Iterator, List, Optional

import fontforge

from .glyph import Glyph


class FontMetadata:
    """Structured container for font-level metadata.

    Attributes
    ----------
    family_name : str
        The font family name (e.g. ``"Roboto"``).
    full_name : str
        The full PostScript name (e.g. ``"Roboto Bold"``).
    weight : str
        The weight string (e.g. ``"Bold"``).
    version : str
        The version string stored in the font.
    copyright : str
        Copyright notice embedded in the font.
    em_size : int
        The units-per-em value.
    ascent : int
        The font ascent value.
    descent : int
        The font descent value (negative in fontforge convention).
    """

    def __init__(self, ff_font: "fontforge.font") -> None:
        self._ff = ff_font

    # ------------------------------------------------------------------
    # Properties backed by the fontforge font object
    # ------------------------------------------------------------------

    @property
    def family_name(self) -> str:
        return self._ff.familyname or ""

    @family_name.setter
    def family_name(self, value: str) -> None:
        self._ff.familyname = value

    @property
    def full_name(self) -> str:
        return self._ff.fullname or ""

    @full_name.setter
    def full_name(self, value: str) -> None:
        self._ff.fullname = value

    @property
    def weight(self) -> str:
        return self._ff.weight or ""

    @weight.setter
    def weight(self, value: str) -> None:
        self._ff.weight = value

    @property
    def version(self) -> str:
        return self._ff.version or ""

    @version.setter
    def version(self, value: str) -> None:
        self._ff.version = value

    @property
    def copyright(self) -> str:
        return self._ff.copyright or ""

    @copyright.setter
    def copyright(self, value: str) -> None:
        self._ff.copyright = value

    @property
    def em_size(self) -> int:
        return int(self._ff.em)

    @em_size.setter
    def em_size(self, value: int) -> None:
        self._ff.em = value

    @property
    def ascent(self) -> int:
        return int(self._ff.ascent)

    @ascent.setter
    def ascent(self, value: int) -> None:
        self._ff.ascent = value

    @property
    def descent(self) -> int:
        return int(self._ff.descent)

    @descent.setter
    def descent(self, value: int) -> None:
        self._ff.descent = value

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"FontMetadata(family={self.family_name!r}, weight={self.weight!r}, "
            f"em={self.em_size})"
        )


class Font:
    """High-level wrapper around a FontForge font object.

    This class wraps ``fontforge.font`` (obtained via
    ``fontforge.open()`` or ``fontforge.font()``) and provides a clean,
    Pythonic interface for font manipulation.

    Do **not** call the constructor directly; use the class methods
    :meth:`open` and :meth:`new` instead.

    Parameters
    ----------
    ff_font : fontforge.font
        The underlying FontForge font object.

    Examples
    --------
    Open an existing font::

        font = Font.open("MyFont.otf")
        for glyph in font.glyphs:
            print(glyph.name)
        font.save("out/MyFont.otf")

    Create a new font from scratch::

        font = Font.new()
        font.metadata.family_name = "MyFont"
        g = font.create_glyph(65, "A")
        font.save("MyFont.ufo", fmt="ufo")
    """

    def __init__(self, ff_font: "fontforge.font") -> None:
        self._ff = ff_font
        self._metadata = FontMetadata(ff_font)

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def open(cls, path: str) -> "Font":
        """Open an existing font file.

        Parameters
        ----------
        path : str
            Path to the font file (OTF, TTF, UFO, SFD, etc.).

        Returns
        -------
        Font
            A new :class:`Font` instance wrapping the loaded font.

        Raises
        ------
        OSError
            If *path* does not exist or cannot be read.
        """
        if not os.path.exists(path):
            raise OSError(f"Font file not found: {path!r}")
        return cls(fontforge.open(path))

    @classmethod
    def new(cls) -> "Font":
        """Create a new, empty font.

        Returns
        -------
        Font
            A new :class:`Font` instance wrapping a blank FontForge font.
        """
        return cls(fontforge.font())

    # ------------------------------------------------------------------
    # Glyph access
    # ------------------------------------------------------------------

    @property
    def glyphs(self) -> List[Glyph]:
        """Return all glyphs in the font's default layer.

        Returns
        -------
        list of Glyph
            Ordered list of :class:`~aifont.core.glyph.Glyph` wrappers.
        """
        result: List[Glyph] = []
        for name in self._ff:
            try:
                result.append(Glyph(self._ff[name]))
            except Exception:  # noqa: BLE001
                pass
        return result

    def __iter__(self) -> Iterator[Glyph]:
        """Iterate over all glyphs in the font."""
        return iter(self.glyphs)

    def __len__(self) -> int:
        """Return the number of glyphs in the font."""
        return sum(1 for _ in self._ff)

    def __contains__(self, item: object) -> bool:
        """Test membership by glyph name or Unicode code-point.

        Parameters
        ----------
        item : str or int
            Glyph name (str) or Unicode code-point (int).
        """
        try:
            _ = self._ff[item]  # type: ignore[index]
            return True
        except Exception:  # noqa: BLE001
            return False

    def __getitem__(self, key: "str | int") -> Glyph:
        """Return the glyph identified by *key*.

        Parameters
        ----------
        key : str or int
            Glyph name (str) or Unicode code-point (int).

        Raises
        ------
        KeyError
            If no glyph with the given name/code-point exists.
        """
        try:
            return Glyph(self._ff[key])
        except Exception as exc:
            raise KeyError(key) from exc

    def get_glyph(self, name_or_codepoint: "str | int") -> Optional[Glyph]:
        """Return a glyph by name or code-point, or *None* if absent.

        Parameters
        ----------
        name_or_codepoint : str or int
            Glyph name or Unicode code-point.

        Returns
        -------
        Glyph or None
        """
        try:
            return Glyph(self._ff[name_or_codepoint])
        except Exception:  # noqa: BLE001
            return None

    def create_glyph(
        self, unicode_point: int = -1, name: Optional[str] = None
    ) -> Glyph:
        """Create a new glyph in the font.

        Parameters
        ----------
        unicode_point : int, optional
            Unicode code-point for the glyph. Use ``-1`` to create an
            unnamed glyph without a code-point assignment.
        name : str, optional
            Glyph name. When *None* and *unicode_point* is valid the
            name is auto-assigned by FontForge.

        Returns
        -------
        Glyph
            The newly created :class:`~aifont.core.glyph.Glyph`.
        """
        if name is not None:
            ff_glyph = self._ff.createChar(unicode_point, name)
        else:
            ff_glyph = self._ff.createChar(unicode_point)
        return Glyph(ff_glyph)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def metadata(self) -> FontMetadata:
        """Font-level metadata (family name, weight, em size, …)."""
        return self._metadata

    # ------------------------------------------------------------------
    # Encoding & Unicode
    # ------------------------------------------------------------------

    def set_encoding(self, encoding: str = "UnicodeBMP") -> None:
        """Set the font encoding.

        Parameters
        ----------
        encoding : str
            Encoding name (e.g. ``"UnicodeBMP"``, ``"ISO8859-1"``).
            Defaults to ``"UnicodeBMP"``.
        """
        self._ff.encoding = encoding

    # ------------------------------------------------------------------
    # Save / generate
    # ------------------------------------------------------------------

    def save(self, path: str, fmt: Optional[str] = None) -> None:
        """Save the font to *path*.

        When *fmt* is not specified the format is inferred from the file
        extension.

        Parameters
        ----------
        path : str
            Destination file path.
        fmt : str, optional
            Explicit format override: ``"otf"``, ``"ttf"``, ``"woff2"``,
            ``"ufo"``, ``"sfd"``, etc.  When *None* the extension of
            *path* is used.

        Raises
        ------
        ValueError
            If the format cannot be determined from the extension and no
            *fmt* was given.
        """
        ext = fmt or os.path.splitext(path)[1].lstrip(".").lower()
        if not ext:
            raise ValueError(
                "Cannot determine format; provide fmt= or use a known extension."
            )

        # Map friendly names to fontforge generate flags
        _FMT_MAP: Dict[str, str] = {
            "otf": "opentype",
            "ttf": "ttf",
            "woff": "woff",
            "woff2": "woff2",
            "ufo": "ufo3",
            "ufo3": "ufo3",
            "sfd": "",  # native save
        }

        if ext == "sfd":
            self._ff.save(path)
        else:
            ff_fmt = _FMT_MAP.get(ext, ext)
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            self._ff.generate(path, ff_fmt)

    # ------------------------------------------------------------------
    # Low-level access
    # ------------------------------------------------------------------

    @property
    def ff_font(self) -> "fontforge.font":
        """The underlying ``fontforge.font`` object.

        Use this only when you need functionality not yet covered by
        the AIFont wrapper API.
        """
        return self._ff

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Font(family={self.metadata.family_name!r}, "
            f"glyphs={len(self)})"
        )
