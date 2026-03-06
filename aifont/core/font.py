"""aifont.core.font — high-level Font wrapper around ``fontforge.font``.

Responsibilities:
- Open and save font files.
- Iterate over glyphs.
- Read/write font-level metadata (name, family, weight, em size, etc.).

All heavy lifting is delegated to the underlying ``fontforge.font`` object.
FontForge source code is never modified.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from pathlib import Path

try:
    import fontforge  # type: ignore

    if not hasattr(fontforge, "font"):
        fontforge = None  # type: ignore
except ImportError:  # pragma: no cover
    fontforge = None  # type: ignore

from aifont.core.glyph import Glyph

# Module-level references used by Font.open() / Font.new() and patchable in tests
_ff = fontforge
_FF_AVAILABLE: bool = fontforge is not None

# ---------------------------------------------------------------------------
# Metadata fields accepted by set_metadata() — fontforge attribute names
# ---------------------------------------------------------------------------
_METADATA_FIELDS = frozenset(
    {
        "fontname",
        "familyname",
        "fullname",
        "version",
        "copyright",
        "em",
        "ascent",
        "descent",
        "italicangle",
        "weight",
    }
)


class FontMetadata:
    """Dict-like and attribute-based view of a font's metadata.

    Supports both fontforge-style key access (``metadata["fontname"]``)
    and Pythonic attribute access (``metadata.family_name``).
    """

    def __init__(self, ff_font: object) -> None:
        object.__setattr__(self, "_ff", ff_font)

    # ------------------------------------------------------------------
    # Dict-like interface (fontforge attribute names as keys)
    # ------------------------------------------------------------------

    def __contains__(self, key: object) -> bool:
        return key in _METADATA_FIELDS

    def __getitem__(self, key: str) -> object:
        if key not in _METADATA_FIELDS:
            raise KeyError(key)
        ff = object.__getattribute__(self, "_ff")
        return getattr(ff, key, None)

    def __setitem__(self, key: str, value: object) -> None:
        if key not in _METADATA_FIELDS:
            raise KeyError(key)
        ff = object.__getattribute__(self, "_ff")
        setattr(ff, key, value)

    # ------------------------------------------------------------------
    # Pythonic attribute access
    # ------------------------------------------------------------------

    @property
    def family_name(self) -> str:
        ff = object.__getattribute__(self, "_ff")
        return str(getattr(ff, "familyname", "") or "")

    @family_name.setter
    def family_name(self, value: str) -> None:
        ff = object.__getattribute__(self, "_ff")
        ff.familyname = value  # type: ignore[union-attr]

    @property
    def full_name(self) -> str:
        ff = object.__getattribute__(self, "_ff")
        return str(getattr(ff, "fullname", "") or "")

    @full_name.setter
    def full_name(self, value: str) -> None:
        ff = object.__getattribute__(self, "_ff")
        ff.fullname = value  # type: ignore[union-attr]

    @property
    def name(self) -> str:
        """PostScript font name (``fontname``). Alias for :attr:`font_name`."""
        ff = object.__getattribute__(self, "_ff")
        return str(getattr(ff, "fontname", "") or "")

    @name.setter
    def name(self, value: str) -> None:
        ff = object.__getattribute__(self, "_ff")
        ff.fontname = value  # type: ignore[union-attr]

    @property
    def family(self) -> str:
        """Font family name (``familyname``). Alias for :attr:`family_name`."""
        ff = object.__getattribute__(self, "_ff")
        return str(getattr(ff, "familyname", "") or "")

    @family.setter
    def family(self, value: str) -> None:
        ff = object.__getattribute__(self, "_ff")
        ff.familyname = value  # type: ignore[union-attr]

    @property
    def font_name(self) -> str:
        """Alias for :attr:`name`."""
        return self.name

    @property
    def version(self) -> str:
        ff = object.__getattribute__(self, "_ff")
        return str(getattr(ff, "version", "") or "")

    @version.setter
    def version(self, value: str) -> None:
        ff = object.__getattribute__(self, "_ff")
        ff.version = value  # type: ignore[union-attr]

    @property
    def copyright(self) -> str:
        ff = object.__getattribute__(self, "_ff")
        return str(getattr(ff, "copyright", "") or "")

    @copyright.setter
    def copyright(self, value: str) -> None:
        ff = object.__getattribute__(self, "_ff")
        ff.copyright = value  # type: ignore[union-attr]

    @property
    def weight(self) -> str:
        ff = object.__getattribute__(self, "_ff")
        return str(getattr(ff, "weight", "") or "")

    @weight.setter
    def weight(self, value: str) -> None:
        ff = object.__getattribute__(self, "_ff")
        ff.weight = value  # type: ignore[union-attr]

    @property
    def em_size(self) -> int:
        ff = object.__getattribute__(self, "_ff")
        return int(getattr(ff, "em", 1000))

    @em_size.setter
    def em_size(self, value: int) -> None:
        ff = object.__getattribute__(self, "_ff")
        ff.em = int(value)  # type: ignore[union-attr]

    @property
    def ascent(self) -> int:
        ff = object.__getattribute__(self, "_ff")
        return int(getattr(ff, "ascent", 800))

    @ascent.setter
    def ascent(self, value: int) -> None:
        ff = object.__getattribute__(self, "_ff")
        ff.ascent = int(value)  # type: ignore[union-attr]

    @property
    def descent(self) -> int:
        ff = object.__getattribute__(self, "_ff")
        return int(getattr(ff, "descent", 200))

    @descent.setter
    def descent(self, value: int) -> None:
        ff = object.__getattribute__(self, "_ff")
        ff.descent = int(value)  # type: ignore[union-attr]

    def to_dict(self) -> dict:
        """Return a plain dict snapshot of the metadata."""
        return {
            "name": self.name,
            "family": self.family,
            "weight": self.weight,
            "version": self.version,
            "copyright": self.copyright,
            "em_size": self.em_size,
        }

    def __repr__(self) -> str:
        return f"FontMetadata(name={self.name!r}, family={self.family!r}, weight={self.weight!r})"


class Font:
    """Pythonic wrapper around a :class:`fontforge.font` object.

    Example::

        font = Font.open("MyFont.otf")
        for glyph in font.glyphs:
            print(glyph.name)
        font.save("MyFont_modified.sfd")
    """

    def __init__(self, _ff_font: object) -> None:
        """Initialise from an existing fontforge font object.

        Args:
            _ff_font: A live :class:`fontforge.font` instance.
        """
        self._font = _ff_font

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _ff(self) -> object:
        """Return the underlying fontforge font object."""
        return self._font

    @property
    def raw(self) -> object:
        """The underlying ``fontforge.font`` object."""
        return self._font

    @property
    def ff_font(self) -> object:
        """Alias for :attr:`raw`."""
        return self._font

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def open(cls, path: str | Path) -> Font:
        """Open an existing font file and return a :class:`Font` instance."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Font file not found: {path}")
        import aifont.core.font as _self_mod

        if not _self_mod._FF_AVAILABLE or _self_mod._ff is None:
            raise RuntimeError("fontforge Python bindings are not available.")
        return cls(_self_mod._ff.open(str(p)))  # type: ignore[union-attr]

    @classmethod
    def new(cls, name: str = "") -> Font:
        """Create a new, empty font and return a :class:`Font` instance."""
        import aifont.core.font as _self_mod

        if not _self_mod._FF_AVAILABLE or _self_mod._ff is None:
            raise RuntimeError("fontforge Python bindings are not available.")
        ff = _self_mod._ff.font()  # type: ignore[union-attr]
        if name:
            ff.fontname = name
            ff.familyname = name
            ff.fullname = name
        return cls(ff)

    @classmethod
    def create(cls, name: str, *, family: str = "") -> Font:
        """Create a new font with the given *name*.

        Args:
            name:   PostScript font name and default family name.
            family: Family name (defaults to *name*).

        Returns:
            A new :class:`Font` instance.
        """
        font = cls.new()
        font.name = name
        font.family = family or name
        return font

    # ------------------------------------------------------------------
    # Metadata properties
    # ------------------------------------------------------------------

    @property
    def metadata(self) -> FontMetadata:
        """Return a :class:`FontMetadata` view of this font's metadata."""
        return FontMetadata(self._font)

    def set_metadata(self, **kwargs: object) -> None:
        """Set one or more metadata fields on the font.

        Args:
            **kwargs: Keyword arguments where keys are fontforge attribute
                      names (``fontname``, ``familyname``, ``em``, etc.).

        Raises:
            ValueError: If an unknown field name is passed.
        """
        for key, value in kwargs.items():
            if key not in _METADATA_FIELDS:
                raise ValueError(
                    f"Unknown metadata field: {key!r}. Valid fields: {sorted(_METADATA_FIELDS)}"
                )
            setattr(self._font, key, value)

    @property
    def name(self) -> str:
        """The PostScript font name (``fontname``)."""
        return str(getattr(self._font, "fontname", "") or "")

    @name.setter
    def name(self, value: str) -> None:
        self._font.fontname = value  # type: ignore[union-attr]

    @property
    def font_name(self) -> str:
        """Alias for :attr:`name`."""
        return self.name

    @font_name.setter
    def font_name(self, value: str) -> None:
        self.name = value

    @property
    def family(self) -> str:
        """The font family name (``familyname``)."""
        return str(getattr(self._font, "familyname", "") or "")

    @family.setter
    def family(self, value: str) -> None:
        self._font.familyname = value  # type: ignore[union-attr]

    @property
    def family_name(self) -> str:
        """Alias for :attr:`family`."""
        return self.family

    @family_name.setter
    def family_name(self, value: str) -> None:
        self.family = value

    @property
    def version(self) -> str:
        """The font version string."""
        return str(getattr(self._font, "version", "") or "")

    @version.setter
    def version(self, value: str) -> None:
        self._font.version = value  # type: ignore[union-attr]

    @property
    def copyright(self) -> str:
        """The copyright notice embedded in the font."""
        return str(getattr(self._font, "copyright", "") or "")

    @copyright.setter
    def copyright(self, value: str) -> None:
        self._font.copyright = value  # type: ignore[union-attr]

    @property
    def em_size(self) -> int:
        """Units per em (typically 1000 or 2048)."""
        return int(getattr(self._font, "em", 1000))

    @em_size.setter
    def em_size(self, value: int) -> None:
        self._font.em = value  # type: ignore[union-attr]

    @property
    def ascent(self) -> int:
        """Ascender value in font units."""
        return int(getattr(self._font, "ascent", 800))

    @ascent.setter
    def ascent(self, value: int) -> None:
        self._font.ascent = value  # type: ignore[union-attr]

    @property
    def descent(self) -> int:
        """Descender value in font units."""
        return int(getattr(self._font, "descent", 200))

    @descent.setter
    def descent(self, value: int) -> None:
        self._font.descent = value  # type: ignore[union-attr]

    @property
    def italic_angle(self) -> float:
        """Italic angle in degrees (0 for upright fonts)."""
        return float(getattr(self._font, "italicangle", 0.0))

    @italic_angle.setter
    def italic_angle(self, value: float) -> None:
        self._font.italicangle = value  # type: ignore[union-attr]

    @property
    def glyph_count(self) -> int:
        """Total number of glyphs in the font."""
        return len(self)

    # ------------------------------------------------------------------
    # Glyph access
    # ------------------------------------------------------------------

    @property
    def glyphs(self) -> list[Glyph]:
        """Return all glyphs in the font as a list of :class:`Glyph` wrappers."""
        result: list[Glyph] = []
        for glyph_name in self._font:  # type: ignore[union-attr]
            try:
                ff_glyph = self._font[glyph_name]  # type: ignore[index]
                result.append(Glyph(ff_glyph))
            except Exception:  # noqa: BLE001
                pass
        return result

    def __iter__(self) -> Iterator[Glyph]:
        """Iterate over all glyphs in the font."""
        return iter(self.glyphs)

    def __len__(self) -> int:
        """Return the number of glyphs in the font."""
        return sum(1 for _ in self._font)  # type: ignore[union-attr]

    def __contains__(self, item: object) -> bool:
        """Test membership by glyph name or Unicode code-point."""
        try:
            _ = self._font[item]  # type: ignore[index]
            return True
        except Exception:  # noqa: BLE001
            return False

    def __getitem__(self, key: str | int) -> Glyph:
        """Return the glyph identified by *key* (name or code-point)."""
        try:
            return Glyph(self._font[key])  # type: ignore[index]
        except Exception as exc:
            raise KeyError(key) from exc

    def glyph(self, name_or_codepoint: str | int) -> Glyph | None:
        """Return a :class:`Glyph` by name or code-point, or ``None`` if absent."""
        try:
            return Glyph(self._font[name_or_codepoint])  # type: ignore[index]
        except Exception:  # noqa: BLE001
            return None

    def get_glyph(self, name_or_codepoint: str | int) -> Glyph:
        """Return a :class:`Glyph` by name or code-point.

        Raises:
            KeyError: If no such glyph exists.
        """
        g = self.glyph(name_or_codepoint)
        if g is None:
            raise KeyError(name_or_codepoint)
        return g

    def list_glyphs(self) -> list[str]:
        """Return a list of all glyph names in the font."""
        return [g.name for g in self.glyphs]

    def add_glyph(self, name: str, unicode_val: int = -1) -> Glyph:
        """Create a new glyph with the given *name* (chainable alias for create_glyph).

        Args:
            name:        Glyph name.
            unicode_val: Unicode code-point (default ``-1`` = no assignment).

        Returns:
            The newly created :class:`Glyph`.
        """
        return self.create_glyph(name, unicode_val)

    def create_glyph(
        self,
        name_or_unicode: str | int,
        unicode_or_name: str | int | None = None,
    ) -> Glyph:
        """Create a new glyph in the font.

        Accepts two calling conventions:

        * ``create_glyph(name, unicode_val)`` — name first, code-point second.
        * ``create_glyph(unicode_val, name)`` — code-point first, name second.

        Args:
            name_or_unicode: Glyph name (str) or Unicode code-point (int).
            unicode_or_name: Unicode code-point (int) or glyph name (str).

        Returns:
            The newly created :class:`Glyph`.
        """
        if isinstance(name_or_unicode, str):
            name = name_or_unicode
            unicode_val = int(unicode_or_name) if unicode_or_name is not None else -1
        else:
            unicode_val = int(name_or_unicode)
            name = str(unicode_or_name) if unicode_or_name is not None else None  # type: ignore[assignment]

        if name is not None:
            ff_glyph = self._font.createChar(unicode_val, name)  # type: ignore[union-attr]
        else:
            ff_glyph = self._font.createChar(unicode_val)  # type: ignore[union-attr]
        return Glyph(ff_glyph)

    def remove_glyph(self, name: str) -> None:
        """Remove a glyph from the font by name.

        Raises:
            KeyError: If no glyph with *name* exists.
        """
        if name not in self._font:  # type: ignore[operator]
            raise KeyError(f"Glyph '{name}' not found in font.")
        self._font.removeGlyph(name)  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str | Path, fmt: str | None = None) -> None:
        """Save the font.

        Args:
            path: Destination file path.
            fmt:  Optional format string (passed as second arg to fontforge save).
        """
        if fmt is not None:
            self._font.save(str(path), fmt)  # type: ignore[union-attr]
        else:
            self._font.save(str(path))  # type: ignore[union-attr]

    def generate(self, path: str | Path, flags: tuple | None = None) -> None:
        """Generate (compile) the font to *path*.

        Args:
            path:  Destination file path.
            flags: Optional fontforge generate flags tuple.
        """
        if flags:
            self._font.generate(str(path), flags=flags)  # type: ignore[union-attr]
        else:
            self._font.generate(str(path))  # type: ignore[union-attr]

    def export(self, fmt: str, path: str | Path | None = None) -> Path:
        """Generate a binary font file.

        Args:
            fmt:  Format name (e.g. ``"otf"``, ``"ttf"``, ``"woff2"``).
            path: Destination file path. Defaults to ``<fontname>.<ext>``.

        Returns:
            The :class:`~pathlib.Path` of the generated file.

        Raises:
            ValueError: If the format is not recognised.
        """
        fmt_lower = fmt.lower()
        format_ext: dict[str, str] = {
            "otf": ".otf",
            "ttf": ".ttf",
            "woff": ".woff",
            "woff2": ".woff2",
            "sfd": ".sfd",
            "ufo": ".ufo",
            "pfb": ".pfb",
            "svg": ".svg",
        }
        if fmt_lower not in format_ext:
            raise ValueError(
                f"Unknown export format: {fmt!r}. "
                f"Supported formats: {', '.join(sorted(format_ext))}"
            )
        ext = format_ext[fmt_lower]
        path = Path(f"{self.name}{ext}") if path is None else Path(path)
        if fmt_lower == "sfd":
            self._font.save(str(path))  # type: ignore[union-attr]
        else:
            self._font.generate(str(path))  # type: ignore[union-attr]
        return path

    def close(self) -> None:
        """Close the underlying fontforge font and release resources."""
        with contextlib.suppress(Exception):
            self._font.close()  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> Font:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        try:
            n = len(self)
        except Exception:  # noqa: BLE001
            n = "?"  # type: ignore[assignment]
        return f"Font(name={self.name!r}, family={self.family!r}, glyphs={n})"


# AIFont is an alias for Font, providing a more product-specific name.
AIFont = Font
