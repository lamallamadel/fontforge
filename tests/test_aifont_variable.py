"""Tests for aifont.core.variable — Variable Font support.

Tests are designed to run without an installed font or UFO source so that
they can run in CI without real font data.  The export_variable_ttf path is
tested only when real UFO masters are present (skipped otherwise).
"""

from __future__ import annotations

import pytest

from aifont.core.variable import (
    Master,
    NamedInstance,
    VariationAxis,
    VariableFontBuilder,
    check_opentype_conformance,
    interpolate,
    location_to_normalized,
    preview_interpolation,
    STANDARD_AXES,
    AXIS_RANGES,
)


# ---------------------------------------------------------------------------
# VariationAxis
# ---------------------------------------------------------------------------


class TestVariationAxis:
    def test_create_basic(self):
        ax = VariationAxis("wght", "Weight", 100, 400, 900)
        assert ax.tag == "wght"
        assert ax.name == "Weight"
        assert ax.minimum == 100
        assert ax.default == 400
        assert ax.maximum == 900
        assert ax.hidden is False

    def test_hidden_flag(self):
        ax = VariationAxis("ital", "Italic", 0, 0, 1, hidden=True)
        assert ax.hidden is True

    def test_invalid_tag_length(self):
        with pytest.raises(ValueError, match="4 characters"):
            VariationAxis("wg", "Weight", 100, 400, 900)

    def test_invalid_range_default_below_min(self):
        with pytest.raises(ValueError, match="must hold"):
            VariationAxis("wght", "Weight", 400, 100, 900)

    def test_invalid_range_default_above_max(self):
        with pytest.raises(ValueError, match="must hold"):
            VariationAxis("wght", "Weight", 100, 1000, 900)

    def test_from_tag_wght(self):
        ax = VariationAxis.from_tag("wght")
        assert ax.tag == "wght"
        assert ax.minimum == 100
        assert ax.default == 400
        assert ax.maximum == 900

    def test_from_tag_wdth(self):
        ax = VariationAxis.from_tag("wdth")
        assert ax.tag == "wdth"
        assert ax.minimum == 50
        assert ax.default == 100
        assert ax.maximum == 200

    def test_from_tag_ital(self):
        ax = VariationAxis.from_tag("ital")
        assert ax.minimum == 0
        assert ax.maximum == 1

    def test_from_tag_opsz(self):
        ax = VariationAxis.from_tag("opsz")
        assert ax.default == 12

    def test_from_tag_with_overrides(self):
        ax = VariationAxis.from_tag("wght", minimum=200, default=500, maximum=800)
        assert ax.minimum == 200
        assert ax.default == 500
        assert ax.maximum == 800

    def test_from_tag_unknown_no_overrides_raises(self):
        with pytest.raises(ValueError, match="Unknown axis tag"):
            VariationAxis.from_tag("CUST")

    def test_from_tag_unknown_with_overrides(self):
        ax = VariationAxis.from_tag(
            "CUST", minimum=0, default=50, maximum=100, name="Custom"
        )
        assert ax.tag == "CUST"
        assert ax.name == "Custom"


# ---------------------------------------------------------------------------
# NamedInstance
# ---------------------------------------------------------------------------


class TestNamedInstance:
    def test_create(self):
        inst = NamedInstance("SemiBold", {"wght": 600})
        assert inst.name == "SemiBold"
        assert inst.location == {"wght": 600}
        assert inst.style_name == "SemiBold"  # defaults to name

    def test_explicit_style_name(self):
        inst = NamedInstance("SemiBold", {"wght": 600}, style_name="Semi Bold")
        assert inst.style_name == "Semi Bold"

    def test_family_name(self):
        inst = NamedInstance("Bold", {"wght": 700}, family_name="MyFont")
        assert inst.family_name == "MyFont"

    def test_postscript_name(self):
        inst = NamedInstance("Bold", {"wght": 700}, postscript_name="MyFont-Bold")
        assert inst.postscript_name == "MyFont-Bold"


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------


