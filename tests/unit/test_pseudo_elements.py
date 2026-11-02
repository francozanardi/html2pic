import pytest

from html2pic import Html2Pic
from html2pic.parsing import CssParser


def pseudo_children(html, css, tag="div"):
    root = Html2Pic(html, css).styled_tree
    node = next(n for n in _walk(root) if n.tag == tag and n.parent is not None and n.pseudo_element is None)
    return node, [c for c in node.children if c.pseudo_element]


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def text_of(pseudo):
    return "".join(c.text_content for c in pseudo.children)


class TestGeneration:
    def test_before_and_after_positions(self):
        node, pseudos = pseudo_children("<div><p>x</p></div>", 'div::before { content: "A" } div::after { content: "Z" }')
        assert node.children[0].pseudo_element == "before" and text_of(node.children[0]) == "A"
        assert node.children[-1].pseudo_element == "after" and text_of(node.children[-1]) == "Z"
        assert [c.tag for c in node.children] == ["::before", "p", "::after"]

    @pytest.mark.parametrize("content", ["none", "normal", None])
    def test_no_box_without_content(self, content):
        css = "div::before { color: red }" if content is None else f"div::before {{ content: {content} }}"
        _, pseudos = pseudo_children("<div>x</div>", css)
        assert pseudos == []

    def test_empty_string_generates_an_empty_box(self):
        _, (pseudo,) = pseudo_children("<div>x</div>", 'div::after { content: ""; width: 5px }')
        assert pseudo.children == []
        assert pseudo.computed_styles["width"] == "5px"

    def test_display_none(self):
        _, pseudos = pseudo_children("<div>x</div>", 'div::after { content: "a"; display: none }')
        assert pseudos == []

    def test_inline_by_default(self):
        _, (pseudo,) = pseudo_children("<div>x</div>", 'div::after { content: "a" }')
        assert pseudo.computed_styles["display"] == "inline"

    def test_inherits_from_element(self):
        _, (pseudo,) = pseudo_children("<div>x</div>", 'div { color: red; font-size: 20px; padding: 4px } div::after { content: "a" }')
        assert pseudo.computed_styles["color"] == "red"
        assert pseudo.computed_styles["font-size"] == "20px"
        assert pseudo.computed_styles["padding-top"] == "0px"
        assert pseudo.children[0].computed_styles["color"] == "red"

    def test_em_is_relative_to_element(self):
        _, (pseudo,) = pseudo_children("<div>x</div>", 'div { font-size: 10px } div::after { content: "a"; font-size: 2em; width: 2em }')
        assert pseudo.computed_styles["font-size"] == "20.0px"
        assert pseudo.computed_styles["width"] == "40.0px"

    def test_specificity_between_pseudo_rules(self):
        css = '.a::after { content: "low" } #x::after { content: "high" } .a::after { color: blue }'
        _, (pseudo,) = pseudo_children("<div id='x' class='a'>t</div>", css)
        assert text_of(pseudo) == "high"
        assert pseudo.computed_styles["color"] == "blue"

    def test_pseudo_rules_do_not_style_the_element(self):
        node, _ = pseudo_children("<div>x</div>", 'div::after { content: "a"; color: red }')
        assert node.computed_styles["color"] == "black"

    def test_legacy_single_colon(self):
        _, (pseudo,) = pseudo_children("<div>x</div>", 'div:after { content: "a" }')
        assert text_of(pseudo) == "a"

    def test_universal_pseudo(self):
        root = Html2Pic("<div><p>x</p></div>", '::before { content: "*" }').styled_tree
        generated = [n for n in _walk(root) if n.pseudo_element]
        assert [n.parent.tag for n in generated] == ["div", "p"]

    def test_styling_twice_does_not_duplicate(self):
        h = Html2Pic("<div>x</div>", 'div::after { content: "a" }')
        tree = h.styled_tree
        h._style_engine.apply_styles(tree, h.style_rules, h.font_registry)
        div = tree.children[0]
        assert [c.pseudo_element for c in div.children].count("after") == 1


class TestContent:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ('"a" "b"', "ab"),
            ('"\\2022  "', "• "),
            ('" (" attr(data-n) ")"', " (7)"),
            ("attr(missing)", ""),
            ("open-quote 'x' close-quote", "“x”"),
            ("no-open-quote", ""),
        ],
    )
    def test_values(self, value, expected):
        _, (pseudo,) = pseudo_children("<div data-n='7'>t</div>", f"div::before {{ content: {value} }}")
        assert text_of(pseudo) == expected

    def test_unsupported_parts_warn(self, warnings_collector):
        _, (pseudo,) = pseudo_children("<div>t</div>", 'div::before { content: "n" counter(item) }')
        assert text_of(pseudo) == "n"
        assert any("counter" in w["message"] for w in warnings_collector.get_warnings())

    def test_spaces_are_kept_in_generated_text(self):
        from html2pic.translation import PicTexTranslator

        h = Html2Pic("<div>x</div>", 'div::after { content: " / " }')
        PicTexTranslator().translate(h.styled_tree, h.font_registry)  # must not drop the text
        _, (pseudo,) = pseudo_children("<div>x</div>", 'div::after { content: " / " }')
        assert text_of(pseudo) == " / "


def test_parser_records_pseudo_element():
    rules, _ = CssParser().parse(".a::after, .b, ::before { color: red }")
    assert [(r.selector, r.pseudo_element) for r in rules] == [(".a::after", "after"), (".b", None), ("::before", "before")]
