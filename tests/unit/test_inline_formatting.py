import pytest
from pictex import Column, Row, Text

from html2pic import Html2Pic
from html2pic.translation import PicTexTranslator
from html2pic.translation.inline_formatting import InlineFormatter, is_inline_level, is_text_like


def styled(html, css=""):
    h = Html2Pic(html, css)
    return h, h.styled_tree


def first(tree, tag):
    stack = [tree]
    while stack:
        node = stack.pop(0)
        if node.is_element() and node.tag == tag and node.parent is not None:
            return node
        stack.extend(node.children)
    raise AssertionError(tag)


def collapsed(html, css="", container="p"):
    _, tree = styled(html, css)
    node = first(tree, container)
    texts = InlineFormatter(None, None, None)._collapse_whitespace(node.children)
    out = []

    def walk(n):
        if n.is_text():
            out.append(texts.get(id(n)))
        for c in n.children:
            walk(c)

    for child in node.children:
        walk(child)
    return out


def translate(html, css=""):
    h, tree = styled(html, css)
    _, root = PicTexTranslator().translate(tree, h.font_registry)
    return root


class TestWhitespace:
    @pytest.mark.parametrize(
        "html, expected",
        [
            ("<p>  Hello   world  </p>", ["Hello world"]),
            ("<p>Hello <b>bold</b> text</p>", ["Hello ", "bold", " text"]),
            ("<p>Hello<b> bold </b> text</p>", ["Hello", " bold ", "text"]),
            ("<p>a <b> b</b></p>", ["a ", "b"]),
            ("<p>line one   <br>   line two</p>", ["line one", "line two"]),
            ("<p>\n  <b>x</b>\n</p>", ["", "x", ""]),
        ],
    )
    def test_collapsing(self, html, expected):
        assert collapsed(html) == expected

    def test_spaces_around_atomic_boxes_are_kept(self):
        assert collapsed("<p>a <img src='x.png'> b</p>") == ["a ", " b"]


class TestClassification:
    def test_inline_tags_default_to_inline(self):
        _, tree = styled("<p><b>x</b><span>y</span><a>z</a></p><div>d</div>")
        assert [first(tree, t).computed_styles["display"] for t in ("b", "span", "a", "div")] == ["inline", "inline", "inline", "block"]

    def test_css_can_blockify_inline_tags(self):
        _, tree = styled("<p><span>y</span></p>", "span { display: block }")
        assert not is_inline_level(first(tree, "span"))

    @pytest.mark.parametrize(
        "css, text_like",
        [
            ("", True),
            ("span { color: red; font-weight: bold; text-decoration: underline }", True),
            ("span { background-color: yellow }", False),
            ("span { padding: 2px }", False),
            ("span { border: 1px solid red }", False),
            ("span { width: 10px }", False),
            ("span { position: relative; top: 2px }", False),
        ],
    )
    def test_text_like(self, css, text_like):
        _, tree = styled("<p><span>y</span></p>", css)
        assert is_text_like(first(tree, "span")) is text_like

    def test_box_in_descendant_makes_ancestor_atomic(self):
        _, tree = styled("<p><b>a <span>b</span></b></p>", "span { background-color: red }")
        assert not is_text_like(first(tree, "b"))

    def test_images_are_atomic(self):
        _, tree = styled("<p><img src='x.png'></p>")
        assert is_inline_level(first(tree, "img")) and not is_text_like(first(tree, "img"))


class TestStructure:
    def test_paragraph_with_inline_markup_is_one_text(self):
        root = translate("<p>Hello <b>bold</b> and <i>italic</i></p>")
        (p,) = root._children
        assert len(p._children) == 1 and isinstance(p._children[0], Text)

    def test_block_children_split_runs(self):
        root = translate("<div>intro <b>x</b><p>block</p> tail</div>")
        (div,) = root._children
        kinds = [type(c).__name__ for c in div._children]
        assert kinds == ["Text", "Column", "Text"]

    def test_whitespace_only_runs_are_dropped(self):
        root = translate("<div>\n  <p>a</p>\n  <p>b</p>\n</div>")
        (div,) = root._children
        assert [type(c).__name__ for c in div._children] == ["Column", "Column"]

    def test_flex_items_are_blockified(self):
        root = translate("<div class='f'>text <b>bold</b> more</div>", ".f { display: flex }")
        (div,) = root._children
        assert [type(c).__name__ for c in div._children] == ["Text", "Row", "Text"]

    def test_atomic_inline_box_makes_a_wrapping_row(self):
        root = translate("<p>Status: <span class='t'>beta</span> today</p>", ".t { background-color: yellow }")
        (p,) = root._children
        (row,) = p._children
        assert isinstance(row, Row)
        assert [type(c).__name__ for c in row._children] == ["Text", "Row", "Text"]

    def test_hidden_inline_content_is_skipped(self):
        root = translate("<p>a <b class='h'>hidden</b> b</p>", ".h { display: none }")
        (p,) = root._children
        assert len(p._children) == 1


class TestRendering:
    def test_inline_markup_stays_on_one_line(self):
        plain = Html2Pic("<p>Hello world</p>").render()
        rich = Html2Pic("<p>Hello <b>world</b></p>").render()
        assert (rich.width, rich.height) == (plain.width, plain.height)

    def test_br_breaks_the_line(self):
        one = Html2Pic("<p>a b</p>").render()
        two = Html2Pic("<p>a<br>b</p>").render()
        assert two.height > one.height * 1.5

    def test_inline_color_applies_to_its_words_only(self):
        img = Html2Pic("<p>aaaa <span class='r'>bbbb</span></p>", "p { font-size: 30px; color: black } .r { color: red }").render().to_numpy("RGBA")
        opaque = img[..., 3] > 200
        reds = (img[..., 0] > 200) & (img[..., 1] < 60) & opaque
        blacks = (img[..., 0] < 60) & opaque
        assert reds[:, img.shape[1] // 2:].any() and not reds[:, : img.shape[1] // 3].any()
        assert blacks[:, : img.shape[1] // 3].any()