class TestMaster:
    def test_create(self):
        m = Master("Regular", "/tmp/Regular.ufo", {"wght": 400}, is_default=True)
        assert m.name == "Regular"
        assert m.is_default is True

    def test_path_is_pathlib(self):
        from pathlib import Path
        m = Master("Bold", "/tmp/Bold.ufo", {"wght": 700})
        assert isinstance(m.path, Path)

    def test_default_is_false(self):
        m = Master("Bold", "/tmp/Bold.ufo", {"wght": 700})
        assert m.is_default is False


# ---------------------------------------------------------------------------
# interpolate()
# ---------------------------------------------------------------------------


class TestInterpolate:
    def test_zero(self):
        assert interpolate(100, 900, 0.0) == 100.0

    def test_one(self):
        assert interpolate(100, 900, 1.0) == 900.0

    def test_midpoint(self):
        assert interpolate(100, 900, 0.5) == pytest.approx(500.0)

    def test_quarter(self):
        assert interpolate(0, 400, 0.25) == pytest.approx(100.0)

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError, match="Interpolation factor"):
            interpolate(0, 100, 1.5)

    def test_negative_t_raises(self):
        with pytest.raises(ValueError, match="Interpolation factor"):
            interpolate(0, 100, -0.1)


# ---------------------------------------------------------------------------
# location_to_normalized()
# ---------------------------------------------------------------------------


class TestLocationToNormalized:
    def _axes(self):
        return [VariationAxis.from_tag("wght")]

    def test_default_is_zero(self):
        norm = location_to_normalized({"wght": 400}, self._axes())
        assert norm["wght"] == pytest.approx(0.0)

    def test_maximum_is_plus_one(self):
        norm = location_to_normalized({"wght": 900}, self._axes())
        assert norm["wght"] == pytest.approx(1.0)

    def test_minimum_is_minus_one(self):
        norm = location_to_normalized({"wght": 100}, self._axes())
        assert norm["wght"] == pytest.approx(-1.0)

    def test_midpoint_above_default(self):
        # wght 650 is halfway between default 400 and max 900 → 0.5
        norm = location_to_normalized({"wght": 650}, self._axes())
        assert norm["wght"] == pytest.approx(0.5)

    def test_midpoint_below_default(self):
        # wght 250 is halfway between min 100 and default 400 → -0.5
        norm = location_to_normalized({"wght": 250}, self._axes())
        assert norm["wght"] == pytest.approx(-0.5)

    def test_unknown_axis_raises(self):
        with pytest.raises(ValueError, match="Unknown axis tag"):
            location_to_normalized({"XXXX": 400}, self._axes())


# ---------------------------------------------------------------------------
# preview_interpolation()
# ---------------------------------------------------------------------------


class TestPreviewInterpolation:
    def _axes_masters(self):
        axes = [VariationAxis.from_tag("wght")]
        masters = [
            Master("Regular", "/tmp/R.ufo", {"wght": 400}, is_default=True),
            Master("Bold",    "/tmp/B.ufo", {"wght": 700}),
        ]
        return axes, masters

    def test_returns_axis_info(self):
        axes, masters = self._axes_masters()
        result = preview_interpolation(axes, masters, {"wght": 400})
        assert "wght" in result
        assert result["wght"]["value"] == 400
        assert result["wght"]["normalised"] == pytest.approx(0.0)
        assert result["wght"]["nearest_master"] == "Regular"

    def test_nearest_master_bold(self):
        axes, masters = self._axes_masters()
        result = preview_interpolation(axes, masters, {"wght": 700})
        assert result["wght"]["nearest_master"] == "Bold"

    def test_between_masters(self):
        axes, masters = self._axes_masters()
        result = preview_interpolation(axes, masters, {"wght": 500})
        # 500 is closer to 400 than 700 (diff: 100 vs 200)
        assert result["wght"]["nearest_master"] == "Regular"

    def test_unknown_axis_ignored(self):
        axes, masters = self._axes_masters()
        # "ital" not in axes, so it's silently ignored
        result = preview_interpolation(axes, masters, {"ital": 1})
        assert result == {}


