import math

import pytest
import skia

from html2pic.translation.gradients import (
    ColorStop,
    CssConicGradient,
    CssLinearGradient,
    CssRadialGradient,
    GradientError,
    Length,
    is_gradient,
    parse_angle,
    parse_gradient,
    resolve_stop_positions,
)
from html2pic.translation.style_applicators.overflow_applicator import OverflowApplicator
from html2pic.parsing import ShorthandExpander

from .test_translation import apply


def stops_at(*positions):
    return [ColorStop(None, p) for p in positions]


class TestStopFixup:
    def test_defaults_first_and_last(self):
        assert resolve_stop_positions(stops_at(None, None), 100) == [0.0, 1.0]

    def test_even_distribution_of_missing_positions(self):
        assert resolve_stop_positions(stops_at(None, None, None, Length(60, "%")), 100) == pytest.approx([0, 0.2, 0.4, 0.6])

    def test_positions_never_decrease(self):
        assert resolve_stop_positions(stops_at(Length(60, "%"), Length(30, "%")), 100) == [0.6, 0.6]

    def test_px_positions_use_gradient_length(self):
        assert resolve_stop_positions(stops_at(Length(25, "px"), None), 200) == [0.125, 1.0]

    def test_out_of_range_positions_are_kept(self):
        assert resolve_stop_positions(stops_at(Length(-20, "%"), Length(120, "%")), 1) == pytest.approx([-0.2, 1.2])


class TestParseAngle:
    @pytest.mark.parametrize("token, degrees", [("90deg", 90), ("0.25turn", 90), ("100grad", 90), (f"{math.pi}rad", 180), ("0", 0)])
    def test_units(self, token, degrees):
        assert parse_angle(token) == pytest.approx(degrees)

    @pytest.mark.parametrize("token", ["90", "10px", "abc"])
    def test_invalid(self, token):
        assert parse_angle(token) is None


class TestParseGradient:
    def test_is_gradient(self):
        assert is_gradient("Repeating-Radial-Gradient(red, blue)")
        assert not is_gradient("url(a.png)")

    def test_linear_defaults(self):
        g = parse_gradient("linear-gradient(red, blue)")
        assert isinstance(g, CssLinearGradient) and g.angle == 180 and not g.repeating
        assert [s.position for s in g.stops] == [None, None]

    @pytest.mark.parametrize("direction, angle", [("to top", 0), ("to right", 90), ("to left", 270), ("45deg", 45), ("0.5turn", 180)])
    def test_linear_directions(self, direction, angle):
        assert parse_gradient(f"linear-gradient({direction}, red, blue)").angle == pytest.approx(angle)

    @pytest.mark.parametrize("direction, corner", [("to top right", ("top", "right")), ("to left bottom", ("bottom", "left"))])
    def test_linear_corners(self, direction, corner):
        assert parse_gradient(f"linear-gradient({direction}, red, blue)").corner == corner

    def test_double_position_stops_and_functions(self):
        g = parse_gradient("repeating-linear-gradient(45deg, rgb(1, 2, 3) 0 10px, #fff 10px 20px)")
        assert g.repeating
        assert [s.position for s in g.stops] == [Length(0, "px"), Length(10, "px"), Length(10, "px"), Length(20, "px")]
        assert (g.stops[0].color.r, g.stops[0].color.g, g.stops[0].color.b) == (1, 2, 3)

    def test_transparent(self):
        assert parse_gradient("linear-gradient(red, transparent)").stops[1].color.a == 0

    def test_radial_defaults(self):
        g = parse_gradient("radial-gradient(red, blue)")
        assert isinstance(g, CssRadialGradient)
        assert (g.shape, g.extent, g.position) == ("ellipse", "farthest-corner", (Length(50, "%"), Length(50, "%")))

    @pytest.mark.parametrize(
        "config, shape, extent, size",
        [
            ("circle", "circle", "farthest-corner", ()),
            ("closest-side", "ellipse", "closest-side", ()),
            ("circle farthest-side", "circle", "farthest-side", ()),
            ("20px", "circle", "explicit", (Length(20, "px"),)),
            ("20px 50%", "ellipse", "explicit", (Length(20, "px"), Length(50, "%"))),
        ],
    )
    def test_radial_shapes(self, config, shape, extent, size):
        g = parse_gradient(f"radial-gradient({config}, red, blue)")
        assert (g.shape, g.extent, g.size) == (shape, extent, size)

    @pytest.mark.parametrize(
        "position, expected",
        [
            ("left", (Length(0, "%"), Length(50, "%"))),
            ("top", (Length(50, "%"), Length(0, "%"))),
            ("right bottom", (Length(100, "%"), Length(100, "%"))),
            ("bottom left", (Length(0, "%"), Length(100, "%"))),
            ("10px 30%", (Length(10, "px"), Length(30, "%"))),
        ],
    )
    def test_positions(self, position, expected):
        assert parse_gradient(f"radial-gradient(circle at {position}, red, blue)").position == expected

    def test_conic(self):
        g = parse_gradient("conic-gradient(from 0.25turn at 10% 20%, red 0deg, blue 50%)")
        assert isinstance(g, CssConicGradient)
        assert g.from_angle == pytest.approx(90)
        assert g.position == (Length(10, "%"), Length(20, "%"))
        assert g.stops[0].position == Length(0, "deg")

    @pytest.mark.parametrize(
        "value, message",
        [
            ("linear-gradient(red)", "at least two"),
            ("linear-gradient(sideways, red, blue)", "invalid"),
            ("linear-gradient(red, 50%, blue)", "hints"),
            ("radial-gradient(circle 10px 20px, red, blue)", "single size"),
            ("radial-gradient(ellipse 10px, red, blue)", "circle"),
            ("conic-gradient(from 10px, red, blue)", "invalid"),
            ("linear-gradient(to top, red, notacolor)", "invalid color stop"),
        ],
    )
    def test_errors(self, value, message):
        with pytest.raises(GradientError, match=message):
            parse_gradient(value)


