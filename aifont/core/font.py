"""aifont.core.font — high-level Font wrapper around fontforge.open().

FontForge is the underlying engine.  DO NOT modify FontForge source code.
This module wraps the ``fontforge.font`` object with a clean Pythonic API.
"""
aifont.core.font — High-level Font wrapper around FontForge.

This module provides the :class:`Font` class, which wraps
``fontforge.font`` objects and exposes a clean, Pythonic API for
opening, inspecting, modifying and saving font files.

FontForge is used as a black-box dependency via ``import fontforge``.
No FontForge source code is modified.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

try:
    # Imported as `_fontforge` to avoid shadowing the public name and to make
    # clear that this is an internal dependency, not part of the aifont API.
    import fontforge as _fontforge
except ImportError:  # pragma: no cover
    _fontforge = None  # type: ignore[assignment]


class Font:
    """Pythonic wrapper around a :class:`fontforge.font` object.

    Use :meth:`Font.open` to load an existing font file, or :meth:`Font.new`
    to create a blank font.
    """

    def __init__(self, _ff_font: object) -> None:
        """Initialise from an existing fontforge font object.

        Args:
            _ff_font: A raw ``fontforge.font`` instance.
        """
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
aifont.core.font — high-level Font wrapper around ``fontforge.font``.

This module provides a clean Pythonic API for opening, inspecting, and
saving fonts.  All low-level operations are delegated to the underlying
``fontforge.font`` object.

Architecture constraint
-----------------------
DO NOT modify FontForge source code.  ``import fontforge`` is treated as
a black-box dependency.
"""High-level Font wrapper around fontforge.open()."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

try:
    import fontforge  # type: ignore
except ImportError:  # pragma: no cover — fontforge not installed in test env
    fontforge = None  # type: ignore

from aifont.core.glyph import Glyph


@dataclass
class FontMetadata:
    """Structured font metadata."""

    family_name: str = ""
    full_name: str = ""
    weight: str = ""
    version: str = ""
    copyright: str = ""
    description: str = ""


class Font:
    """High-level Pythonic wrapper around a FontForge font object.

    Example:
        >>> font = Font.open("MyFont.otf")
        >>> print(font.metadata.family_name)
        >>> font.save("output.otf")
    """

    def __init__(self, _ff_font=None) -> None:
        self._ff = _ff_font
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import fontforge as _ff

    from aifont.core.glyph import Glyph

    _FFFont = _ff.font


class Font:
    """Pythonic wrapper over a :class:`fontforge.font` object.

    All low-level operations are delegated to the underlying
    :class:`fontforge.font` instance — this class never bypasses it.

    Example::

        font = Font.open("path/to/font.otf")
        for glyph in font.glyphs:
            print(glyph.name)
        font.save("output.otf")
    """

    def __init__(self, _ff_font: _FFFont) -> None:
        self._font = _ff_font

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def open(cls, path: str | Path) -> Font:
        """Open an existing font file and return a :class:`Font` instance."""
        import fontforge  # noqa: PLC0415

        return cls(fontforge.open(str(path)))

    @classmethod
    def new(cls, family: str = "Untitled") -> Font:
        """Create a blank font."""
        import fontforge  # noqa: PLC0415

        ff_font = fontforge.font()
        ff_font.familyname = family
        return cls(ff_font)
"""
aifont.core.font — high-level Font wrapper around ``fontforge.open()``.

Responsibilities:
- Open and save font files.
- Iterate over glyphs.
- Read/write font-level metadata (name, family, weight, em size, etc.).

All heavy lifting is delegated to the underlying ``fontforge.font`` object.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Optional

try:
    import fontforge as _ff
except ImportError:  # pragma: no cover — fontforge may not be installed
    _ff = None  # type: ignore[assignment]


class Font:
    """High-level wrapper around a :class:`fontforge.font` object.

    Parameters
    ----------
    ff_font:
        A raw ``fontforge.font`` instance (returned by ``fontforge.open``
        or ``fontforge.font()``).

    Examples
    --------
    >>> font = Font.open("MyFont.otf")
    >>> for glyph in font.glyphs:
    ...     print(glyph.name)
    >>> font.save("/tmp/MyFont-modified.otf")
    """

    def __init__(self, ff_font: object) -> None:
        self._ff_font = ff_font

    # ------------------------------------------------------------------
    # Construction helpers
from typing import Generator, Optional

try:
    import fontforge  # type: ignore
except ImportError:  # pragma: no cover
    fontforge = None  # type: ignore  # Allow import in environments without FontForge


