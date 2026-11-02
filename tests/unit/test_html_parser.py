import pytest

from html2pic.dom import NodeType
from html2pic.parsing import HtmlParser


def parse(html):
    return HtmlParser().parse(html)


class TestHtmlParser:
    def test_wraps_content_in_synthetic_root(self):
        root = parse("<p>hi</p>")
        assert root.tag == "div"
        assert root.get_classes() == ["_root"]
        assert [c.tag for c in root.children] == ["p"]

    def test_builds_nested_tree_with_parent_links(self):
        root = parse("<div><span>a</span><span>b</span></div>")
        div = root.children[0]
        assert [c.tag for c in div.children] == ["span", "span"]
        assert all(c.parent is div for c in div.children)
        assert div.parent is root

    def test_text_nodes_are_stripped(self):
        root = parse("<p>   hello   </p>")
        text = root.children[0].children[0]
        assert text.node_type == NodeType.TEXT
        assert text.text_content == "hello"

    def test_whitespace_only_text_is_dropped(self):
        root = parse("<div>\n   <p>x</p>\n   </div>")
        assert [c.tag for c in root.children[0].children] == ["p"]

    def test_class_list_is_joined_into_string(self):
        root = parse('<div class="a  b c"></div>')
        div = root.children[0]
        assert div.attributes["class"] == "a b c"
        assert div.get_classes() == ["a", "b", "c"]

    def test_id_and_other_attributes(self):
        div = parse('<div id="main" data-x="1"></div>').children[0]
        assert div.get_id() == "main"
        assert div.attributes["data-x"] == "1"

    def test_tags_are_lowercased(self):
        assert parse("<DIV></DIV>").children[0].tag == "div"

    def test_scripts_are_skipped_with_warning(self, warnings_collector):
        root = parse("<script>alert(1)</script><p>x</p>")
        assert [c.tag for c in root.children] == ["p"]
        assert {w["details"]["tag"] for w in warnings_collector.get_warnings()} == {"script"}

    def test_metadata_is_skipped_silently(self, warnings_collector):
        root = parse("<head><title>t</title><meta charset='utf-8'></head><p>x</p>")
        assert [c.tag for c in root.children] == ["p"]
        assert warnings_collector.get_warnings() == []

    def test_get_all_text_joins_descendants(self):
        root = parse("<div><p>Hello</p><p><b>big</b> world</p></div>")
        assert root.get_all_text() == "Hello big world"

    def test_has_text_content(self):
        assert parse("<div><p>x</p></div>").has_text_content()
        assert not parse("<div><p></p></div>").has_text_content()


class TestNonContentNodes:
    @pytest.mark.filterwarnings("ignore::bs4.XMLParsedAsHTMLWarning")
    @pytest.mark.parametrize(
        "markup",
        [
            "<!doctype html>",
            "<!-- a comment -->",
            "<![CDATA[x]]>",
            '<?xml version="1.0"?>',
        ],
    )
    def test_are_not_rendered_as_text(self, markup):
        root = parse(f"{markup}<p>{markup}hi</p>")
        assert root.get_all_text() == "hi"
        assert [c.tag for c in root.children] == ["p"]
