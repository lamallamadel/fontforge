"""
aifont.core.font — high-level Font wrapper around ``fontforge.open()``.

Responsibilities
----------------
- Create new fonts and open existing ones (SFD, UFO, OTF, TTF, …).
- Read and write font-level metadata (name, family, version, copyright).
- Enumerate, add and remove glyphs.
- Save the font back to disk in native SFD format.
- Export the font to binary formats (OTF, TTF, WOFF, …).

All heavy lifting is delegated to the underlying ``fontforge.font`` object.
FontForge is treated as a black-box dependency: ``import fontforge`` is the
only way this module communicates with it.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

try:
    import fontforge  # type: ignore[import]
except ImportError:  # pragma: no cover – no FontForge available in CI
    fontforge = None  # type: ignore[assignment]

from aifont.core.glyph import Glyph


# ---------------------------------------------------------------------------
# Export format helpers
# ---------------------------------------------------------------------------

#: Mapping from a simple format name to the file extension used by fontforge.
_FORMAT_EXT: dict[str, str] = {
    "otf": ".otf",
    "ttf": ".ttf",
    "woff": ".woff",
    "woff2": ".woff2",
    "sfd": ".sfd",
    "ufo": ".ufo",
    "pfb": ".pfb",
    "svg": ".svg",
}


class AIFont:
    """Pythonic high-level wrapper around a :class:`fontforge.font` object.

    Do **not** instantiate this class directly — use the class-method
    constructors :meth:`create` or :meth:`open` instead.
    """

    def __init__(self, _ff_font: object) -> None:
        """Wrap an existing ``fontforge.font`` object.

        Args:
            _ff_font: A live ``fontforge.font`` instance.
        """
        self._font = _ff_font

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, name: str, family: Optional[str] = None) -> "AIFont":
        """Create a new, empty font.

        Args:
            name:   The font name (``fontname`` in FontForge terminology).
            family: Optional family name.  When omitted the family name
                    defaults to *name*.

        Returns:
            A new :class:`AIFont` wrapping a freshly created fontforge font.

        Raises:
            RuntimeError: If FontForge Python bindings are not available.

        Example::

            font = AIFont.create("MyFont", family="Sans-Serif")
        """
        if fontforge is None:
            raise RuntimeError(
                "fontforge Python bindings are not installed. "
                "Install FontForge with Python support to use AIFont."
            )
        ff = fontforge.font()
        ff.fontname = name
        ff.familyname = family if family is not None else name
        ff.fullname = name
        return cls(ff)

    @classmethod
    def open(cls, path: str | Path) -> "AIFont":
        """Open an existing font file.

        Supports any format that FontForge can read, including SFD, UFO,
        OTF, TTF, WOFF, PFB and SVG.

        Args:
            path: Path to the font file.

        Returns:
            A new :class:`AIFont` wrapping the loaded font.

        Raises:
            FileNotFoundError: If *path* does not exist.
            RuntimeError:      If FontForge Python bindings are not available.

        Example::

            font = AIFont.open("existing_font.sfd")
        """
        if fontforge is None:
            raise RuntimeError(
                "fontforge Python bindings are not installed. "
                "Install FontForge with Python support to use AIFont."
            )
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Font file not found: {path}")
        ff = fontforge.open(str(path))
        return cls(ff)

    # ------------------------------------------------------------------
    # Metadata — name
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """The PostScript / internal font name (``fontname``)."""
        return str(getattr(self._font, "fontname", "") or "")

    @name.setter
    def name(self, value: str) -> None:
        self._font.fontname = value

    # ------------------------------------------------------------------
    # Metadata — family
    # ------------------------------------------------------------------

    @property
    def family(self) -> str:
        """The font family name (``familyname``)."""
        return str(getattr(self._font, "familyname", "") or "")

    @family.setter
    def family(self, value: str) -> None:
        self._font.familyname = value

    # ------------------------------------------------------------------
    # Metadata — version
    # ------------------------------------------------------------------

    @property
    def version(self) -> str:
        """The font version string."""
        return str(getattr(self._font, "version", "") or "")

    @version.setter
    def version(self, value: str) -> None:
        self._font.version = value

    # ------------------------------------------------------------------
    # Metadata — copyright
    # ------------------------------------------------------------------

    @property
    def copyright(self) -> str:
        """The copyright notice embedded in the font."""
        return str(getattr(self._font, "copyright", "") or "")

    @copyright.setter
    def copyright(self, value: str) -> None:
        self._font.copyright = value

    # ------------------------------------------------------------------
    # Glyph management
    # ------------------------------------------------------------------

    def list_glyphs(self) -> List[str]:
        """Return the names of all glyphs currently in the font.

        Returns:
            A list of glyph name strings, e.g. ``['A', 'B', 'space', …]``.

        Example::

            names = font.list_glyphs()  # → ['A', 'B', 'C', ...]
        """
        names: List[str] = []
        for name in self._font:
            names.append(name)
        return names

    def add_glyph(self, name: str, unicode_value: int = -1) -> Glyph:
        """Add a new glyph to the font.

        If a glyph with *name* already exists, the existing glyph is returned.

        Args:
            name:          The glyph name (e.g. ``'A'``).
            unicode_value: Unicode code point to assign, or ``-1`` to
                           determine it automatically from the glyph name.

        Returns:
            A :class:`~aifont.core.glyph.Glyph` wrapper for the new glyph.

        Example::

            glyph = font.add_glyph('A')
        """
        ff_glyph = self._font.createChar(unicode_value, name)
        return Glyph(ff_glyph)

    def remove_glyph(self, name: str) -> None:
        """Remove a glyph from the font by name.

        Args:
            name: The glyph name to remove (e.g. ``'Z'``).

        Raises:
            KeyError: If no glyph with *name* exists in the font.

        Example::

            font.remove_glyph('Z')
        """
        if name not in self._font:
            raise KeyError(f"Glyph '{name}' not found in font.")
        self._font[name].unlinkThisGlyph()
        self._font.removeGlyph(name)

    def get_glyph(self, name: str) -> Glyph:
        """Return a :class:`~aifont.core.glyph.Glyph` wrapper for *name*.

        Args:
            name: The glyph name (e.g. ``'A'``).

        Raises:
            KeyError: If no glyph with *name* exists in the font.

        Example::

            g = font.get_glyph('A')
        """
        if name not in self._font:
            raise KeyError(f"Glyph '{name}' not found in font.")
        return Glyph(self._font[name])

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str | Path) -> None:
        """Save the font in FontForge's native SFD format.

        Args:
            path: Destination ``.sfd`` file path.

        Example::

            font.save("output.sfd")
        """
        self._font.save(str(path))

    def export(self, fmt: str, path: Optional[str | Path] = None) -> Path:
        """Generate a binary font file.

        Args:
            fmt:  Format name, e.g. ``"otf"``, ``"ttf"``, ``"woff"``,
                  ``"woff2"``, ``"svg"``.  Case-insensitive.
            path: Destination file path.  When *None*, the file is created
                  in the current working directory using the font name and
                  the appropriate extension.

        Returns:
            The :class:`~pathlib.Path` of the generated file.

        Raises:
            ValueError: If *fmt* is not a recognised export format.

        Example::

            out = font.export("otf")          # → Path('MyFont.otf')
            out = font.export("ttf", "/tmp/my.ttf")
        """
        fmt = fmt.lower()
        ext = _FORMAT_EXT.get(fmt)
        if ext is None:
            raise ValueError(
                f"Unknown export format '{fmt}'. "
                f"Supported formats: {', '.join(_FORMAT_EXT)}"
            )
        if path is None:
            path = Path(f"{self.name}{ext}")
        else:
            path = Path(path)
        self._font.generate(str(path))
        return path

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "AIFont":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying fontforge font and release resources."""
        try:
            self._font.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _ff(self) -> object:
        """Direct access to the underlying ``fontforge.font`` (internal use)."""
        return self._font

    def __repr__(self) -> str:
        return f"<AIFont name={self.name!r} family={self.family!r}>"