# ---------------------------------------------------------------------------
# check_opentype_conformance()
# ---------------------------------------------------------------------------


class TestConformanceChecks:
    def _ok_setup(self):
        axes = [VariationAxis.from_tag("wght")]
        masters = [
            Master("Regular", "/tmp/R.ufo", {"wght": 400}, is_default=True),
            Master("Bold",    "/tmp/B.ufo", {"wght": 700}),
        ]
        instances = [
            NamedInstance("Regular", {"wght": 400}),
            NamedInstance("Bold",    {"wght": 700}),
        ]
        return axes, masters, instances

    def test_clean_setup_has_no_issues(self):
        axes, masters, instances = self._ok_setup()
        issues = check_opentype_conformance(axes, masters, instances)
        assert issues == []

    def test_missing_default_master(self):
        axes = [VariationAxis.from_tag("wght")]
        masters = [
            Master("Regular", "/tmp/R.ufo", {"wght": 400}),
            Master("Bold",    "/tmp/B.ufo", {"wght": 700}),
        ]
        issues = check_opentype_conformance(axes, masters, [])
        assert any("default master" in i.lower() for i in issues)

    def test_multiple_default_masters(self):
        axes = [VariationAxis.from_tag("wght")]
        masters = [
            Master("Regular", "/tmp/R.ufo", {"wght": 400}, is_default=True),
            Master("Bold",    "/tmp/B.ufo", {"wght": 700}, is_default=True),
        ]
        issues = check_opentype_conformance(axes, masters, [])
        assert any("More than one default" in i for i in issues)

    def test_master_missing_axis_location(self):
        axes = [VariationAxis.from_tag("wght"), VariationAxis.from_tag("wdth")]
        masters = [
            Master("Regular", "/tmp/R.ufo", {"wght": 400}, is_default=True),
        ]
        issues = check_opentype_conformance(axes, masters, [])
        assert any("wdth" in i for i in issues)

    def test_instance_out_of_bounds(self):
        axes, masters, _ = self._ok_setup()
        instances = [NamedInstance("Ultra", {"wght": 1200})]
        issues = check_opentype_conformance(axes, masters, instances)
        assert any("outside" in i for i in issues)

    def test_duplicate_master_location(self):
        axes = [VariationAxis.from_tag("wght")]
        masters = [
            Master("Regular",  "/tmp/R.ufo",  {"wght": 400}, is_default=True),
            Master("Regular2", "/tmp/R2.ufo", {"wght": 400}),
        ]
        issues = check_opentype_conformance(axes, masters, [])
        assert any("Duplicate master location" in i for i in issues)

    def test_duplicate_instance_name(self):
        axes, masters, _ = self._ok_setup()
        instances = [
            NamedInstance("Bold", {"wght": 700}),
            NamedInstance("Bold", {"wght": 700}),
        ]
        issues = check_opentype_conformance(axes, masters, instances)
        assert any("Duplicate instance name" in i for i in issues)


# ---------------------------------------------------------------------------
# VariableFontBuilder
# ---------------------------------------------------------------------------


