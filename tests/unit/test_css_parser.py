import pytest

from html2pic.parsing import CssParser, ParsedSelector, SelectorType, ShorthandExpander
from html2pic.warnings import WarningCategory


def parse(css):
    return CssParser().parse(css)


class TestCssParser:
    def test_empty_css(self):
        rules, registry = parse("   ")
        assert rules == []
        assert len(registry) == 0

    def test_single_rule(self):
        rules, _ = parse(".card { color: red; width: 10px }")
        assert len(rules) == 1
        assert rules[0].selector == ".card"
        assert rules[0].declarations == {"color": "red", "width": "10px"}

    def test_selector_list_is_split_into_rules(self):
        rules, _ = parse("h1, .title, #main { color: blue }")
        assert [r.selector for r in rules] == ["h1", ".title", "#main"]
        assert all(r.declarations == {"color": "blue"} for r in rules)

    @pytest.mark.parametrize(
        "selector, specificity",
        [("#id", 10000), (".cls", 100), ("div", 1), ("*", 0), ("div.a#b", 10101), (".a .b > p", 201)],
    )
    def test_specificity(self, selector, specificity):
        rules, _ = parse(f"{selector} {{ color: red }}")
        assert rules[0].specificity == specificity

    def test_property_names_are_lowercased(self):
        rules, _ = parse("div { COLOR: red }")
        assert rules[0].declarations == {"color": "red"}

    def test_padding_shorthand_is_expanded(self):
        rules, _ = parse("div { padding: 1px 2px }")
        assert rules[0].declarations == {
            "padding-top": "1px",
            "padding-right": "2px",
            "padding-bottom": "1px",
            "padding-left": "2px",
        }

    def test_margin_shorthand_is_expanded(self):
        rules, _ = parse("div { margin: 1px 2px 3px }")
        assert rules[0].declarations == {
            "margin-top": "1px",
            "margin-right": "2px",
            "margin-bottom": "3px",
            "margin-left": "2px",
        }

    def test_border_shorthand_is_expanded(self):
        rules, _ = parse("div { border: 2px dashed rgba(0, 0, 0, 0.5) }")
        assert rules[0].declarations == {
            "border-width": "2px",
            "border-style": "dashed",
            "border-color": "rgba(0, 0, 0, 0.5)",
        }

    def test_later_declaration_wins_within_rule(self):
        rules, _ = parse("div { padding: 5px; padding-left: 9px }")
        assert rules[0].declarations["padding-left"] == "9px"
        assert rules[0].declarations["padding-top"] == "5px"

    def test_unsupported_property_warns(self, warnings_collector):
        parse("div { float: left }")
        warnings = warnings_collector.get_warnings(WarningCategory.CSS_PARSING)
        assert len(warnings) == 1
        assert warnings[0]["details"]["property"] == "float"

    def test_supported_property_does_not_warn(self, warnings_collector):
        parse("div { color: red; display: flex }")
        assert warnings_collector.get_warnings() == []


class TestFontFace:
    def test_font_face_is_registered(self):
        _, registry = parse(
            """
            @font-face {
                font-family: "My Font";
                src: url('fonts/my.ttf') format('truetype');
                font-weight: bold;
                font-style: italic;
            }
            """
        )
        assert len(registry) == 1
        face = registry.font_faces[0]
        assert face.family == "My Font"
        assert face.src == "fonts/my.ttf"
        assert face.weight == "700"
        assert face.style == "italic"

    def test_font_face_defaults(self):
        _, registry = parse("@font-face { font-family: X; src: url(x.ttf) }")
        face = registry.font_faces[0]
        assert (face.weight, face.style) == ("400", "normal")

    @pytest.mark.parametrize(
        "css",
        [
            "@font-face { src: url(x.ttf) }",
            "@font-face { font-family: X }",
            "@font-face { font-family: X; src: local(Arial) }",
        ],
    )
    def test_incomplete_font_face_is_ignored(self, css):
        _, registry = parse(css)
        assert len(registry) == 0

    def test_font_face_does_not_produce_rules(self):
        rules, _ = parse("@font-face { font-family: X; src: url(x.ttf) } p { color: red }")
        assert [r.selector for r in rules] == ["p"]

    @pytest.mark.parametrize(
        "weight, expected",
        [("normal", "400"), ("bold", "700"), ("lighter", "300"), ("600", "600"), ("950", "400"), ("abc", "400")],
    )
    def test_weight_normalization(self, weight, expected):
        assert CssParser()._normalize_weight(weight) == expected


