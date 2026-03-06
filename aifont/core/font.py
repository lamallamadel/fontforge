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

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def open(cls, path: str | Path) -> "Font":
        """Open an existing font file.

        Args:
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