class TestVariableFontBuilder:
    def _builder(self):
        b = VariableFontBuilder(family_name="TestFont")
        b.add_axis(VariationAxis.from_tag("wght"))
        b.add_master(Master("Regular", "/tmp/R.ufo", {"wght": 400}, is_default=True))
        b.add_master(Master("Bold",    "/tmp/B.ufo", {"wght": 700}))
        b.add_instance(NamedInstance("Regular", {"wght": 400}))
        b.add_instance(NamedInstance("Bold",    {"wght": 700}))
        return b

    def test_family_name(self):
        b = VariableFontBuilder("MyFont")
        assert b.family_name == "MyFont"

    def test_add_axis(self):
        b = VariableFontBuilder()
        b.add_axis(VariationAxis.from_tag("wght"))
        assert len(b.axes) == 1

    def test_add_duplicate_axis_raises(self):
        b = VariableFontBuilder()
        b.add_axis(VariationAxis.from_tag("wght"))
        with pytest.raises(ValueError, match="already added"):
            b.add_axis(VariationAxis.from_tag("wght"))

    def test_remove_axis(self):
        b = VariableFontBuilder()
        b.add_axis(VariationAxis.from_tag("wght"))
        b.remove_axis("wght")
        assert b.axes == []

    def test_remove_nonexistent_axis_raises(self):
        b = VariableFontBuilder()
        with pytest.raises(KeyError):
            b.remove_axis("wght")

    def test_add_master(self):
        b = VariableFontBuilder()
        b.add_master(Master("Regular", "/tmp/R.ufo", {"wght": 400}))
        assert len(b.masters) == 1

    def test_remove_master(self):
        b = self._builder()
        b.remove_master("Bold")
        assert len(b.masters) == 1
        assert b.masters[0].name == "Regular"

    def test_remove_nonexistent_master_raises(self):
        b = VariableFontBuilder()
        with pytest.raises(KeyError):
            b.remove_master("Ghost")

    def test_add_instance(self):
        b = VariableFontBuilder()
        b.add_instance(NamedInstance("SemiBold", {"wght": 600}))
        assert len(b.instances) == 1

    def test_remove_instance(self):
        b = self._builder()
        b.remove_instance("Regular")
        assert len(b.instances) == 1

    def test_remove_nonexistent_instance_raises(self):
        b = VariableFontBuilder()
        with pytest.raises(KeyError):
            b.remove_instance("Ghost")

    def test_validate_clean(self):
        b = self._builder()
        assert b.validate() == []

    def test_validate_reports_issues(self):
        b = VariableFontBuilder()
        b.add_axis(VariationAxis.from_tag("wght"))
        # No default master
        b.add_master(Master("R", "/tmp/R.ufo", {"wght": 400}))
        b.add_master(Master("B", "/tmp/B.ufo", {"wght": 700}))
        issues = b.validate()
        assert len(issues) > 0

    def test_axes_property_is_copy(self):
        b = self._builder()
        axes = b.axes
        axes.clear()
        assert len(b.axes) == 1  # original unchanged

    def test_masters_property_is_copy(self):
        b = self._builder()
        m = b.masters
        m.clear()
        assert len(b.masters) == 2

    def test_instances_property_is_copy(self):
        b = self._builder()
        i = b.instances
        i.clear()
        assert len(b.instances) == 2

    def test_build_design_space(self):
        """build_design_space() should return a DesignSpaceDocument."""
        from fontTools.designspaceLib import DesignSpaceDocument
        b = self._builder()
        doc = b.build_design_space()
        assert isinstance(doc, DesignSpaceDocument)
        assert len(doc.axes) == 1
        assert doc.axes[0].tag == "wght"
        assert len(doc.sources) == 2
        assert len(doc.instances) == 2

    def test_save_design_space(self, tmp_path):
        b = self._builder()
        out = b.save_design_space(tmp_path / "test.designspace")
        assert out.exists()
        content = out.read_text()
        assert "wght" in content

    def test_preview_location(self):
        b = self._builder()
        result = b.preview_location({"wght": 400})
        assert "wght" in result
        assert result["wght"]["normalised"] == pytest.approx(0.0)

    def test_chaining(self):
        """add_axis / add_master / add_instance support method chaining."""
        b = (
            VariableFontBuilder("ChainFont")
            .add_axis(VariationAxis.from_tag("wght"))
            .add_master(Master("R", "/tmp/R.ufo", {"wght": 400}, is_default=True))
            .add_instance(NamedInstance("R", {"wght": 400}))
        )
        assert b.family_name == "ChainFont"
        assert len(b.axes) == 1
        assert len(b.masters) == 1
        assert len(b.instances) == 1

    def test_export_variable_ttf_raises_on_invalid_config(self, tmp_path):
        """export_variable_ttf raises ValueError when conformance fails."""
        b = VariableFontBuilder()
        b.add_axis(VariationAxis.from_tag("wght"))
        # Two masters, neither is default
        b.add_master(Master("R", "/tmp/R.ufo", {"wght": 400}))
        b.add_master(Master("B", "/tmp/B.ufo", {"wght": 700}))
        with pytest.raises(ValueError, match="conformance issues"):
            b.export_variable_ttf(tmp_path / "out.ttf")

    def test_export_variable_ttf_skipped_without_real_ufos(self, tmp_path):
        """export_variable_ttf with real paths is an integration test.
        This ensures the build path is exercised without real UFOs by
        disabling validation and expecting a RuntimeError from varLib."""
        b = VariableFontBuilder()
        b.add_axis(VariationAxis.from_tag("wght"))
        b.add_master(Master("R", "/nonexistent/R.ufo", {"wght": 400}, is_default=True))
        b.add_master(Master("B", "/nonexistent/B.ufo", {"wght": 700}))
        # validate=False bypasses the conformance step; varLib will fail on
        # missing sources, which surfaces as RuntimeError.
        with pytest.raises((RuntimeError, Exception)):
            b.export_variable_ttf(tmp_path / "out.ttf", validate=False)


