import pytest

from html2pic.dom import DOMNode, NodeType
from html2pic.parsing import CSSRule
from html2pic.styling import CascadeResolver, ColorNormalizer, DEFAULT_STYLES, UnitConverter


class TestUnitConverter:
    @pytest.mark.parametrize("value", ["10px", "auto", "none", "inherit", "initial"])
    def test_passthrough(self, value):
        assert UnitConverter().to_pixels(value) == value

    def test_unitless_number_becomes_pixels(self):
        assert UnitConverter().to_pixels("0") == "0.0px"
        assert UnitConverter().to_pixels("12") == "12.0px"

    def test_em_uses_given_font_size(self):
        assert UnitConverter().to_pixels("2em", font_size="10px") == "20.0px"

    def test_em_defaults_to_base_font_size(self):
        assert UnitConverter(base_font_size=20).to_pixels("1.5em") == "30.0px"

    def test_value_is_normalized(self):
        assert UnitConverter().to_pixels("  10PX ") == "10px"

    def test_non_string_is_stringified(self):
        assert UnitConverter().to_pixels(5) == "5"

    def test_garbage_warns_and_is_returned(self, warnings_collector):
        assert UnitConverter().to_pixels("abc") == "abc"
        assert len(warnings_collector.get_warnings()) == 1


class TestColorNormalizer:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("rgb(255, 0, 0)", "#ff0000ff"),
            ("rgba(0, 128, 255, 0.5)", "#0080ff7f"),
            ("rgba(0,0,0,0)", "transparent"),
            ("rgb(300, -5, 10)", "#ff000aff"),
            ("TRANSPARENT", "transparent"),
            ("  #ABCDEF ", "#abcdef"),
            ("Red", "red"),
        ],
    )
    def test_normalize(self, value, expected):
        assert ColorNormalizer().normalize(value) == expected

    def test_non_string_falls_back_to_black(self):
        assert ColorNormalizer().normalize(None) == "black"

    def test_malformed_rgb_warns_and_falls_back(self, warnings_collector):
        assert ColorNormalizer().normalize("rgb(1, 2)") == "black"
        assert len(warnings_collector.get_warnings()) == 1

    @pytest.mark.parametrize("color", ["red", "#fff", "#ffffff", "#ffffff80", "rgb(1,2,3)", "hsl(1, 2%, 3%)"])
    def test_is_valid(self, color):
        assert ColorNormalizer().is_valid(color)

    @pytest.mark.parametrize("color", ["#ff", "#gggggg", "notacolor"])
    def test_is_invalid(self, color):
        assert not ColorNormalizer().is_valid(color)


class TestCascadeResolver:
    def node(self, tag="div", **attrs):
        return DOMNode(node_type=NodeType.ELEMENT, tag=tag, attributes=attrs)

    @pytest.mark.parametrize(
        "selector, matches",
        [("*", True), ("div", True), ("p", False), (".a", True), (".b", True), (".c", False), ("#x", True), ("#y", False)],
    )
    def test_simple_selectors(self, selector, matches):
        node = self.node(**{"class": "a b", "id": "x"})
        rule = CSSRule(selector=selector, declarations={})
        assert (CascadeResolver().find_matching_rules(node, [rule]) == [rule]) is matches

    def test_text_nodes_never_match(self):
        text = DOMNode(node_type=NodeType.TEXT, text_content="hi")
        assert CascadeResolver().find_matching_rules(text, [CSSRule("*", {})]) == []


class TestStyleEngine:
    def test_defaults_are_applied(self, computed):
        styles = computed("<div></div>")
        for prop in ("display", "flex-direction", "position", "background-image", "box-shadow"):
            assert styles[prop] == DEFAULT_STYLES[prop]

    def test_higher_specificity_wins_regardless_of_order(self, computed):
        css = "#x { color: red } .a { color: green } div { color: blue }"
        assert computed('<div id="x" class="a"></div>', css)["color"] == "red"

    def test_source_order_breaks_ties(self, computed):
        css = ".a { color: red } .b { color: green }"
        assert computed('<div class="a b"></div>', css)["color"] == "green"

    def test_inherited_properties_flow_to_children(self, computed):
        css = "div { color: red; font-size: 20px; font-family: Foo; text-align: center }"
        styles = computed("<div><p>x</p></div>", css, tag="p")
        assert styles["color"] == "red"
        assert styles["font-size"] == "20px"
        assert styles["font-family"] == "Foo"
        assert styles["text-align"] == "center"

    def test_non_inherited_properties_do_not_flow(self, computed):
        css = "div { background-color: red; width: 100px; padding: 5px }"
        styles = computed("<div><p>x</p></div>", css, tag="p")
        assert styles["background-color"] == "transparent"
        assert styles["width"] == "auto"
        assert styles["padding-top"] == "0px"

    def test_child_overrides_inherited_value(self, computed):
        css = "div { color: red } p { color: blue }"
        assert computed("<div><p>x</p></div>", css, tag="p")["color"] == "blue"

    def test_colors_are_normalized(self, computed):
        css = "div { color: rgb(255,0,0); background-color: rgba(0,0,0,0); border-color: RED }"
        styles = computed("<div></div>", css)
        assert styles["color"] == "#ff0000ff"
        assert styles["background-color"] == "transparent"
        assert styles["border-color"] == "red"

    def test_em_length_uses_element_font_size(self, computed):
        css = "div { font-size: 10px; padding: 2em }"
        assert computed("<div></div>", css)["padding-top"] == "20.0px"

    @pytest.mark.parametrize(
        "value, expected",
        [("flex", "flex"), ("none", "none"), ("block", "block"), ("inline", "inline"), ("inline-block", "inline"), ("FLEX", "flex")],
    )
    def test_display_normalization(self, computed, value, expected):
        assert computed("<div></div>", f"div {{ display: {value} }}")["display"] == expected

    def test_unsupported_display_falls_back_to_block_with_warning(self, computed, warnings_collector):
        assert computed("<div></div>", "div { display: grid }")["display"] == "block"
        assert any("grid" in w["message"] for w in warnings_collector.get_warnings())


