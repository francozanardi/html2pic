"""
Data models for DOM nodes and CSS styles
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

class NodeType(Enum):
    """Types of DOM nodes"""
    ELEMENT = "element"
    TEXT = "text"

@dataclass
class DOMNode:
    """
    Represents a node in the parsed DOM tree.
    
    This is our internal representation of HTML elements and text nodes.
    """
    node_type: NodeType
    tag: Optional[str] = None  # HTML tag name (div, span, p, etc.)
    attributes: Dict[str, str] = field(default_factory=dict)  # id, class, src, etc.
    text_content: str = ""  # Text content for text nodes
    children: List['DOMNode'] = field(default_factory=list)
    parent: Optional['DOMNode'] = None
    
    # Computed styles (set by StyleEngine)
    computed_styles: Dict[str, Any] = field(default_factory=dict)
    
    def get_classes(self) -> List[str]:
        """Get list of CSS classes for this element"""
        class_attr = self.attributes.get('class', '')
        
        # Handle BeautifulSoup's AttributeValueList
        if hasattr(class_attr, '__iter__') and not isinstance(class_attr, str):
            # It's a list-like object, convert to space-separated string
            class_attr = ' '.join(str(cls) for cls in class_attr)
        
        return [cls.strip() for cls in str(class_attr).split() if cls.strip()]
    
    def get_id(self) -> Optional[str]:
        """Get the ID attribute for this element"""
        return self.attributes.get('id')
    
    def is_element(self) -> bool:
        """Check if this is an element node"""
        return self.node_type == NodeType.ELEMENT
    
    def is_text(self) -> bool:
        """Check if this is a text node"""
        return self.node_type == NodeType.TEXT
    
    def has_text_content(self) -> bool:
        """Check if this node contains any text content"""
        if self.is_text() and self.text_content.strip():
            return True
        return any(child.has_text_content() for child in self.children)
    
    def get_all_text(self) -> str:
        """Get all text content from this node and its children"""
        if self.is_text():
            return self.text_content
        
        text_parts = []
        for child in self.children:
            child_text = child.get_all_text()
            if child_text:
                text_parts.append(child_text)
        
        return ' '.join(text_parts)

@dataclass
class CSSRule:
    """
    Represents a single CSS rule (selector + declarations).
    
    Example: .my-class { color: red; font-size: 16px; }
    """
    selector: str  # ".my-class"
    declarations: Dict[str, str]  # {"color": "red", "font-size": "16px"}
    specificity: int = 0  # Calculated CSS specificity for cascade resolution
    
class SelectorType(Enum):
    """Types of CSS selectors we support"""
    TAG = "tag"        # div, p, h1
    CLASS = "class"    # .my-class
    ID = "id"          # #my-id
    UNIVERSAL = "*"    # * (universal selector)

@dataclass
class ParsedSelector:
    """
    Parsed CSS selector information.
    
    For now we support simple selectors only.
    Complex selectors like "div > .class" will be added later.
    """
    selector_type: SelectorType
    value: str  # The actual selector value (without . or # prefix)
    
    @classmethod
    def parse(cls, selector: str) -> 'ParsedSelector':
        """Parse a simple CSS selector string"""
        selector = selector.strip()
        
        if selector.startswith('#'):
            return cls(SelectorType.ID, selector[1:])
        elif selector.startswith('.'):
            return cls(SelectorType.CLASS, selector[1:])
        elif selector == '*':
            return cls(SelectorType.UNIVERSAL, '*')
        else:
            # Assume it's a tag selector
            return cls(SelectorType.TAG, selector.lower())

# CSS property value types for type safety and validation
CSSValue = Union[str, int, float]

# Default CSS values - these will be applied when no explicit value is set
DEFAULT_STYLES = {
    # Layout
    'display': 'block',  # We'll map this to Row/Column/Text
    'flex-direction': 'row',
    'justify-content': 'flex-start',  # Maps to horizontal_distribution/vertical_distribution
    'align-items': 'stretch',  # Maps to vertical_align/horizontal_align
    'gap': '0px',
    
    # Box model
    'width': 'auto',
    'height': 'auto', 
    'padding-top': '0px',
    'padding-right': '0px',
    'padding-bottom': '0px',
    'padding-left': '0px',
    'margin-top': '0px',
    'margin-right': '0px',
    'margin-bottom': '0px',
    'margin-left': '0px',
    'border-width': '0px',
    'border-style': 'solid',
    'border-color': 'black',
    'border-radius': '0px',
    
    # Visual
    'background-color': 'transparent',
    'background-image': 'none',
    'background-size': 'cover',
    'box-shadow': 'none',
    
    # Typography
    'color': 'black',
    'font-family': 'Arial, sans-serif',
    'font-size': '16px',
    'font-weight': '400',
    'font-style': 'normal', 
    'text-align': 'left',
    'line-height': '1.2',
    'text-decoration': 'none',
    'text-wrap': 'wrap',
    
    # Positioning (for future use)
    'position': 'static',
    'top': 'auto',
    'right': 'auto', 
    'bottom': 'auto',
    'left': 'auto',
}