# ---------------------------------------------------------------------------
# Multi-axis tests
# ---------------------------------------------------------------------------


class TestMultiAxis:
    def test_two_axes(self):
        b = VariableFontBuilder("MultiAxis")
        b.add_axis(VariationAxis.from_tag("wght"))
        b.add_axis(VariationAxis.from_tag("wdth"))
        b.add_master(Master(
            "Regular", "/tmp/R.ufo",
            {"wght": 400, "wdth": 100},
            is_default=True,
        ))
        b.add_master(Master("Bold",      "/tmp/B.ufo",  {"wght": 700, "wdth": 100}))
        b.add_master(Master("Condensed", "/tmp/C.ufo",  {"wght": 400, "wdth": 75}))
        b.add_instance(NamedInstance("Regular",    {"wght": 400, "wdth": 100}))
        b.add_instance(NamedInstance("Condensed",  {"wght": 400, "wdth": 75}))
        b.add_instance(NamedInstance("BoldCond",   {"wght": 700, "wdth": 75}))

        issues = b.validate()
        assert issues == []

    def test_design_space_two_axes(self):
        from fontTools.designspaceLib import DesignSpaceDocument
        b = VariableFontBuilder("MultiAxis")
        b.add_axis(VariationAxis.from_tag("wght"))
        b.add_axis(VariationAxis.from_tag("wdth"))
        b.add_master(Master("R", "/tmp/R.ufo", {"wght": 400, "wdth": 100}, is_default=True))
        b.add_master(Master("B", "/tmp/B.ufo", {"wght": 700, "wdth": 100}))
        doc = b.build_design_space()
        assert len(doc.axes) == 2

    def test_four_standard_axes(self):
        b = VariableFontBuilder("AllAxes")
        for tag in ("wght", "wdth", "ital", "opsz"):
            b.add_axis(VariationAxis.from_tag(tag))
        b.add_master(Master(
            "Regular", "/tmp/R.ufo",
            {"wght": 400, "wdth": 100, "ital": 0, "opsz": 12},
            is_default=True,
        ))
        assert len(b.axes) == 4

    def test_normalized_location_two_axes(self):
        axes = [VariationAxis.from_tag("wght"), VariationAxis.from_tag("wdth")]
        loc = location_to_normalized({"wght": 900, "wdth": 75}, axes)
        assert loc["wght"] == pytest.approx(1.0)
        assert loc["wdth"] == pytest.approx(-0.5)
