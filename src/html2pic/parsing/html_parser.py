"""HTML parser using BeautifulSoup."""

from typing import Optional

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from ..dom import DOMNode, NodeType
from ..warnings import get_warning_collector
from ..exceptions import ParseError


class HtmlParser:
    """Parses HTML content into a DOM tree."""

    SKIP_TAGS = {"script", "meta", "title"}

    def __init__(self):
        self.warnings = get_warning_collector()

    def parse(self, html_content: str) -> DOMNode:
        """Parse HTML string into a DOM tree."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            return self._create_root(soup)
        except Exception as e:
            raise ParseError(f"Failed to parse HTML: {e}") from e

    def _create_root(self, soup: BeautifulSoup) -> DOMNode:
        root = DOMNode(
            node_type=NodeType.ELEMENT, tag="div", attributes={"class": "_root"}
        )

        for child in soup.children:
            child_node = self._process_node(child, root)
            if child_node:
                root.children.append(child_node)

        return root

    def _process_node(self, node, parent: DOMNode) -> Optional[DOMNode]:
        if isinstance(node, NavigableString):
            text = str(node).strip()
            if text:
                return DOMNode(
                    node_type=NodeType.TEXT, text_content=text, parent=parent
                )
            return None

        if isinstance(node, Tag):
            tag_name = node.name.lower()

            if tag_name in self.SKIP_TAGS:
                self.warnings.warn_unsupported_html_tag(tag_name)
                return None

            attrs = {}
            for key, value in node.attrs.items():
                if isinstance(value, list):
                    attrs[key] = " ".join(value)
                else:
                    attrs[key] = value

            dom_node = DOMNode(
                node_type=NodeType.ELEMENT,
                tag=tag_name,
                attributes=attrs,
                parent=parent,
            )

            for child in node.children:
                child_node = self._process_node(child, dom_node)
                if child_node:
                    dom_node.children.append(child_node)

            return dom_node

        return None