class TestGeometry:
    def test_linear_gradient_line_length(self):
        # CSS: |w sin(a)| + |h cos(a)|; for 90deg on a 200x50 box the line spans the width.
        g = parse_gradient("linear-gradient(90deg, red, blue)")
        assert g.make_shader(skia.Rect.MakeWH(200, 50)) is not None

    def test_corner_direction_is_perpendicular_to_diagonal(self):
        g = parse_gradient("linear-gradient(to top right, red, blue)")
        angle = g.gradient_angle(200, 50)
        direction = (math.sin(math.radians(angle)), -math.cos(math.radians(angle)))
        diagonal = (200, 50)  # top-left to bottom-right
        assert direction[0] * diagonal[0] + direction[1] * diagonal[1] == pytest.approx(0, abs=1e-9)
        assert direction[0] > 0 and direction[1] < 0

    @pytest.mark.parametrize(
        "config, expected",
        [
            # on a 200x100 box, "at 25% 50%" is the point (50, 50)
            ("closest-side at 25% 50%", (50, 50)),
            ("farthest-side at 25% 50%", (150, 50)),
            ("circle closest-side at 25% 50%", (50, 50)),
            ("circle farthest-side at 25% 50%", (150, 150)),
            ("circle farthest-corner", (math.hypot(100, 50),) * 2),
            ("farthest-corner", (100 * math.sqrt(2), 50 * math.sqrt(2))),
            ("30px 50%", (30, 50)),
        ],
    )
    def test_radial_radii(self, config, expected):
        g = parse_gradient(f"radial-gradient({config}, red, blue)")
        bounds = skia.Rect.MakeWH(200, 100)
        from html2pic.translation.gradients import _resolve_point

        cx, cy = _resolve_point(g.position, bounds)
        assert g.radii(bounds, cx, cy) == pytest.approx(expected)


class TestOverflow:
    @pytest.mark.parametrize(
        "value, expected",
        [("hidden", ("hidden", "hidden")), ("hidden visible", ("hidden", "visible")), ("", ("visible", "visible"))],
    )
    def test_shorthand(self, value, expected):
        result = ShorthandExpander().expand_overflow(value)
        assert (result["overflow-x"], result["overflow-y"]) == expected

    @pytest.mark.parametrize("x, y, clips", [("visible", "visible", False), ("hidden", "visible", True), ("auto", "auto", True), ("scroll", "clip", True)])
    def test_applicator(self, x, y, clips):
        b = apply(OverflowApplicator(), **{"overflow-x": x, "overflow-y": y})
        assert (b.called("overflow") == [(("hidden",), {})]) is clips

    def test_single_axis_clip_warns(self, warnings_collector):
        apply(OverflowApplicator(), **{"overflow-x": "clip", "overflow-y": "visible"})
        assert any("single axis" in w["message"] for w in warnings_collector.get_warnings())
