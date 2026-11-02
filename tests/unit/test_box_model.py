import pytest

from html2pic import Html2Pic
from html2pic.styling import DEFAULT_STYLES
from html2pic.translation.style_applicators import SizeApplicator, SpacingApplicator

from .test_translation import apply


def margins(html, css, *selectors):
    # .w is a block formatting context root, so margins can't escape past it.
    tree = Html2Pic(html, ".w { overflow: hidden } " + css).styled_tree
    out = []
    for cls in selectors:
        node = _find(tree, cls)
        out.append((node.computed_styles["margin-top"], node.computed_styles["margin-bottom"]))
    return out


def _find(node, cls):
    if node.is_element() and cls in node.get_classes():
        return node
    for child in node.children:
        found = _find(child, cls)
        if found is not None:
            return found
    return None


class TestBoxSizing:
    BOX = {"width": "30px", "height": "20px", "padding-top": "5px", "padding-right": "5px",
           "padding-bottom": "5px", "padding-left": "5px", "border-width": "3px"}

    def test_content_box_is_the_default(self):
        assert DEFAULT_STYLES["box-sizing"] == "content-box"
        assert apply(SizeApplicator(), **self.BOX).called("size") == [((46.0, 36.0), {})]

    def test_border_box(self):
        assert apply(SizeApplicator(), **self.BOX, **{"box-sizing": "border-box"}).called("size") == [((30.0, 20.0), {})]

    def test_constraints_are_adjusted(self):
        b = apply(SizeApplicator(), **{"min-width": "10px", "max-height": "40px", "padding-left": "2px", "padding-top": "1px"})
        assert b.called("min_width") == [((12.0,), {})]
        assert b.called("max_height") == [((41.0,), {})]

    def test_percentages_warn_when_padding_or_border_would_be_added(self, warnings_collector):
        b = apply(SizeApplicator(), width="50%", **{"padding-left": "10px"})
        assert b.called("size") == [(("50%", None), {})]
        assert any("content-box" in w["message"] for w in warnings_collector.get_warnings())

    def test_percentages_without_padding_do_not_warn(self, warnings_collector):
        apply(SizeApplicator(), width="50%")
        assert warnings_collector.get_warnings() == []

    def test_rendered_size(self):
        img = Html2Pic('<div class="b"></div>', ".b { width: 40px; height: 20px; padding: 10px; border: 5px solid black }").render()
        assert (img.width, img.height) == (70, 50)


class TestNegativeMargins:
    def test_negative_only_margins_are_applied(self):
        b = apply(SpacingApplicator(), **{"margin-top": "-10px"})
        assert b.called("margin") == [((-10.0, 0, 0, 0), {})]


class TestMarginCollapsing:
    @pytest.mark.parametrize(
        "bottom, top, collapsed",
        [("10px", "20px", "20.0px"), ("30px", "5px", "30.0px"), ("-5px", "-10px", "-10.0px"), ("20px", "-5px", "15.0px")],
    )
    def test_siblings(self, bottom, top, collapsed):
        css = f".a {{ margin-bottom: {bottom} }} .b {{ margin-top: {top} }}"
        (a, b) = margins('<div class="w"><div class="a"></div><div class="b"></div></div>', css, "a", "b")
        assert a[1] == "0.0px" and b[0] == collapsed

    def test_text_between_siblings_prevents_collapsing(self):
        css = ".a { margin-bottom: 10px } .b { margin-top: 20px }"
        (a, b) = margins('<div class="w"><div class="a"></div>text<div class="b"></div></div>', css, "a", "b")
        assert (a[1], b[0]) == ("10px", "20px")

    def test_absolute_siblings_are_skipped(self):
        css = ".a { margin-bottom: 10px } .x { position: absolute } .b { margin-top: 20px }"
        (a, b) = margins('<div class="w"><div class="a"></div><div class="x"></div><div class="b"></div></div>', css, "a", "b")
        assert (a[1], b[0]) == ("0.0px", "20.0px")

    def test_flex_items_do_not_collapse(self):
        css = ".w { display: flex; flex-direction: column } .a { margin-bottom: 10px } .b { margin-top: 20px }"
        (a, b) = margins('<div class="w"><div class="a"></div><div class="b"></div></div>', css, "a", "b")
        assert (a[1], b[0]) == ("10px", "20px")

    def test_top_level_siblings_collapse(self):
        (a, b) = margins('<div class="a"></div><div class="b"></div>', ".a { margin-bottom: 10px } .b { margin-top: 20px }", "a", "b")
        assert (a[1], b[0]) == ("0.0px", "20.0px")

    def test_parent_and_first_child(self):
        html = '<div class="w"><div class="p"><div class="c"></div></div></div>'
        (p, c) = margins(html, ".p { margin-top: 5px } .c { margin-top: 15px }", "p", "c")
        assert (p[0], c[0]) == ("15.0px", "0.0px")

    def test_parent_and_last_child(self):
        html = '<div class="w"><div class="p"><div class="c"></div></div></div>'
        (p, c) = margins(html, ".p { margin-bottom: 20px } .c { margin-bottom: 8px }", "p", "c")
        assert (p[1], c[1]) == ("20.0px", "0.0px")

    @pytest.mark.parametrize(
        "parent_css",
        ["padding-top: 1px", "border: 1px solid black", "overflow: hidden", "position: absolute"],
    )
    def test_parent_separators(self, parent_css):
        html = '<div class="w"><div class="p"><div class="c"></div></div></div>'
        (p, c) = margins(html, f".p {{ margin-top: 5px; {parent_css} }} .c {{ margin-top: 15px }}", "p", "c")
        assert (p[0], c[0]) == ("5px", "15px")

    def test_fixed_height_parent_keeps_last_child_margin(self):
        html = '<div class="w"><div class="p"><div class="c"></div></div></div>'
        (p, c) = margins(html, ".p { height: 50px } .c { margin-bottom: 8px }", "p", "c")
        assert c[1] == "8px"

    def test_margins_stay_inside_the_image(self):
        # The child's margin collapses into the top-level .a, but the root is a block
        # formatting context root, so the margin is kept inside the image, not dropped.
        css = ".c { width: 10px; height: 10px; margin-top: 10px; background-color: red }"
        img = Html2Pic('<div class="a"><div class="c"></div></div>', css).render()
        assert img.height == 20

    def test_margin_escapes_through_non_bfc_ancestors(self):
        html = '<div class="o"><div class="p"><div class="c"></div></div></div>'
        tree = Html2Pic(html, ".c { margin-top: 12px }").styled_tree
        tops = [_find(tree, cls).computed_styles["margin-top"] for cls in ("o", "p", "c")]
        assert tops == ["12.0px", "0.0px", "0.0px"]

    def test_nested_chain_collapses_bottom_up(self):
        html = '<div class="w"><div class="p"><div class="m"><div class="c"></div></div></div></div>'
        (p, m, c) = margins(html, ".c { margin-top: 30px } .m { margin-top: 10px }", "p", "m", "c")
        assert (p[0], m[0], c[0]) == ("30.0px", "0.0px", "0.0px")

    def test_rendered(self):
        css = ".b { width: 10px; height: 10px; margin: 10px 0; background-color: red }"
        img = Html2Pic('<div class="b"></div><div class="b"></div>', css).render()
        assert img.height == 50  # 10 + 10 + 10 (collapsed) + 10 + 10
