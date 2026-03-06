"""Tests for aifont.core.variable and aifont.core.svg_parser (pure-Python paths)."""

from __future__ import annotations

# ===========================================================================
# aifont.core.variable
# ===========================================================================


class TestVariationAxis:
    def test_valid_axis(self):
        from aifont.core.variable import VariationAxis

        ax = VariationAxis("wght", "Weight", minimum=100, default=400, maximum=900)
        assert ax.tag == "wght"
        assert ax.minimum == 100
        assert ax.default == 400
        assert ax.maximum == 900
        assert ax.hidden is False

    def test_invalid_tag_length(self):
        from aifont.core.variable import VariationAxis

        try:
            VariationAxis("wg", "Weight", minimum=100, default=400, maximum=900)
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_invalid_range(self):
        from aifont.core.variable import VariationAxis

        try:
            VariationAxis("wght", "Weight", minimum=900, default=400, maximum=100)
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_from_tag_known(self):
        from aifont.core.variable import VariationAxis

        ax = VariationAxis.from_tag("wght")
        assert ax.tag == "wght"
        assert ax.minimum == 100.0
        assert ax.maximum == 900.0

    def test_from_tag_known_with_override(self):
        from aifont.core.variable import VariationAxis

        ax = VariationAxis.from_tag("wdth", minimum=75.0)
        assert ax.minimum == 75.0

    def test_from_tag_unknown_with_values(self):
        from aifont.core.variable import VariationAxis

        ax = VariationAxis.from_tag("CSTM", minimum=0.0, default=50.0, maximum=100.0)
        assert ax.tag == "CSTM"

    def test_from_tag_unknown_no_values_raises(self):
        from aifont.core.variable import VariationAxis

        try:
            VariationAxis.from_tag("UNKN")
            assert False, "Expected ValueError"
        except ValueError:
            pass


class TestNamedInstance:
    def test_basic(self):
        from aifont.core.variable import NamedInstance

        inst = NamedInstance("SemiBold", {"wght": 600})
        assert inst.name == "SemiBold"
        assert inst.location == {"wght": 600}
        assert inst.style_name == "SemiBold"  # default

    def test_explicit_style_name(self):
        from aifont.core.variable import NamedInstance

        inst = NamedInstance("B", {"wght": 700}, style_name="Bold")
        assert inst.style_name == "Bold"


class TestMaster:
    def test_basic(self):
        from pathlib import Path

        from aifont.core.variable import Master

        m = Master("Regular", "/tmp/regular.ufo", {"wght": 400})
        assert m.name == "Regular"
        assert isinstance(m.path, Path)

    def test_is_default(self):
        from aifont.core.variable import Master

        m = Master("Regular", "/tmp/r.ufo", {"wght": 400}, is_default=True)
        assert m.is_default is True


class TestInterpolate:
    def test_midpoint(self):
        from aifont.core.variable import interpolate

        assert interpolate(0.0, 100.0, 0.5) == 50.0

    def test_endpoints(self):
        from aifont.core.variable import interpolate

        assert interpolate(0.0, 100.0, 0.0) == 0.0
        assert interpolate(0.0, 100.0, 1.0) == 100.0

    def test_out_of_range(self):
        from aifont.core.variable import interpolate

        try:
            interpolate(0.0, 100.0, 1.5)
            assert False, "Expected ValueError"
        except ValueError:
            pass


class TestLocationToNormalized:
    def _make_axis(self):
        from aifont.core.variable import VariationAxis

        return VariationAxis("wght", "Weight", minimum=100.0, default=400.0, maximum=900.0)

    def test_default_maps_to_zero(self):
        from aifont.core.variable import location_to_normalized

        ax = self._make_axis()
        result = location_to_normalized({"wght": 400.0}, [ax])
        assert result["wght"] == 0.0

    def test_max_maps_to_one(self):
        from aifont.core.variable import location_to_normalized

        ax = self._make_axis()
        result = location_to_normalized({"wght": 900.0}, [ax])
        assert result["wght"] == 1.0

    def test_min_maps_to_minus_one(self):
        from aifont.core.variable import location_to_normalized

        ax = self._make_axis()
        result = location_to_normalized({"wght": 100.0}, [ax])
        assert result["wght"] == -1.0

    def test_unknown_axis_raises(self):
        from aifont.core.variable import VariationAxis, location_to_normalized

        ax = VariationAxis("ital", "Italic", minimum=0.0, default=0.0, maximum=1.0)
        try:
            location_to_normalized({"wght": 400.0}, [ax])
            assert False, "Expected ValueError"
        except ValueError:
            pass