class Font:
    """Pythonic wrapper around a :class:`fontforge.font` object."""

    def __init__(self, _ff_font: object) -> None:
        """Initialise from an existing fontforge font object."""
        self._font = _ff_font

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
    def open(cls, path: str | Path) -> "Font":
        """Open an existing font file.

        Args:
            path: Path to the font file (.otf, .ttf, .sfd, …).

        Returns:
            A :class:`Font` wrapping the loaded fontforge font.

        Raises:
            RuntimeError: If the fontforge bindings are not available.
        """
        if _fontforge is None:
            raise RuntimeError("fontforge Python bindings are not available.")
        ff = _fontforge.open(str(path))
        return cls(ff)

    @classmethod
            path: Path to an OTF, TTF, or SFD font file.

        Returns:
            A new :class:`Font` instance.

        Raises:
            FileNotFoundError: If the file does not exist.
            RuntimeError: If FontForge cannot open the file.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Font file not found: {path}")
        if fontforge is None:
            raise RuntimeError("fontforge Python bindings are not installed.")
        """Open a font file and return a :class:`Font` instance.

        Parameters
        ----------
        path:
            Absolute or relative path to a font file (.otf, .ttf, .sfd, …).

        Raises
        ------
        RuntimeError
            If FontForge is not installed.
        FileNotFoundError
            If *path* does not exist.
        """
        if _ff is None:
            raise RuntimeError(
                "fontforge Python bindings are not installed. "
                "Install FontForge to use Font.open()."
            )
        resolved = Path(path).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Font file not found: {path!r}")
        return cls(_ff.open(str(resolved)))

    @classmethod
    def new(cls, family_name: str = "Untitled") -> "Font":
        """Create a new, empty :class:`Font`.

        Parameters
        ----------
        family_name:
            The font family name to assign to the new font.

        Raises
        ------
        RuntimeError
            If FontForge is not installed.
        """
        if _ff is None:
            raise RuntimeError(
                "fontforge Python bindings are not installed. "
                "Install FontForge to use Font.new()."
            )
        ff_font = _ff.font()
        ff_font.familyname = family_name
        ff_font.fontname = family_name.replace(" ", "-")
        return cls(ff_font)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def raw(self) -> object:
        """The underlying ``fontforge.font`` object."""
        return self._ff_font

    @property
    def family_name(self) -> str:
        """The font family name."""
        return str(getattr(self._ff_font, "familyname", ""))

    @family_name.setter
    def family_name(self, value: str) -> None:
        self._ff_font.familyname = value

    @property
    def font_name(self) -> str:
        """The PostScript font name."""
        return str(getattr(self._ff_font, "fontname", ""))

    @font_name.setter
    def font_name(self, value: str) -> None:
        self._ff_font.fontname = value

    @property
    def em_size(self) -> int:
        """Units per em (typically 1000 or 2048)."""
        return int(getattr(self._ff_font, "em", 1000))

    @property
    def italic_angle(self) -> float:
        """Italic angle in degrees (0 for upright fonts)."""
        return float(getattr(self._ff_font, "italicangle", 0.0))

    @italic_angle.setter
    def italic_angle(self, value: float) -> None:
        self._ff_font.italicangle = value

    @property
    def ascent(self) -> int:
        """Ascender value in font units."""
        return int(getattr(self._ff_font, "ascent", 800))

    @property
    def descent(self) -> int:
        """Descender value in font units (positive number)."""
        return int(getattr(self._ff_font, "descent", 200))

    @property
    def metadata(self) -> dict:
        """A dictionary of basic font metadata."""
        return {
            "family_name": self.family_name,
            "font_name": self.font_name,
            "em_size": self.em_size,
            "italic_angle": self.italic_angle,
            "ascent": self.ascent,
            "descent": self.descent,
        }

    # ------------------------------------------------------------------
    # Glyph iteration
    # ------------------------------------------------------------------

    @property
    def glyphs(self) -> Iterator["Glyph"]:
        """Iterate over all glyphs in the font.

        Yields
        ------
        Glyph
            Each glyph wrapped in :class:`~aifont.core.glyph.Glyph`.
        """
        from aifont.core.glyph import Glyph

        for name in self._ff_font:
            try:
                ff_glyph = self._ff_font[name]
                yield Glyph(ff_glyph)
            except (KeyError, TypeError):
                continue

    def get_glyph(self, name: str) -> Optional["Glyph"]:
        """Return the :class:`~aifont.core.glyph.Glyph` with the given name.

        Parameters
        ----------
        name:
            PostScript glyph name (e.g. ``"A"``).

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
            ``None`` if the glyph does not exist.
        """
        from aifont.core.glyph import Glyph

        try:
            return Glyph(self._ff_font[name])
        except (KeyError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str | Path, fmt: Optional[str] = None) -> None:
        """Save the font to *path*.

        Parameters
        ----------
        path:
            Output file path.  The extension determines the format unless
            *fmt* is given.
        fmt:
            Optional explicit format string passed to
            ``fontforge.font.generate`` (e.g. ``"otf"``).
        """
        out = str(Path(path))
        if fmt is not None:
            self._ff_font.generate(out, flags=(), layer="Fore")
        else:
            self._ff_font.save(out)

    def close(self) -> None:
        """Close the font and free fontforge resources."""
        try:
            self._ff_font.close()
        Args:
            path: Path to the font file (.sfd, .otf, .ttf, …).

        Returns:
            A new :class:`Font` wrapping the loaded font.

        Raises:
            RuntimeError: If FontForge cannot open the file.
        """
        if fontforge is None:
            raise RuntimeError("fontforge Python bindings are not available.")
        ff = fontforge.open(str(path))
        return cls(ff)

    @classmethod
    def new(cls, family_name: str = "Untitled") -> "Font":
        """Create a new empty font.

        Args:
            family_name: The family name for the new font.

        Returns:
            A new :class:`Font` instance.
        """
        if fontforge is None:
            raise RuntimeError("fontforge Python bindings are not installed.")
        ff = fontforge.font()
        ff.familyname = family_name
        ff.fontname = family_name.replace(" ", "")
        ff.fullname = family_name
        return cls(ff)

    # ------------------------------------------------------------------
    # Properties
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
        """Return structured font metadata."""
        if self._ff is None:
            return FontMetadata()
        return FontMetadata(
            family_name=getattr(self._ff, "familyname", ""),
            full_name=getattr(self._ff, "fullname", ""),
            weight=getattr(self._ff, "weight", ""),
            version=getattr(self._ff, "version", ""),
            copyright=getattr(self._ff, "copyright", ""),
            description=getattr(self._ff, "comment", ""),
        )

    @metadata.setter
    def metadata(self, meta: FontMetadata) -> None:
        """Update font metadata from a :class:`FontMetadata` object."""
        if self._ff is None:
            return
        self._ff.familyname = meta.family_name
        self._ff.fullname = meta.full_name
        self._ff.weight = meta.weight
        self._ff.version = meta.version
        self._ff.copyright = meta.copyright
        self._ff.comment = meta.description

    @property
    def glyphs(self) -> list[Glyph]:
        """Return all glyphs in the font."""
        if self._ff is None:
            return []
        return [Glyph(self._ff[name]) for name in self._ff]

    # ------------------------------------------------------------------
    # Save / export helpers
    # ------------------------------------------------------------------

    def save(self, path: str | Path, fmt: Optional[str] = None) -> None:
        """Save the font.

        Args:
            path: Destination path.
            fmt:  Optional format string (e.g. ``"otf"``, ``"ttf"``).
                  Inferred from *path* extension when omitted.
        """
        if self._ff is None:
            raise RuntimeError("No font loaded.")
        path = Path(path)
        if fmt is None:
            fmt = path.suffix.lstrip(".")
        fmt_map = {"otf": "opentype", "ttf": "truetype", "woff2": "woff2", "sfd": "sfd"}
        ff_fmt = fmt_map.get(fmt.lower(), fmt)
        if ff_fmt == "sfd":
            self._ff.save(str(path))
        else:
            self._ff.generate(str(path))

    def close(self) -> None:
        """Close the underlying FontForge font and release resources."""
        if self._ff is not None:
            self._ff.close()
            self._ff = None
    def new(cls) -> "Font":
        """Create a new, empty font.

        Returns:
            A :class:`Font` wrapping a blank fontforge font.

        Raises:
            RuntimeError: If the fontforge bindings are not available.
        """
        if _fontforge is None:
            raise RuntimeError("fontforge Python bindings are not available.")
        ff = _fontforge.font()
            A new :class:`Font` wrapping a blank fontforge font.
        """
        if fontforge is None:
            raise RuntimeError("fontforge Python bindings are not available.")
        ff = fontforge.font()
        return cls(ff)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str | Path, fmt: Optional[str] = None) -> None:
        """Save the font in FontForge's native SFD format or another format.

        Args:
            path: Destination file path.
            fmt:  Optional format string (e.g. ``"otf"``).  When *None* the
                  format is inferred from the file extension.
    def save(self, path: str | Path, fmt: str | None = None) -> None:
        """Save the font to *path*.

        Args:
            path: Destination file path.
            fmt:  Optional fontforge format string (e.g. ``"otf"``).
        """
        if fmt:
            self._font.generate(str(path))
    def save(self, path: str | Path, fmt: Optional[str] = None) -> None:
        """Save the font.

        Args:
            path: Destination file path.
            fmt:  Optional format string passed to ``fontforge.font.save``
                  (e.g. ``"otf"``).  When *None* the format is inferred from
                  the file extension.
        """
        if fmt is not None:
            self._font.save(str(path), fmt)
        else:
            self._font.save(str(path))

    def generate(self, path: str | Path, flags: tuple = ()) -> None:
        """Generate (export) the font to a binary format.

        Args:
            path:  Destination file path (.otf, .ttf, …).
            flags: Tuple of fontforge generation flags.
        """
        self._font.generate(str(path), flags=flags)

    # ------------------------------------------------------------------
    # Glyph access
    # ------------------------------------------------------------------

    @property
    def glyphs(self) -> list:
        """Return a list of raw fontforge glyph objects in this font."""
        result = []
        for name in self._font:
            try:
                result.append(self._font[name])
    def glyphs(self) -> Iterable:
        """Iterate over all glyphs in the font."""
        from aifont.core.glyph import Glyph  # noqa: PLC0415

        for name in self._font:
            yield Glyph(self._font[name])

    def glyph(self, name_or_codepoint: str | int) -> Glyph:
        """Return a :class:`~aifont.core.glyph.Glyph` by name or codepoint."""
        from aifont.core.glyph import Glyph  # noqa: PLC0415

        return Glyph(self._font[name_or_codepoint])
    def glyphs(self) -> list:
        """Return a list of :class:`~aifont.core.glyph.Glyph` wrappers.

        Only glyphs that are present in the font (i.e. have an encoding slot
        assigned and contain actual outline data or metrics) are returned.
        """
        from aifont.core.glyph import Glyph  # local import avoids circular deps

        result = []
        for name in self._font:
            try:
                result.append(Glyph(self._font[name]))
            except Exception:
                pass
        return result

    def glyph(self, name_or_unicode: str | int) -> "Glyph":
        """Return a single :class:`~aifont.core.glyph.Glyph` by name or codepoint.

        Args:
            name_or_unicode: Glyph name (str) or Unicode code point (int).
        """
        from aifont.core.glyph import Glyph

        return Glyph(self._font[name_or_unicode])

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def metadata(self) -> dict[str, str]:
        """Return a dict of common font metadata fields."""
        f = self._font
        return {
            "family": getattr(f, "familyname", ""),
            "full_name": getattr(f, "fullname", ""),
            "weight": getattr(f, "weight", ""),
            "copyright": getattr(f, "copyright", ""),
            "version": getattr(f, "version", ""),
            "em_size": str(getattr(f, "em", 1000)),
        }

    @metadata.setter
    def metadata(self, data: dict[str, str]) -> None:
        field_map = {
            "family": "familyname",
            "full_name": "fullname",
            "weight": "weight",
            "copyright": "copyright",
            "version": "version",
        }
        for key, ff_attr in field_map.items():
            if key in data:
                setattr(self._font, ff_attr, data[key])

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
    def _raw(self) -> _FFFont:
        """Direct access to the underlying :class:`fontforge.font` object."""
        return self._font

    def __repr__(self) -> str:  # pragma: no cover
        name = getattr(self._font, "familyname", "?")
        return f"<Font family={name!r}>"
    def metadata(self) -> dict:
        """Font-level metadata as a plain dictionary."""
        ff = self._font
        return {
            "fontname": getattr(ff, "fontname", ""),
            "familyname": getattr(ff, "familyname", ""),
            "fullname": getattr(ff, "fullname", ""),
            "weight": getattr(ff, "weight", ""),
            "version": getattr(ff, "version", ""),
        }

    @property
    def path(self) -> Optional[str]:
        """The file path this font was opened from, or *None* for new fonts."""
        return getattr(self._font, "path", None)

    # ------------------------------------------------------------------
    # Internal access
    # ------------------------------------------------------------------

    @property
    def _ff(self) -> object:
        """The raw fontforge font object (use only inside aifont.core)."""
        return self._font
            "copyright": getattr(ff, "copyright", ""),
            "version": getattr(ff, "version", ""),
            "em": getattr(ff, "em", 0),
            "ascent": getattr(ff, "ascent", 0),
            "descent": getattr(ff, "descent", 0),
            "upos": getattr(ff, "upos", 0),
            "uwidth": getattr(ff, "uwidth", 0),
        }

    def set_metadata(self, **kwargs: object) -> None:
        """Update font-level metadata fields.

        Keyword arguments correspond to fontforge font attributes such as
        ``fontname``, ``familyname``, ``weight``, etc.
        """
        for key, value in kwargs.items():
            setattr(self._font, key, value)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @property
    def _ff(self):
        """Direct access to the underlying fontforge font object (internal use)."""
        return self._font

    def close(self) -> None:
        """Close the underlying fontforge font and release resources."""
        try:
            self._font.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        return f"Font(family_name={self.family_name!r}, em={self.em_size})"
        name = getattr(self._font, "fontname", "<unknown>")
        return f"<Font '{name}'>"
