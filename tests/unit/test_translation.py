import math

import pytest
from pictex import Column, Image, Row, Text

from html2pic import Html2Pic
from html2pic.dom import DOMNode, NodeType
from html2pic.styling import DEFAULT_STYLES
from html2pic.translation import ElementFactory, PicTexTranslator
from html2pic.translation.shadow_parser import ShadowParser
from html2pic.translation.style_applicators import (
    BackgroundApplicator,
    BorderApplicator,
    LayoutApplicator,
    PositioningApplicator,
    SizeApplicator,
    SpacingApplicator,
    TransformApplicator,
    TypographyApplicator,
)


class RecordingBuilder:
    """Stand-in for a PicTex builder that records every chained call."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self

        return method

    def called(self, name):
        return [(args, kwargs) for n, args, kwargs in self.calls if n == name]


def apply(applicator, **overrides):
    styles = dict(DEFAULT_STYLES)
    styles.update(overrides)
    builder = RecordingBuilder()
    applicator.apply(builder, styles)
    return builder


class TestSizeApplicator:
    def test_auto_size_is_not_applied(self):
        assert apply(SizeApplicator()).called("size") == []

    @pytest.mark.parametrize(
        "width, height, expected",
        [("100px", "auto", (100.0, None)), ("50%", "20px", ("50%", 20.0)), ("fit-content", "auto", ("fit-content", None))],
    )
    def test_dimensions(self, width, height, expected):
        assert apply(SizeApplicator(), width=width, height=height).called("size") == [(expected, {})]

    def test_constraints(self):
        b = apply(SizeApplicator(), **{"min-width": "10px", "max-width": "50%", "max-height": "2em"})
        assert b.called("min_width") == [((10.0,), {})]
        assert b.called("max_width") == [(("50%",), {})]
        assert b.called("max_height") == [((32.0,), {})]
        assert b.called("min_height") == []

    @pytest.mark.parametrize("value, ratio", [("16/9", 16 / 9), ("2", 2.0), ("4 / 3", 4 / 3)])
    def test_aspect_ratio(self, value, ratio):
        (args, _), = apply(SizeApplicator(), **{"aspect-ratio": value}).called("aspect_ratio")
        assert math.isclose(args[0], ratio)

    def test_invalid_aspect_ratio_warns(self, warnings_collector):
        assert apply(SizeApplicator(), **{"aspect-ratio": "1/0"}).called("aspect_ratio") == []
        assert len(warnings_collector.get_warnings()) == 1

    def test_flex_item_properties(self):
        b = apply(SizeApplicator(), **{"flex-grow": "2", "flex-shrink": "0", "align-self": "flex-end"})
        assert b.called("flex_grow") == [((2.0,), {})]
        assert b.called("flex_shrink") == [((0.0,), {})]
        assert b.called("align_self") == [(("end",), {})]


class TestSpacingApplicator:
    def test_zero_spacing_is_skipped(self):
        b = apply(SpacingApplicator())
        assert b.called("padding") == [] and b.called("margin") == []

    @pytest.mark.parametrize(
        "values, expected",
        [
            (("5px",) * 4, (5.0,)),
            (("1px", "2px", "1px", "2px"), (1.0, 2.0)),
            (("1px", "2px", "3px", "4px"), (1.0, 2.0, 3.0, 4.0)),
        ],
    )
    def test_padding_collapses_to_shortest_form(self, values, expected):
        sides = dict(zip(("padding-top", "padding-right", "padding-bottom", "padding-left"), values))
        builder = RecordingBuilder()
        styles = dict(DEFAULT_STYLES, **sides)
        # SpacingApplicator calls the bound method it reads off the builder.
        SpacingApplicator().apply(builder, styles)
        assert builder.called("padding") == [(expected, {})]


class TestPercentSpacing:
    def test_percent_padding_warns_instead_of_silently_dropping(self, warnings_collector):
        apply(SpacingApplicator(), **{"padding-top": "10%"})
        assert any("padding" in w["message"] for w in warnings_collector.get_warnings())

    def test_percent_gap_warns(self, warnings_collector):
        apply(LayoutApplicator(), gap="5%")
        assert any("gap" in w["message"] for w in warnings_collector.get_warnings())


class TestBorderApplicator:
    def test_no_border_by_default(self):
        b = apply(BorderApplicator())
        assert b.called("border") == [] and b.called("border_radius") == []

    def test_border(self):
        (args, _), = apply(BorderApplicator(), **{"border-width": "2px", "border-style": "dashed", "border-color": "red"}).called("border")
        assert args[0] == 2.0
        assert args[2].name == "DASHED"

    def test_uniform_radius_from_shorthand(self):
        assert apply(BorderApplicator(), **{"border-radius": "8px"}).called("border_radius") == [((8.0,), {})]

    def test_percentage_radius_is_passed_through(self):
        assert apply(BorderApplicator(), **{"border-radius": "50%"}).called("border_radius") == [(("50%",), {})]

    def test_mixed_corner_units(self):
        b = apply(BorderApplicator(), **{"border-top-left-radius": "50%", "border-top-right-radius": "4px"})
        assert b.called("border_radius") == [(("50%", 4.0, 0, 0), {})]

    def test_individual_corners(self):
        b = apply(BorderApplicator(), **{"border-top-left-radius": "4px", "border-bottom-right-radius": "2px"})
        assert b.called("border_radius") == [((4.0, 0, 2.0, 0), {})]


class TestBackgroundApplicator:
    def test_transparent_is_skipped(self):
        assert apply(BackgroundApplicator()).called("background_color") == []

    def test_solid_color(self):
        (args, _), = apply(BackgroundApplicator(), **{"background-color": "#ff0000"}).called("background_color")
        assert type(args[0]).__name__ == "SolidColor"

    def test_url_image(self):
        b = apply(BackgroundApplicator(), **{"background-image": "url('bg.png')", "background-size": "contain"})
        assert b.called("background_image") == [(("bg.png", "contain"), {})]

    def test_linear_gradient(self):
        (args, _), = apply(BackgroundApplicator(), **{"background-image": "linear-gradient(to right, red, blue)"}).called("background_color")
        assert type(args[0]).__name__ == "LinearGradient"

    @pytest.mark.parametrize(
        "angle, start, end",
        [("180deg", (0.5, 0.0), (0.5, 1.0)), ("90deg", (0.0, 0.5), (1.0, 0.5)), ("0deg", (0.5, 1.0), (0.5, 0.0))],
    )
    def test_angle_to_points(self, angle, start, end):
        got_start, got_end = BackgroundApplicator()._angle_to_points(angle)
        assert got_start == pytest.approx(start, abs=1e-9)
        assert got_end == pytest.approx(end, abs=1e-9)

    @pytest.mark.parametrize(
        "stop, index, total, expected",
        [("red 25%", 0, 3, ("red", 0.25)), ("red", 1, 3, ("red", 0.5)), ("rgb(1, 2, 3) 100%", 0, 2, ("rgb(1, 2, 3)", 1.0))],
    )
    def test_color_stops(self, stop, index, total, expected):
        assert BackgroundApplicator()._parse_color_stop(stop, index, total) == expected

    def test_gradient_with_single_color_is_ignored(self):
        assert apply(BackgroundApplicator(), **{"background-image": "linear-gradient(red)"}).called("background_color") == []


class TestLayoutApplicator:
    def test_defaults(self):
        b = apply(LayoutApplicator())
        assert b.called("justify_content") == [(("start",), {})]
        assert b.called("align_items") == [(("stretch",), {})]
        assert b.called("gap") == [] and b.called("flex_wrap") == []

    def test_values(self):
        b = apply(LayoutApplicator(), gap="12px", **{"justify-content": "space-between", "align-items": "flex-end", "flex-wrap": "wrap"})
        assert b.called("gap") == [((12.0,), {})]
        assert b.called("justify_content") == [(("space-between",), {})]
        assert b.called("align_items") == [(("end",), {})]
        assert b.called("flex_wrap") == [(("wrap",), {})]


class TestPositioningApplicator:
    def test_static_is_skipped(self):
        assert apply(PositioningApplicator(), top="10px").calls == []

    @pytest.mark.parametrize("position, method", [("absolute", "absolute_position"), ("relative", "relative_position"), ("fixed", "fixed_position")])
    def test_positions(self, position, method):
        b = apply(PositioningApplicator(), position=position, top="10px", left="50%")
        assert b.called(method) == [((), {"top": 10.0, "left": "50%"})]

    def test_no_insets_is_skipped(self):
        assert apply(PositioningApplicator(), position="absolute").calls == []


class TestTransformApplicator:
    @pytest.mark.parametrize(
        "transform, expected",
        [
            ("translate(10px, 20px)", {"x": "10.0", "y": "20.0"}),
            ("translate(-50%, -50%)", {"x": "-50%", "y": "-50%"}),
            ("translateX(5px)", {"x": "5.0"}),
            ("translateY(1em)", {"y": "16.0"}),
        ],
    )
    def test_translate(self, transform, expected):
        assert apply(TransformApplicator(), transform=transform).called("translate") == [((), expected)]

    def test_unsupported_transform_warns(self, warnings_collector):
        assert apply(TransformApplicator(), transform="rotate(45deg)").called("translate") == []
        assert any("rotate" in w["message"] for w in warnings_collector.get_warnings())


class TestTypographyApplicator:
    def test_font_family_with_fallbacks(self):
        b = apply(TypographyApplicator(), **{"font-family": "'Inter', Arial, sans-serif"})
        assert b.called("font_family") == [(("Inter",), {})]
        assert b.called("font_fallbacks") == [(("Arial", "sans-serif"), {})]

    def test_basic_properties(self):
        b = apply(
            TypographyApplicator(),
            **{"font-size": "24px", "font-weight": "bold", "font-style": "italic", "text-align": "center", "line-height": "1.5", "text-wrap": "nowrap"},
        )
        assert b.called("font_size") == [((24.0,), {})]
        assert b.called("font_weight") == [((700,), {})]
        assert b.called("font_style") == [(("italic",), {})]
        assert b.called("text_align") == [(("center",), {})]
        assert b.called("line_height") == [((1.5,), {})]
        assert b.called("text_wrap") == [(("nowrap",), {})]

    def test_text_shadow(self):
        b = apply(TypographyApplicator(), **{"text-shadow": "1px 1px 2px black"})
        (args, _), = b.called("text_shadows")
        assert len(args) == 1


class TestShadowParser:
    def test_multiple_shadows_with_rgba(self):
        shadows = ShadowParser().parse_shadows("0 4px 6px rgba(0, 0, 0, 0.1), 2px 2px red")
        assert len(shadows) == 2
        assert shadows[0].offset == (0.0, 4.0)
        assert shadows[0].blur_radius == 6.0
        assert shadows[1].offset == (2.0, 2.0)
        assert shadows[1].blur_radius == 0.0

    def test_negative_offsets(self):
        (shadow,) = ShadowParser().parse_shadows("-3px -4px 5px blue")
        assert shadow.offset == (-3.0, -4.0)

    def test_invalid_color_is_dropped(self):
        assert ShadowParser().parse_shadows("1px 1px notacolor") == []


class TestElementFactory:
    def node(self, tag, **styles):
        return DOMNode(node_type=NodeType.ELEMENT, tag=tag, computed_styles=dict(DEFAULT_STYLES, **styles))

    def test_block_is_column(self):
        assert isinstance(ElementFactory().create(self.node("div")), Column)

    def test_inline_tag_is_row(self):
        assert isinstance(ElementFactory().create(self.node("span")), Row)

    @pytest.mark.parametrize("direction, cls", [("row", Row), ("row-reverse", Row), ("column", Column), ("column-reverse", Column)])
    def test_flex_direction(self, direction, cls):
        node = self.node("div", display="flex", **{"flex-direction": direction})
        assert isinstance(ElementFactory().create(node), cls)

    def test_img(self):
        node = self.node("img")
        node.attributes = {"src": "x.png"}
        assert isinstance(ElementFactory().create(node), Image)

    def test_img_without_src_is_skipped(self, warnings_collector):
        assert ElementFactory().create(self.node("img")) is None
        assert len(warnings_collector.get_warnings()) == 1


class TestTranslator:
    def translate(self, html, css=""):
        h = Html2Pic(html, css)
        return PicTexTranslator().translate(h.styled_tree, h.font_registry)

    def test_returns_canvas_and_root(self):
        canvas, root = self.translate("<p>x</p>")
        assert type(canvas).__name__ == "Canvas"
        assert isinstance(root, Column)

    def test_display_none_subtree_is_dropped(self):
        _, root = self.translate('<div class="h"><p>x</p></div>', ".h { display: none }")
        assert root._children == []

    def test_text_children_become_text_elements(self):
        _, root = self.translate("<p>hello</p>")
        (p,) = root._children
        (text,) = p._children
        assert isinstance(text, Text)