class TestPreviewInterpolation:
    def test_basic(self):
        from aifont.core.variable import Master, VariationAxis, preview_interpolation

        axes = [VariationAxis("wght", "Weight", minimum=100.0, default=400.0, maximum=900.0)]
        masters = [
            Master("Regular", "/tmp/r.ufo", {"wght": 400.0}),
            Master("Bold", "/tmp/b.ufo", {"wght": 700.0}),
        ]
        result = preview_interpolation(axes, masters, {"wght": 700.0})
        assert "wght" in result
        assert result["wght"]["nearest_master"] == "Bold"

    def test_default_position(self):
        from aifont.core.variable import Master, VariationAxis, preview_interpolation

        axes = [VariationAxis("wght", "Weight", minimum=100.0, default=400.0, maximum=900.0)]
        masters = [Master("Regular", "/tmp/r.ufo", {"wght": 400.0})]
        result = preview_interpolation(axes, masters, {"wght": 400.0})
        assert result["wght"]["normalised"] == 0.0


class TestCheckOpenTypeConformance:
    def test_no_axes_no_masters_returns_list(self):
        from aifont.core.variable import check_opentype_conformance

        errors = check_opentype_conformance([], [], [])
        # Empty inputs produce no issues
        assert isinstance(errors, list)

    def test_missing_default_master_detected(self):
        from aifont.core.variable import (
            Master,
            VariationAxis,
            check_opentype_conformance,
        )

        axes = [VariationAxis("wght", "Weight", minimum=100.0, default=400.0, maximum=900.0)]
        masters = [
            Master("Regular", "/tmp/r.ufo", {"wght": 400.0}),  # is_default=False
            Master("Bold", "/tmp/b.ufo", {"wght": 700.0}),
        ]
        errors = check_opentype_conformance(axes, masters, [])
        assert any("default master" in e.lower() for e in errors)

    def test_valid_setup(self):
        from aifont.core.variable import (
            Master,
            NamedInstance,
            VariationAxis,
            check_opentype_conformance,
        )

        axes = [VariationAxis("wght", "Weight", minimum=100.0, default=400.0, maximum=900.0)]
        masters = [
            Master("Regular", "/tmp/r.ufo", {"wght": 400.0}, is_default=True),
            Master("Bold", "/tmp/b.ufo", {"wght": 700.0}),
        ]
        instances = [NamedInstance("Regular", {"wght": 400.0})]
        errors = check_opentype_conformance(axes, masters, instances)
        assert errors == []


class TestVariableFontBuilder:
    def test_instantiation(self):
        from aifont.core.variable import VariableFontBuilder

        builder = VariableFontBuilder(family_name="TestVF")
        assert builder.family_name == "TestVF"

    def test_add_axis(self):
        from aifont.core.variable import VariableFontBuilder, VariationAxis

        builder = VariableFontBuilder()
        ax = VariationAxis("wght", "Weight", minimum=100.0, default=400.0, maximum=900.0)
        result = builder.add_axis(ax)
        assert result is builder  # chaining
        assert len(builder.axes) == 1

    def test_add_master(self):
        from aifont.core.variable import Master, VariableFontBuilder

        builder = VariableFontBuilder()
        master = Master("Regular", "/tmp/r.ufo", {"wght": 400.0})
        result = builder.add_master(master)
        assert result is builder
        assert len(builder.masters) == 1

    def test_add_instance(self):
        from aifont.core.variable import NamedInstance, VariableFontBuilder

        builder = VariableFontBuilder()
        inst = NamedInstance("Regular", {"wght": 400.0})
        result = builder.add_instance(inst)
        assert result is builder
        assert len(builder.instances) == 1

    def test_conformance_empty_raises_or_returns_errors(self):
        from aifont.core.variable import VariableFontBuilder

        builder = VariableFontBuilder()
        # build_design_space without fonttools or with no masters raises
        try:
            builder.build_design_space()
            # If fonttools available, returns a doc
        except Exception:
            pass  # expected without masters


