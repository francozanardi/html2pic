"""
HTML parser using BeautifulSoup to create DOM tree
"""

from typing import Optional
from bs4 import BeautifulSoup, Tag, NavigableString, Comment
from .models import DOMNode, NodeType
from .exceptions import ParseError
from .warnings_system import get_warning_collector, WarningCategory

class HtmlParser:
    """
    Parses HTML content into our internal DOM tree representation.
    
    Uses BeautifulSoup under the hood for robust HTML parsing,
    then converts to our own DOMNode structure for easier processing.
    """
    
    def __init__(self):
        self.parser = "html.parser"  # Use Python's built-in parser
        self.warnings = get_warning_collector()
    
    def parse(self, html_content: str) -> DOMNode:
        """
        Parse HTML string into a DOM tree.
        
        Args:
            html_content: HTML content as string
            
        Returns:
            Root DOMNode representing the document
            
        Raises:
            ParseError: If HTML parsing fails
        """
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, self.parser)
            
            # Convert BeautifulSoup tree to our DOM tree
            # We create a virtual root node to hold all top-level elements
            root = DOMNode(
                node_type=NodeType.ELEMENT,
                tag="__root__",  # Special tag for root node
                attributes={},
                text_content="",
                children=[],
                parent=None
            )
            
            # Process all direct children of the parsed document
            for element in soup.contents:
                if isinstance(element, Tag):
                    child_node = self._convert_element(element)
                    if child_node:
                        child_node.parent = root
                        root.children.append(child_node)
                elif isinstance(element, NavigableString) and not isinstance(element, Comment):
                    # Handle top-level text content
                    text_content = str(element).strip()
                    if text_content:
                        text_node = DOMNode(
                            node_type=NodeType.TEXT,
                            text_content=text_content,
                            parent=root
                        )
                        root.children.append(text_node)
            
            return root
            
        except Exception as e:
            raise ParseError(f"Failed to parse HTML: {e}") from e
    
    def _convert_element(self, bs_element: Tag) -> Optional[DOMNode]:
        """
        Convert a BeautifulSoup Tag to our DOMNode.
        
        Args:
            bs_element: BeautifulSoup Tag element
            
        Returns:
            DOMNode or None if element should be skipped
        """
        # Skip script, style, and other non-visual elements
        if bs_element.name in ['script', 'style', 'meta', 'link', 'title', 'head']:
            self.warnings.warn(
                f"Skipping non-visual element '<{bs_element.name}>'",
                WarningCategory.HTML_PARSING,
                {'tag': bs_element.name, 'reason': 'non-visual element'}
            )
            return None
        
        # Check if element is recognized
        supported_tags = {
            'div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
            'section', 'article', 'header', 'footer', 'main', 'nav', 'aside',
            'img', 'br', 'hr', 'strong', 'em', 'b', 'i', 'u', 's',
            'ul', 'ol', 'li', 'a'
        }
        
        # Warn about potentially unsupported elements
        unsupported_tags = {
            'table', 'tr', 'td', 'th', 'thead', 'tbody', 'tfoot',
            'form', 'input', 'button', 'select', 'textarea', 'label',
            'video', 'audio', 'canvas', 'svg', 'iframe', 'embed', 'object'
        }
        
        if bs_element.name not in supported_tags:
            if bs_element.name in unsupported_tags:
                self.warnings.warn_unsupported_html_tag(
                    bs_element.name, 
                    f"May not render correctly - consider using div with appropriate styling"
                )
            else:
                # Completely unrecognized element
                self.warnings.warn_unsupported_html_tag(
                    bs_element.name,
                    f"Unrecognized HTML element - will be treated as a div container"
                )
        
        # Create element node
        node = DOMNode(
            node_type=NodeType.ELEMENT,
            tag=bs_element.name,
            attributes=dict(bs_element.attrs) if bs_element.attrs else {},
            text_content="",
            children=[],
            parent=None
        )
        
        # Process children
        for child in bs_element.contents:
            if isinstance(child, Tag):
                child_node = self._convert_element(child)
                if child_node:
                    child_node.parent = node
                    node.children.append(child_node)
                    
            elif isinstance(child, NavigableString) and not isinstance(child, Comment):
                # Handle text content
                text_content = str(child).strip()
                if text_content:
                    text_node = DOMNode(
                        node_type=NodeType.TEXT,
                        text_content=text_content,
                        parent=node
                    )
                    node.children.append(text_node)
        
        return node
    
    def _should_skip_element(self, tag_name: str) -> bool:
        """
        Determine if an HTML element should be skipped during parsing.
        
        Args:
            tag_name: HTML tag name
            
        Returns:
            True if element should be skipped
        """
        # Elements that don't contribute to visual layout
        skip_tags = {
            'script', 'style', 'meta', 'link', 'title', 'head',
            'base', 'noscript', 'template'
        }
        return tag_name.lower() in skip_tags