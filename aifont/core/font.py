"""High-level Font wrapper around fontforge.font."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional

try:
    import fontforge as _ff

    _FF_AVAILABLE = hasattr(_ff, "font")
except ImportError:
    _ff = None  # type: ignore[assignment]
    _FF_AVAILABLE = False

if TYPE_CHECKING:
    from aifont.core.glyph import Glyph


class FontMetadata:
    """Structured font metadata."""

    def __init__(self, ff_font: object) -> None:
        self._ff = ff_font

    @property
    def name(self) -> str:
        return getattr(self._ff, "fontname", "")

    @name.setter
    def name(self, value: str) -> None:
        self._ff.fontname = value  # type: ignore[union-attr]

    @property
    def family(self) -> str:
        return getattr(self._ff, "familyname", "")

    @family.setter
    def family(self, value: str) -> None:
        self._ff.familyname = value  # type: ignore[union-attr]

    @property
    def weight(self) -> str:
        return getattr(self._ff, "weight", "Regular")

    @weight.setter
    def weight(self, value: str) -> None:
        self._ff.weight = value  # type: ignore[union-attr]

    @property
    def version(self) -> str:
        return getattr(self._ff, "version", "")

    @version.setter
    def version(self, value: str) -> None:
        self._ff.version = value  # type: ignore[union-attr]

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "family": self.family,
            "weight": self.weight,
            "version": self.version,
        }


class Font:
    """Pythonic wrapper around a fontforge.font object.

    All low-level operations are delegated to the underlying fontforge
    font object.  Never call fontforge directly — use this class.
    """

    def __init__(self, _ff_font: object) -> None:
        self._ff = _ff_font
        self._metadata = FontMetadata(_ff_font)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def open(cls, path: str) -> "Font":
        """Open an existing font file and return a Font instance."""
        if not _FF_AVAILABLE or _ff is None:
            raise RuntimeError(
                "fontforge Python bindings are not available. "
                "Install fontforge to use Font.open()."
            )
        if not os.path.exists(path):
            raise FileNotFoundError(f"Font file not found: {path}")
        ff_font = _ff.open(path)  # type: ignore[union-attr]
        return cls(ff_font)

    @classmethod
    def new(cls, name: str = "") -> "Font":
        """Create a new empty font and return a Font instance."""
        if not _FF_AVAILABLE or _ff is None:
            raise RuntimeError(
                "fontforge Python bindings are not available. "
                "Install fontforge to use Font.new()."
            )
        ff_font = _ff.font()  # type: ignore[union-attr]
        ff_font.fontname = name
        return cls(ff_font)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def metadata(self) -> FontMetadata:
        """Return structured font metadata."""
        return self._metadata

    @property
    def glyphs(self) -> List["Glyph"]:
        """Return all glyphs in the font as a list of Glyph wrappers."""
        from aifont.core.glyph import Glyph as _Glyph

        result: List["Glyph"] = []
        for glyph_name in self._ff:  # type: ignore[union-attr]
            ff_glyph = self._ff[glyph_name]  # type: ignore[index]
            result.append(_Glyph(ff_glyph))
        return result

    @property
    def glyph_count(self) -> int:
        """Return the number of glyphs in the font."""
        try:
            return len(list(self._ff))  # type: ignore[arg-type]
        except TypeError:
            return 0

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def get_glyph(self, name: str) -> "Glyph":
        """Return a Glyph by name."""
        from aifont.core.glyph import Glyph as _Glyph

        try:
            ff_glyph = self._ff[name]  # type: ignore[index]
        except (KeyError, TypeError) as exc:
            raise KeyError(f"Glyph not found: {name}") from exc
        return _Glyph(ff_glyph)

    def save(self, path: str, fmt: Optional[str] = None) -> None:
        """Save the font to *path*.

        *fmt* is forwarded to fontforge.font.save() if provided.
        """
        if fmt is not None:
            self._ff.save(path, fmt)  # type: ignore[union-attr]
        else:
            self._ff.save(path)  # type: ignore[union-attr]

    def generate(self, path: str) -> None:
        """Generate (compile) the font to *path*."""
        self._ff.generate(path)  # type: ignore[union-attr]

    def close(self) -> None:
        """Close the underlying fontforge font object."""
        if hasattr(self._ff, "close"):
            self._ff.close()  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Iteration / context manager
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator["Glyph"]:
        return iter(self.glyphs)

    def __len__(self) -> int:
        return self.glyph_count

    def __enter__(self) -> "Font":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"Font(name={self.metadata.name!r}, glyphs={self.glyph_count})"