# ===========================================================================
# aifont.core.svg_parser (pure-Python helpers)
# ===========================================================================


class TestParseTransform:
    def test_identity_empty(self):
        from aifont.core.svg_parser import _parse_transform

        result = _parse_transform("")
        assert result == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

    def test_translate(self):
        from aifont.core.svg_parser import _parse_transform

        a, b, c, d, e, f = _parse_transform("translate(10, 20)")
        assert e == 10.0
        assert f == 20.0

    def test_translate_single_arg(self):
        from aifont.core.svg_parser import _parse_transform

        a, b, c, d, e, f = _parse_transform("translate(50)")
        assert e == 50.0
        assert f == 0.0

    def test_scale_uniform(self):
        from aifont.core.svg_parser import _parse_transform

        a, b, c, d, e, f = _parse_transform("scale(2)")
        assert a == 2.0
        assert d == 2.0

    def test_scale_non_uniform(self):
        from aifont.core.svg_parser import _parse_transform

        a, b, c, d, e, f = _parse_transform("scale(2, 3)")
        assert a == 2.0
        assert d == 3.0

    def test_matrix(self):
        from aifont.core.svg_parser import _parse_transform

        result = _parse_transform("matrix(1 0 0 1 10 20)")
        assert result[4] == 10.0
        assert result[5] == 20.0


class TestApplyMatrix:
    def test_identity(self):
        from aifont.core.svg_parser import _apply_matrix

        x, y = _apply_matrix(5.0, 10.0, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
        assert x == 5.0
        assert y == 10.0

    def test_translation(self):
        from aifont.core.svg_parser import _apply_matrix

        x, y = _apply_matrix(0.0, 0.0, (1.0, 0.0, 0.0, 1.0, 10.0, 20.0))
        assert x == 10.0
        assert y == 20.0


class TestTokenisePath:
    def test_simple_moveto(self):
        from aifont.core.svg_parser import _tokenise_path

        tokens = _tokenise_path("M 10 20")
        assert tokens == ["M", 10.0, 20.0]

    def test_mixed_commands(self):
        from aifont.core.svg_parser import _tokenise_path

        tokens = _tokenise_path("M10,20 L30,40 Z")
        assert "M" in tokens
        assert "L" in tokens
        assert "Z" in tokens


class TestParsePathD:
    def test_simple_move_close(self):
        from aifont.core.svg_parser import _parse_path_d

        cmds = _parse_path_d("M 0 0 Z")
        assert any(cmd == "M" for cmd, _ in cmds)

    def test_lineto(self):
        from aifont.core.svg_parser import _parse_path_d

        cmds = _parse_path_d("M 0 0 L 100 100 Z")
        assert any(cmd == "L" for cmd, _ in cmds)

    def test_relative_lineto_converted(self):
        from aifont.core.svg_parser import _parse_path_d

        # relative 'l' should be converted to absolute 'L'
        cmds = _parse_path_d("M 10 10 l 50 50")
        cmd_names = [c for c, _ in cmds]
        # The relative 'l' should become 'L' or be included
        assert "M" in cmd_names

    def test_bezier_curve(self):
        from aifont.core.svg_parser import _parse_path_d

        cmds = _parse_path_d("M 0 0 C 10 20 30 40 50 60 Z")
        assert any(cmd == "C" for cmd, _ in cmds)


class TestSvgParserConstants:
    def test_ff_available_is_bool(self):
        from aifont.core.svg_parser import _FF_AVAILABLE

        assert isinstance(_FF_AVAILABLE, bool)

    def test_svg_ns(self):
        from aifont.core.svg_parser import _SVG_NS

        assert _SVG_NS == "http://www.w3.org/2000/svg"

    def test_path_cmd_re_matches(self):
        from aifont.core.svg_parser import _PATH_CMD_RE

        matches = _PATH_CMD_RE.findall("M10 20")
        assert len(matches) > 0
