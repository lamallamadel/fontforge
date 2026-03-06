"""aifont.core.variable — Variable Font axis/instance/master support.

This module adds OpenType Variable Font capabilities to the AIFont SDK.
It wraps fontTools.designSpaceLib and fontTools.varLib to build variable
fonts from multiple FontForge masters.

FontForge is the underlying engine. DO NOT modify FontForge source code.
All font operations go through fontforge Python bindings or fontTools.

Supported axes (standard OpenType tags):
    wght — Weight  (100–900)
    wdth — Width   (50–200, percentage of normal)
    ital — Italic  (0 or 1)
    opsz — Optical size (in typographic points)

Typical workflow::

    from aifont.core.variable import VariationAxis, Master, NamedInstance, VariableFontBuilder

    builder = VariableFontBuilder()
    builder.add_axis(VariationAxis("wght", "Weight", minimum=100, default=400, maximum=900))

    builder.add_master(Master("Regular", "path/to/regular.ufo", location={"wght": 400}))
    builder.add_master(Master("Bold",    "path/to/bold.ufo",    location={"wght": 700}))

    builder.add_instance(NamedInstance("Regular", location={"wght": 400}))
    builder.add_instance(NamedInstance("Bold",    location={"wght": 700}))
    builder.add_instance(NamedInstance("SemiBold",location={"wght": 600}))

    builder.export_variable_ttf("MyFont-Variable.ttf")
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    from fontTools.designspaceLib import (
        AxisDescriptor,
        DesignSpaceDocument,
        InstanceDescriptor,
        SourceDescriptor,
    )
    from fontTools.varLib import build as _varlib_build

    _FONTTOOLS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FONTTOOLS_AVAILABLE = False

try:
    import importlib.util

    _FF_AVAILABLE = importlib.util.find_spec("fontforge") is not None
except Exception:  # pragma: no cover
    _FF_AVAILABLE = False


# ---------------------------------------------------------------------------
# Standard OpenType variation axis tags
# ---------------------------------------------------------------------------

STANDARD_AXES: dict[str, str] = {
    "wght": "Weight",
    "wdth": "Width",
    "ital": "Italic",
    "opsz": "Optical Size",
    "slnt": "Slant",
}

# Recommended default ranges for standard axes
AXIS_RANGES: dict[str, tuple[float, float, float]] = {
    "wght": (100.0, 400.0, 900.0),  # (minimum, default, maximum)
    "wdth": (50.0, 100.0, 200.0),
    "ital": (0.0, 0.0, 1.0),
    "opsz": (6.0, 12.0, 144.0),
    "slnt": (-90.0, 0.0, 90.0),
}


# ---------------------------------------------------------------------------
# Public data classes
# ---------------------------------------------------------------------------


@dataclass
class VariationAxis:
    """Defines one axis of variation in a variable font.

    Attributes:
        tag:     Four-character OpenType axis tag (e.g. ``"wght"``).
        name:    Human-readable axis name (e.g. ``"Weight"``).
        minimum: Minimum axis value.
        default: Default axis value (the value at which the font appears normal).
        maximum: Maximum axis value.
        hidden:  When *True* the axis is hidden from end-user UIs.
    """

    tag: str
    name: str
    minimum: float
    default: float
    maximum: float
    hidden: bool = False

    def __post_init__(self) -> None:
        if len(self.tag) != 4:
            raise ValueError(f"Axis tag must be exactly 4 characters, got {self.tag!r}")
        if not (self.minimum <= self.default <= self.maximum):
            raise ValueError(
                f"Axis {self.tag!r}: minimum ({self.minimum}) <= default ({self.default})"
                f" <= maximum ({self.maximum}) must hold."
            )

    @classmethod
    def from_tag(cls, tag: str, **overrides: float) -> VariationAxis:
        """Construct a :class:`VariationAxis` from a standard OpenType tag.

        Sensible defaults are applied for well-known tags (``wght``, ``wdth``,
        ``ital``, ``opsz``, ``slnt``).

        Args:
            tag:      Four-character axis tag.
            **overrides: Optional keyword arguments ``minimum``, ``default``,
                          ``maximum`` that override the built-in defaults.

        Returns:
            A configured :class:`VariationAxis`.

        Raises:
            ValueError: If *tag* is unknown and no range overrides are supplied.
        """
        if tag in AXIS_RANGES:
            mn, df, mx = AXIS_RANGES[tag]
        elif {"minimum", "default", "maximum"}.issubset(overrides):
            mn, df, mx = overrides["minimum"], overrides["default"], overrides["maximum"]
        else:
            raise ValueError(
                f"Unknown axis tag {tag!r}. Provide minimum/default/maximum explicitly."
            )
        return cls(
            tag=tag,
            name=str(overrides.get("name", STANDARD_AXES.get(tag, tag))),
            minimum=overrides.get("minimum", mn),
            default=overrides.get("default", df),
            maximum=overrides.get("maximum", mx),
            hidden=bool(overrides.get("hidden", False)),
        )


@dataclass
class NamedInstance:
    """A named instance (static snapshot) within a variable font.

    Named instances allow applications to present preset styles (e.g.
    *Regular*, *Bold*, *Light*) even though the font supports continuous
    variation.

    Attributes:
        name:         PostScript-friendly style name (e.g. ``"SemiBold"``).
        location:     Mapping of axis tag → design-space coordinate.
        family_name:  Optional override for the family name.
        style_name:   Optional explicit style name (defaults to ``name``).
        postscript_name: Optional PostScript name for this instance.
    """

    name: str
    location: dict[str, float]
    family_name: str | None = None
    style_name: str | None = None
    postscript_name: str | None = None

    def __post_init__(self) -> None:
        if self.style_name is None:
            self.style_name = self.name


@dataclass
class Master:
    """A font master (source) used as an interpolation endpoint.

    Each master represents a fully-drawn font at a specific position in the
    design space.  Masters must be UFO directories or font files that
    fontTools can open.

    Attributes:
        name:     Human-readable master name (e.g. ``"Regular"``).
        path:     File-system path to the UFO / font file for this master.
        location: Mapping of axis tag → design-space coordinate.
        is_default: When *True* this master is the default source.
        family_name: Override for the family name in the generated font.
        style_name:  Override for the style name.
    """

    name: str
    path: str | Path
    location: dict[str, float]
    is_default: bool = False
    family_name: str | None = None
    style_name: str | None = None

    def __post_init__(self) -> None:
        self.path = Path(self.path)


# ---------------------------------------------------------------------------
# Interpolation utilities
# ---------------------------------------------------------------------------


def interpolate(
    value_at_min: float,
    value_at_max: float,
    t: float,
) -> float:
    """Linear interpolation between two scalar values.

    Args:
        value_at_min: Value at ``t=0``.
        value_at_max: Value at ``t=1``.
        t:            Interpolation factor in ``[0, 1]``.

    Returns:
        The interpolated value.

    Raises:
        ValueError: If *t* is outside ``[0, 1]``.
    """
    if not (0.0 <= t <= 1.0):
        raise ValueError(f"Interpolation factor t must be in [0, 1], got {t}")
    return value_at_min + t * (value_at_max - value_at_min)


def location_to_normalized(
    location: dict[str, float],
    axes: list[VariationAxis],
) -> dict[str, float]:
    """Normalise a design-space location to ``[−1, 0, +1]`` per axis.

    The normalised value is computed piecewise:
      * default → 0
      * maximum → +1
      * minimum → −1
      * values between default and maximum are mapped to (0, 1)
      * values between minimum and default are mapped to (−1, 0)

    Args:
        location: Mapping of axis tag → design-space value.
        axes:     List of :class:`VariationAxis` definitions.

    Returns:
        Mapping of axis tag → normalised value.
    """
    axis_map = {ax.tag: ax for ax in axes}
    normalised: dict[str, float] = {}
    for tag, value in location.items():
        ax = axis_map.get(tag)
        if ax is None:
            raise ValueError(f"Unknown axis tag {tag!r}")
        if value == ax.default:
            normalised[tag] = 0.0
        elif value > ax.default:
            normalised[tag] = (value - ax.default) / (ax.maximum - ax.default)
        else:
            normalised[tag] = (value - ax.default) / (ax.default - ax.minimum)
    return normalised


# ---------------------------------------------------------------------------
# DesignSpace builder helpers
# ---------------------------------------------------------------------------


def _build_design_space(
    axes: list[VariationAxis],
    masters: list[Master],
    instances: list[NamedInstance],
    family_name: str = "MyVariableFont",
) -> DesignSpaceDocument:
    """Build a :class:`fontTools.designspaceLib.DesignSpaceDocument`.

    Args:
        axes:        List of variation axes.
        masters:     List of source masters.
        instances:   List of named instances.
        family_name: Font family name.

    Returns:
        A populated :class:`DesignSpaceDocument`.

    Raises:
        ImportError: If fontTools is not installed.
    """
    if not _FONTTOOLS_AVAILABLE:
        raise ImportError(
            "fontTools is required for variable font support. "
            "Install it with:  pip install fonttools"
        )

    doc = DesignSpaceDocument()
    doc.family_name = family_name

    # Axes
    for ax in axes:
        desc = AxisDescriptor()
        desc.tag = ax.tag
        desc.name = ax.name
        desc.minimum = ax.minimum
        desc.default = ax.default
        desc.maximum = ax.maximum
        desc.hidden = ax.hidden
        doc.addAxis(desc)

    # Sources / masters
    for master in masters:
        src = SourceDescriptor()
        src.path = str(master.path)
        src.name = master.name
        src.familyName = master.family_name or family_name
        src.styleName = master.style_name or master.name
        src.location = dict(master.location)
        if master.is_default:
            # Mark the default master
            src.copyInfo = True
            src.copyFeatures = True
        doc.addSource(src)

    # Named instances
    for inst in instances:
        idesc = InstanceDescriptor()
        idesc.name = inst.name
        idesc.familyName = inst.family_name or family_name
        idesc.styleName = inst.style_name or inst.name
        idesc.postScriptFontName = inst.postscript_name
        idesc.location = dict(inst.location)
        doc.addInstance(idesc)

    return doc


# ---------------------------------------------------------------------------
# Preview helpers
# ---------------------------------------------------------------------------


def preview_interpolation(
    axes: list[VariationAxis],
    masters: list[Master],
    target_location: dict[str, float],
) -> dict[str, float]:
    """Return a preview of where a target location sits relative to each axis.

    This is a lightweight utility that does *not* require font data — it only
    performs design-space calculations.  The result maps each axis tag to:

    * The normalised value at the target location (range ``[−1, +1]``).
    * A human-readable description of the position.

    Args:
        axes:            List of :class:`VariationAxis` definitions.
        masters:         List of :class:`Master` sources (used to list nearby
                         masters along each axis).
        target_location: Mapping of axis tag → design-space coordinate.

    Returns:
        A dict with axis tags as keys and dicts
        ``{"value": float, "normalised": float, "nearest_master": str}`` as
        values.
    """
    axis_map = {ax.tag: ax for ax in axes}
    result: dict[str, dict] = {}

    for tag, value in target_location.items():
        ax = axis_map.get(tag)
        if ax is None:
            continue

        # Normalise
        if value == ax.default:
            norm = 0.0
        elif value > ax.default and ax.maximum > ax.default:
            norm = (value - ax.default) / (ax.maximum - ax.default)
        elif value < ax.default and ax.default > ax.minimum:
            norm = (value - ax.default) / (ax.default - ax.minimum)
        else:
            norm = 0.0

        # Find nearest master along this axis
        nearest = None
        nearest_dist: float = float("inf")
        for m in masters:
            m_val = m.location.get(tag)
            if m_val is not None:
                dist = abs(m_val - value)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = m.name

        result[tag] = {
            "value": value,
            "normalised": norm,
            "nearest_master": nearest,
        }

    return result


# ---------------------------------------------------------------------------
# OpenType conformance checks
# ---------------------------------------------------------------------------


def check_opentype_conformance(
    axes: list[VariationAxis],
    masters: list[Master],
    instances: list[NamedInstance],
) -> list[str]:
    """Run a series of OpenType conformance checks on the variable font setup.

    Returns a list of warning/error messages.  An empty list means all checks
    passed.

    Checks performed:
    1. Each axis tag is exactly 4 characters.
    2. minimum ≤ default ≤ maximum for every axis.
    3. At least one master is marked as default (or exactly one master exists).
    4. Every master location contains all defined axes.
    5. Every instance location contains all defined axes.
    6. Instance locations are within axis min/max bounds.
    7. No duplicate master locations.
    8. No duplicate instance names.

    Args:
        axes:      Defined variation axes.
        masters:   Source masters.
        instances: Named instances.

    Returns:
        List of error/warning strings.  Empty list = no issues found.
    """
    issues: list[str] = []
    axis_tags = {ax.tag for ax in axes}
    axis_map = {ax.tag: ax for ax in axes}

    # Check 1 & 2 — already enforced by VariationAxis.__post_init__, but
    # re-verify here for completeness.
    for ax in axes:
        if len(ax.tag) != 4:
            issues.append(f"Axis tag must be 4 characters: {ax.tag!r}")
        if not (ax.minimum <= ax.default <= ax.maximum):
            issues.append(
                f"Axis {ax.tag!r}: minimum ({ax.minimum}) <= default ({ax.default})"
                f" <= maximum ({ax.maximum}) violated."
            )

    # Check 3 — default master
    default_masters = [m for m in masters if m.is_default]
    if len(masters) > 1 and len(default_masters) == 0:
        issues.append(
            "No default master found (is_default=True). "
            "Set is_default=True on the master at the default axis location."
        )
    if len(default_masters) > 1:
        names = [m.name for m in default_masters]
        issues.append(f"More than one default master: {names}")

    # Check 4 — master locations cover all axes
    for master in masters:
        missing = axis_tags - set(master.location.keys())
        if missing:
            issues.append(
                f"Master {master.name!r} is missing locations for axes: {sorted(missing)}"
            )

    # Check 5 & 6 — instance locations
    for inst in instances:
        missing = axis_tags - set(inst.location.keys())
        if missing:
            issues.append(
                f"Instance {inst.name!r} is missing locations for axes: {sorted(missing)}"
            )
        for tag, val in inst.location.items():
            ax = axis_map.get(tag)
            if ax and not (ax.minimum <= val <= ax.maximum):
                issues.append(
                    f"Instance {inst.name!r} axis {tag!r} value {val} is outside "
                    f"[{ax.minimum}, {ax.maximum}]."
                )

    # Check 7 — no duplicate master locations
    seen_locations: list[dict[str, float]] = []
    for master in masters:
        loc = {k: master.location.get(k, 0.0) for k in axis_tags}
        if loc in seen_locations:
            issues.append(f"Duplicate master location for {master.name!r}: {loc}")
        else:
            seen_locations.append(loc)

    # Check 8 — no duplicate instance names
    inst_names = [i.name for i in instances]
    seen_names: set = set()
    for n in inst_names:
        if n in seen_names:
            issues.append(f"Duplicate instance name: {n!r}")
        seen_names.add(n)

    return issues


# ---------------------------------------------------------------------------
# Main builder class
# ---------------------------------------------------------------------------


class VariableFontBuilder:
    """High-level builder for OpenType Variable Fonts.

    Orchestrates axes, masters, and named instances, then exports a variable
    TTF using fontTools.varLib.

    Example::

        builder = VariableFontBuilder(family_name="MyFont")
        builder.add_axis(VariationAxis.from_tag("wght"))
        builder.add_master(Master("Regular", "Regular.ufo", {"wght": 400}, is_default=True))
        builder.add_master(Master("Bold",    "Bold.ufo",    {"wght": 700}))
        builder.add_instance(NamedInstance("Regular", {"wght": 400}))
        builder.add_instance(NamedInstance("Bold",    {"wght": 700}))
        builder.export_variable_ttf("MyFont-VF.ttf")
    """

    def __init__(self, family_name: str = "MyVariableFont") -> None:
        """Initialise the builder.

        Args:
            family_name: Font family name embedded in the generated variable font.
        """
        self.family_name = family_name
        self._axes: list[VariationAxis] = []
        self._masters: list[Master] = []
        self._instances: list[NamedInstance] = []

    # ------------------------------------------------------------------
    # Axis management
    # ------------------------------------------------------------------

    def add_axis(self, axis: VariationAxis) -> VariableFontBuilder:
        """Add a variation axis.

        Args:
            axis: A configured :class:`VariationAxis`.

        Returns:
            *self* (for chaining).

        Raises:
            ValueError: If an axis with the same tag already exists.
        """
        existing_tags = {ax.tag for ax in self._axes}
        if axis.tag in existing_tags:
            raise ValueError(f"Axis {axis.tag!r} already added.")
        self._axes.append(axis)
        return self

    def remove_axis(self, tag: str) -> VariableFontBuilder:
        """Remove a variation axis by tag.

        Args:
            tag: Four-character axis tag to remove.

        Returns:
            *self* (for chaining).

        Raises:
            KeyError: If the tag is not found.
        """
        before = len(self._axes)
        self._axes = [ax for ax in self._axes if ax.tag != tag]
        if len(self._axes) == before:
            raise KeyError(f"No axis with tag {tag!r}")
        return self

    @property
    def axes(self) -> list[VariationAxis]:
        """List of currently defined variation axes (read-only copy)."""
        return list(self._axes)

    # ------------------------------------------------------------------
    # Master management
    # ------------------------------------------------------------------

    def add_master(self, master: Master) -> VariableFontBuilder:
        """Add a font master.

        Args:
            master: A configured :class:`Master`.

        Returns:
            *self* (for chaining).
        """
        self._masters.append(master)
        return self

    def remove_master(self, name: str) -> VariableFontBuilder:
        """Remove a master by name.

        Args:
            name: The master name to remove.

        Returns:
            *self* (for chaining).

        Raises:
            KeyError: If no master with *name* is found.
        """
        before = len(self._masters)
        self._masters = [m for m in self._masters if m.name != name]
        if len(self._masters) == before:
            raise KeyError(f"No master named {name!r}")
        return self

    @property
    def masters(self) -> list[Master]:
        """List of currently defined masters (read-only copy)."""
        return list(self._masters)

    # ------------------------------------------------------------------
    # Instance management
    # ------------------------------------------------------------------

    def add_instance(self, instance: NamedInstance) -> VariableFontBuilder:
        """Add a named instance.

        Args:
            instance: A configured :class:`NamedInstance`.

        Returns:
            *self* (for chaining).
        """
        self._instances.append(instance)
        return self

    def remove_instance(self, name: str) -> VariableFontBuilder:
        """Remove a named instance by name.

        Args:
            name: The instance name to remove.

        Returns:
            *self* (for chaining).

        Raises:
            KeyError: If no instance with *name* is found.
        """
        before = len(self._instances)
        self._instances = [i for i in self._instances if i.name != name]
        if len(self._instances) == before:
            raise KeyError(f"No instance named {name!r}")
        return self

    @property
    def instances(self) -> list[NamedInstance]:
        """List of currently defined named instances (read-only copy)."""
        return list(self._instances)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> list[str]:
        """Run OpenType conformance checks.

        Returns:
            List of issue strings.  Empty list = all checks passed.
        """
        return check_opentype_conformance(self._axes, self._masters, self._instances)

    # ------------------------------------------------------------------
    # Design-space export
    # ------------------------------------------------------------------

    def build_design_space(self) -> DesignSpaceDocument:
        """Build and return the :class:`~fontTools.designspaceLib.DesignSpaceDocument`.

        Returns:
            A populated document ready for use with fontTools.

        Raises:
            ImportError: If fontTools is not installed.
        """
        return _build_design_space(self._axes, self._masters, self._instances, self.family_name)

    def save_design_space(self, path: str | Path) -> Path:
        """Write the design space to a ``.designspace`` file.

        Args:
            path: Destination file path (should end in ``.designspace``).

        Returns:
            The resolved output path.
        """
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        doc = self.build_design_space()
        doc.write(str(output))
        return output

    # ------------------------------------------------------------------
    # Variable font export
    # ------------------------------------------------------------------

    def export_variable_ttf(
        self,
        output_path: str | Path,
        *,
        validate: bool = True,
    ) -> Path:
        """Build and export a variable OpenType/TrueType font.

        This method:
        1. Validates the build configuration (when *validate* is True).
        2. Writes a temporary ``.designspace`` file.
        3. Calls ``fontTools.varLib.build`` to compile the variable font.
        4. Writes the result to *output_path*.

        Args:
            output_path: Destination ``.ttf`` file path.
            validate:    Run conformance checks before building.

        Returns:
            The resolved output path.

        Raises:
            ValueError: If *validate* is True and conformance issues are found.
            ImportError: If fontTools is not installed.
            RuntimeError: On build failure.
        """
        if not _FONTTOOLS_AVAILABLE:
            raise ImportError(
                "fontTools is required for variable font export. "
                "Install it with:  pip install fonttools"
            )

        if validate:
            issues = self.validate()
            if issues:
                raise ValueError(
                    "Variable font configuration has conformance issues:\n"
                    + "\n".join(f"  • {i}" for i in issues)
                )

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmp_dir:
            ds_path = Path(tmp_dir) / "build.designspace"
            doc = self.build_design_space()
            doc.write(str(ds_path))

            try:
                vf, _, _ = _varlib_build(str(ds_path))
                vf.save(str(output))
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(f"varLib build failed: {exc}") from exc

        return output

    # ------------------------------------------------------------------
    # Preview / interpolation utilities
    # ------------------------------------------------------------------

    def preview_location(self, location: dict[str, float]) -> dict[str, dict]:
        """Preview interpolation at a given design-space location.

        Returns information about where the location sits relative to each
        axis and which master is nearest.

        Args:
            location: Mapping of axis tag → design-space value.

        Returns:
            A dict mapping axis tag → ``{"value", "normalised", "nearest_master"}``.
        """
        return preview_interpolation(self._axes, self._masters, location)