class TestParsedSelector:
    @pytest.mark.parametrize(
        "selector, kind, value",
        [
            ("#main", SelectorType.ID, "main"),
            (".card", SelectorType.CLASS, "card"),
            ("*", SelectorType.UNIVERSAL, "*"),
            ("DIV", SelectorType.TAG, "div"),
            ("  p  ", SelectorType.TAG, "p"),
        ],
    )
    def test_parse(self, selector, kind, value):
        parsed = ParsedSelector.parse(selector)
        assert parsed.selector_type == kind
        assert parsed.value == value


class TestShorthandExpander:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("1px", ["1px", "1px", "1px", "1px"]),
            ("1px 2px", ["1px", "2px", "1px", "2px"]),
            ("1px 2px 3px", ["1px", "2px", "3px", "2px"]),
            ("1px 2px 3px 4px", ["1px", "2px", "3px", "4px"]),
            ("1px 2px 3px 4px 5px", ["1px", "2px", "3px", "4px"]),
            ("", ["0px", "0px", "0px", "0px"]),
        ],
    )
    def test_box_values(self, value, expected):
        assert ShorthandExpander()._parse_box_values(value) == expected

    def test_border_with_named_color(self):
        assert ShorthandExpander().expand_border("1px solid red") == {
            "border-width": "1px",
            "border-style": "solid",
            "border-color": "red",
        }

    def test_border_order_independent(self):
        assert ShorthandExpander().expand_border("#fff dotted 3px") == {
            "border-width": "3px",
            "border-style": "dotted",
            "border-color": "#fff",
        }

    def test_border_keeps_function_arguments_together(self):
        result = ShorthandExpander().expand_border("1px solid rgb(1, 2, 3)")
        assert result["border-color"] == "rgb(1, 2, 3)"


class TestBackgroundShorthand:
    @pytest.mark.parametrize(
        "value, color, image",
        [
            ("red", "red", "none"),
            ("#fff", "#fff", "none"),
            ("rgba(0, 0, 0, 0.5)", "rgba(0, 0, 0, 0.5)", "none"),
            ("linear-gradient(135deg, #667eea 0%, #764ba2 100%)", "transparent", "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"),
            ("url(bg.png) no-repeat center / cover", "transparent", "url(bg.png)"),
            ("blue url('a b.png') repeat-x top left", "blue", "url('a b.png')"),
            ("none", "transparent", "none"),
            ("url(a.png), url(b.png) green", "green", "url(a.png)"),
        ],
    )
    def test_expansion(self, value, color, image):
        assert ShorthandExpander().expand_background(value) == {
            "background-color": color,
            "background-image": image,
        }

    def test_parser_expands_and_does_not_warn(self, warnings_collector):
        rules, _ = parse("div { background: linear-gradient(red, blue) }")
        assert rules[0].declarations == {
            "background-color": "transparent",
            "background-image": "linear-gradient(red, blue)",
        }
        assert warnings_collector.get_warnings() == []

    def test_shorthand_resets_earlier_longhand(self):
        rules, _ = parse("div { background-image: url(x.png); background: red }")
        assert rules[0].declarations["background-image"] == "none"

    def test_later_longhand_overrides_shorthand(self):
        rules, _ = parse("div { background: red; background-color: blue }")
        assert rules[0].declarations["background-color"] == "blue"


class TestUnsupportedSelectors:
    @pytest.mark.parametrize(
        "selector, reason",
        [
            ("a:hover", "pseudo-classes"),
            ("p::after", "pseudo-classes"),
            ("[type=text]", "attribute"),
            ("h1 + p", "adjacent sibling"),
            ("li ~ li", "general sibling"),
            ("> p", "misplaced"),
            ("div >", "dangling"),
            (".a > > .b", "misplaced"),
            ("div$", "unexpected character"),
        ],
    )
    def test_unsupported_selectors_are_skipped_with_warning(self, selector, reason, warnings_collector):
        rules, _ = parse(f"{selector} {{ color: red }}")
        assert rules == []
        (warning,) = warnings_collector.get_warnings(WarningCategory.CSS_PARSING)
        assert warning["details"]["selector"] == selector
        assert reason in warning["details"]["reason"]

    def test_only_the_unsupported_part_of_a_list_is_skipped(self):
        rules, _ = parse("h1, a:hover, #x { color: red }")
        assert [r.selector for r in rules] == ["h1", "#x"]

    @pytest.mark.parametrize(
        "selector",
        ["h1", "my-element", ".btn-primary", "#_main", ".-x", "*", ".card h1", "div > p", "div.card", ".a.b", "ul>li"],
    )
    def test_supported_selectors_do_not_warn(self, selector, warnings_collector):
        rules, _ = parse(f"{selector} {{ color: red }}")
        assert len(rules) == 1
        assert warnings_collector.get_warnings() == []
