"""HTML parser using BeautifulSoup."""
from dataclasses import dataclass
from typing import List, Optional

from bs4 import BeautifulSoup, NavigableString, Tag
from bs4.element import PreformattedString
import re

_WHITESPACE = re.compile(r'[ \t\n\r\f]+')

from ..dom import DOMNode, NodeType
from ..warnings import get_warning_collector
from ..exceptions import ParseError


@dataclass
class StyleSource:
    """A stylesheet referenced by the document, in document order."""
    
    kind: str  # 'style' for <style> contents, 'link' for <link rel="stylesheet" href>
    value: str  # CSS text for 'style', the (unresolved) href for 'link'


class HtmlParser:
    """Parses HTML content into a DOM tree.
    
    Besides the DOM, a parse collects the document's stylesheets (``<style>`` and
    ``<link rel="stylesheet">``, in document order) and its ``<base href>``. Those elements,
    like the rest of ``<head>``, are not rendered.
    """
    
    # Elements that are never rendered and carry nothing html2pic uses.
    SKIP_TAGS = {'script', 'noscript', 'template', 'meta', 'title'}
    # Elements handled here (stylesheets, base URL) and not rendered either.
    METADATA_TAGS = {'head', 'style', 'link', 'base'}
    APPLICABLE_MEDIA = {'', 'all', 'screen'}
    
    def __init__(self):
        self.warnings = get_warning_collector()
        self.stylesheets: List[StyleSource] = []
        self.base_href: Optional[str] = None
    
    def parse(self, html_content: str) -> DOMNode:
        """Parse HTML string into a DOM tree."""
        self.stylesheets = []
        self.base_href = None
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            return self._create_root(soup)
        except Exception as e:
            raise ParseError(f"Failed to parse HTML: {e}") from e
    
    def _create_root(self, soup: BeautifulSoup) -> DOMNode:
        root = DOMNode(node_type=NodeType.ELEMENT, tag='div', attributes={'class': '_root'})
        
        for child in soup.children:
            child_node = self._process_node(child, root)
            if child_node:
                root.children.append(child_node)
        
        return root
    
    def _process_metadata(self, tag: Tag):
        name = tag.name.lower()
        if name == 'head':
            for child in tag.children:
                if isinstance(child, Tag):
                    self._process_node(child, None)
        elif name == 'style':
            if self._media_applies(tag):
                self.stylesheets.append(StyleSource('style', tag.get_text()))
        elif name == 'link':
            rel = tag.get('rel') or []
            rel = rel if isinstance(rel, list) else rel.split()
            href = tag.get('href')
            if 'stylesheet' in [r.lower() for r in rel] and href and self._media_applies(tag):
                self.stylesheets.append(StyleSource('link', href))
        elif name == 'base':
            if self.base_href is None and tag.get('href'):
                self.base_href = tag['href']
    
    def _media_applies(self, tag: Tag) -> bool:
        media = (tag.get('media') or '').strip().lower()
        if media in self.APPLICABLE_MEDIA:
            return True
        self.warnings.warn_message(f"Ignored <{tag.name}> with unsupported media query '{media}'")
        return False
    
    def _process_node(self, node, parent: DOMNode) -> Optional[DOMNode]:
        # Comments, doctypes, CDATA sections, declarations and processing instructions are
        # NavigableString subclasses too, but they are not rendered content.
        if isinstance(node, PreformattedString):
            return None
        
        if isinstance(node, NavigableString):
            # Whitespace is collapsed, not removed: spaces between inline elements matter
            # ("<b>a</b> <i>b</i>"). The translator drops whitespace where CSS would.
            text = _WHITESPACE.sub(' ', str(node))
            if not text:
                return None
            return DOMNode(
                node_type=NodeType.TEXT,
                text_content=text,
                parent=parent
            )
        
        if isinstance(node, Tag):
            tag_name = node.name.lower()
            
            if tag_name in self.METADATA_TAGS:
                self._process_metadata(node)
                return None
            
            if tag_name in self.SKIP_TAGS:
                if tag_name in ('script', 'noscript', 'template'):
                    self.warnings.warn_unsupported_html_tag(tag_name)
                return None
            
            attrs = {}
            for key, value in node.attrs.items():
                if isinstance(value, list):
                    attrs[key] = ' '.join(value)
                else:
                    attrs[key] = value
            
            dom_node = DOMNode(
                node_type=NodeType.ELEMENT,
                tag=tag_name,
                attributes=attrs,
                parent=parent
            )
            
            for child in node.children:
                child_node = self._process_node(child, dom_node)
                if child_node:
                    dom_node.children.append(child_node)
            
            return dom_node
        
        return None