class TestSyntheticRoot:
    """The parser wraps the document in a <div class="_root">; user CSS must not style it."""

    @pytest.mark.parametrize("selector", ["div", "*"])
    def test_root_wrapper_ignores_user_rules(self, selector):
        from html2pic import Html2Pic

        root = Html2Pic("<p>x</p>", f"{selector} {{ padding: 10px; color: red }}").styled_tree
        assert root.computed_styles["padding-top"] == DEFAULT_STYLES["padding-top"]
        assert root.computed_styles["color"] == DEFAULT_STYLES["color"]


class TestUnitRegressions:
    def test_rem_is_converted(self):
        # 'rem' also ends with 'em'; it used to be parsed as em and fail.
        assert UnitConverter().to_pixels("2rem") == "32.0px"
        assert UnitConverter(base_font_size=10).to_pixels("1.5rem") == "15.0px"

    def test_rem_ignores_element_font_size(self):
        assert UnitConverter().to_pixels("1rem", font_size="40px") == "16.0px"

    def test_percent_resolves_only_against_pixel_reference(self):
        assert UnitConverter().to_pixels("50%", parent_value="30px") == "15.0px"
        assert UnitConverter().to_pixels("50%") == "50%"
        assert UnitConverter().to_pixels("50%", parent_value="auto") == "50%"

    @pytest.mark.parametrize("value, expected", [("2em", "40.0px"), ("150%", "30.0px"), ("1rem", "16.0px"), ("12px", "12px")])
    def test_font_size_is_relative_to_parent_font_size(self, computed, value, expected):
        css = f"div {{ font-size: 20px }} p {{ font-size: {value} }}"
        assert computed("<div><p>x</p></div>", css, tag="p")["font-size"] == expected

    def test_nested_em_font_sizes_compound(self, computed):
        css = "div { font-size: 10px } section { font-size: 2em } p { font-size: 2em }"
        assert computed("<div><section><p>x</p></section></div>", css, tag="p")["font-size"] == "40.0px"

    def test_rem_lengths(self, computed):
        styles = computed("<div></div>", "div { padding: 1rem; width: 10rem }")
        assert styles["padding-top"] == "16.0px"
        assert styles["width"] == "160.0px"

    @pytest.mark.parametrize("prop", ["padding-top", "border-radius", "width", "top", "max-width"])
    def test_percentages_are_preserved_for_the_layout_engine(self, computed, prop):
        # They used to be resolved against the *parent's value of the same property*,
        # e.g. padding: 10% became 10% of the parent's padding (usually 0px).
        css = f"section {{ width: 200px; padding: 4px; border-radius: 4px }} div {{ {prop}: 10% }}"
        assert computed("<section><div></div></section>", css)[prop] == "10%"

    def test_em_in_insets_and_constraints(self, computed):
        styles = computed("<div></div>", "div { font-size: 10px; top: 2em; max-width: 3em }")
        assert styles["top"] == "20.0px"
        assert styles["max-width"] == "30.0px"


class TestModernColorSyntax:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("rgb(255 0 0)", "#ff0000ff"),
            ("rgb(255 0 0 / 50%)", "#ff00007f"),
            ("rgb(0 0 255 / 0.5)", "#0000ff7f"),
            ("rgb(100%, 0%, 0%)", "#ff0000ff"),
            ("rgba(255, 0, 0, 50%)", "#ff00007f"),
            ("rgb(0 0 0 / 0)", "transparent"),
            ("hsl(0, 100%, 50%)", "#ff0000ff"),
            ("hsl(120deg 100% 25%)", "#008000ff"),
            ("hsl(240 100% 50% / 0.5)", "#0000ff7f"),
            ("hsla(0, 0%, 100%, 1)", "#ffffffff"),
            ("hsl(360, 100%, 50%)", "#ff0000ff"),
        ],
    )
    def test_normalize(self, value, expected):
        assert ColorNormalizer().normalize(value) == expected

    @pytest.mark.parametrize("value", ["hsl(1, 2)", "rgb(a b c)", "hsl(x, 1%, 1%)"])
    def test_malformed_falls_back_to_black(self, value, warnings_collector):
        assert ColorNormalizer().normalize(value) == "black"
        assert len(warnings_collector.get_warnings()) == 1
