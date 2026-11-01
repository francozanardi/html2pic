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
