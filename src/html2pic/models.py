"""
Data models for DOM nodes and CSS styles
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import os

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


@dataclass
class FontFace:
    """
    Represents a @font-face declaration from CSS.

    Example:
    @font-face {
        font-family: "MyFont";
        src: url("myfont.woff2");
        font-weight: normal;
        font-style: normal;
    }
    """
    family: str  # The font-family name declared in the @font-face rule
    src: str     # The font file path or URL
    weight: str = "400"  # Font weight (normal, bold, 100-900)
    style: str = "normal"  # Font style (normal, italic)

    def matches(self, family: str, weight: str = "400", style: str = "normal") -> bool:
        """Check if this font face matches the given criteria"""
        return (self.family.lower() == family.lower() and
                self.weight == weight and
                self.style == style)


class FontRegistry:
    """
    Registry for managing @font-face declarations and font resolution.

    This class stores all @font-face rules and provides methods to resolve
    font-family declarations to actual font paths with fallbacks.
    """

    def __init__(self):
        self.font_faces: List[FontFace] = []

    def add_font_face(self, font_face: FontFace):
        """Add a @font-face declaration to the registry"""
        self.font_faces.append(font_face)

    def clear(self):
        """Clear all registered font faces"""
        self.font_faces.clear()

    def resolve_font_family(self, font_family_value: str, weight: str = "400", style: str = "normal") -> List[str]:
        """
        Resolve a CSS font-family value to a list of font paths/names for PicTex.

        Takes a font-family value like "MyFont, Arial, sans-serif" and returns
        a list of font paths/names that PicTex can use, in fallback order.

        Args:
            font_family_value: CSS font-family value (may contain multiple fonts)
            weight: Font weight to match (currently ignored - uses exact family match only)
            style: Font style to match (currently ignored - uses exact family match only)

        Returns:
            List of font names/paths in fallback order for use with PicTex font_fallbacks()
        """
        # Split the font-family value by comma and clean each font name
        font_names = [name.strip().strip('"\'') for name in font_family_value.split(',')]
        resolved_fonts = []

        for font_name in font_names:
            # Try to find an exact @font-face declaration for this family
            matching_font = self._find_exact_font_face(font_name)
            if matching_font:
                # Use the font file path from @font-face
                resolved_fonts.append(matching_font.src)
            else:
                # Use the font name as-is (system font or font file path)
                resolved_fonts.append(font_name)

        return resolved_fonts if resolved_fonts else ["Arial"]  # Fallback to Arial

    def _find_exact_font_face(self, family: str) -> Optional[FontFace]:
        """
        Find a @font-face declaration that exactly matches the font family name.

        This simplified approach just matches by family name, ignoring weight and style.
        CSS font fallbacks will handle the weight/style matching.
        """
        for font_face in self.font_faces:
            if font_face.family.lower() == family.lower():
                return font_face
        return None

    def get_font_families(self) -> List[str]:
        """Get all registered font family names"""
        return list(set(font_face.family for font_face in self.font_faces))

    def __len__(self) -> int:
        """Return number of registered font faces"""
        return len(self.font_faces)