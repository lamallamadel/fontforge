"""aifont.core.font — high-level Font wrapper around fontforge.open().

FontForge is the underlying engine.  DO NOT modify FontForge source code.
This module wraps the ``fontforge.font`` object with a clean Pythonic API.
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
        self._font = _ff_font

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
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
            except Exception:
                pass
        return result

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
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
