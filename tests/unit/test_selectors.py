import pytest

from html2pic.parsing import HtmlParser
from html2pic.parsing.selector import Selector, UnsupportedSelectorError


HTML = """
<div class="card" id="main">
  <h1 class="title big">Title</h1>
  <section class="body">
    <p class="text">Hello</p>
    <ul><li><span class="x">a</span></li></ul>
  </section>
</div>
<p class="text">Outside</p>
"""


@pytest.fixture(scope="module")
def tree():
    return HtmlParser().parse(HTML)


def select(tree, selector):
    parsed = Selector.parse(selector)
    found = []

    def walk(node):
        if node.is_element() and node.parent is not None and parsed.matches(node):
            found.append(node.tag + "".join("." + c for c in node.get_classes()))
        for child in node.children:
            walk(child)

    walk(tree)
    return found


@pytest.mark.parametrize(
    "selector, expected",
    [
        ("p", ["p.text", "p.text"]),
        (".text", ["p.text", "p.text"]),
        (".card .text", ["p.text"]),
        (".card p", ["p.text"]),
        ("#main p", ["p.text"]),
        (".card > p", []),
        (".body > p", ["p.text"]),
        ("div > h1", ["h1.title.big"]),
        (".title.big", ["h1.title.big"]),
        (".title.small", []),
        ("h1.title", ["h1.title.big"]),
        ("div.card#main", ["div.card"]),
        ("div#other", []),
        (".card ul span", ["span.x"]),
        ("section li > span", ["span.x"]),
        ("section > span", []),
        ("* > .x", ["span.x"]),
        ("div p", ["p.text"]),
    ],
)
def test_matching(tree, selector, expected):
    assert select(tree, selector) == expected


def test_synthetic_root_is_never_an_ancestor(tree):
    # The top-level <p> is wrapped in the parser's <div class="_root">, which must not
    # satisfy "div p" or "div > p".
    assert select(tree, "div > p") == []
    assert select(tree, "._root p") == []


@pytest.mark.parametrize(
    "selector, specificity",
    [("*", (0, 0, 0)), ("p", (0, 0, 1)), (".a.b", (0, 2, 0)), ("#x .a p", (1, 1, 1)), ("ul > li span.x", (0, 1, 3))],
)
def test_specificity(selector, specificity):
    assert Selector.parse(selector).specificity == specificity


@pytest.mark.parametrize("selector", ["", ".a:hover", "a[href]", "p + p", "p ~ p", "> p", "p >", "div$", ".a*"])
def test_unsupported(selector):
    with pytest.raises(UnsupportedSelectorError):
        Selector.parse(selector)


def test_ids_and_classes_may_follow_a_type_selector():
    (_, compound), = Selector.parse("p.x#b.y").parts
    assert (compound.tag, compound.ids, compound.classes) == ("p", ["b"], ["x", "y"])


def test_whitespace_around_child_combinator():
    assert Selector.parse("a>b").parts == Selector.parse("a  >  b").parts
