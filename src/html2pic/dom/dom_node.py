"""DOM node representation."""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .node_type import NodeType


@dataclass
class DOMNode:
    """Represents a node in the parsed DOM tree."""
    
    node_type: NodeType
    tag: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)
    text_content: str = ""
    children: List['DOMNode'] = field(default_factory=list)
    parent: Optional['DOMNode'] = None
    computed_styles: Dict[str, Any] = field(default_factory=dict)
    
    def get_classes(self) -> List[str]:
        class_attr = self.attributes.get('class', '')
        if hasattr(class_attr, '__iter__') and not isinstance(class_attr, str):
            class_attr = ' '.join(str(cls) for cls in class_attr)
        return [cls.strip() for cls in str(class_attr).split() if cls.strip()]
    
    def get_id(self) -> Optional[str]:
        return self.attributes.get('id')
    
    def is_element(self) -> bool:
        return self.node_type == NodeType.ELEMENT
    
    def is_text(self) -> bool:
        return self.node_type == NodeType.TEXT
    
    def has_text_content(self) -> bool:
        if self.is_text() and self.text_content.strip():
            return True
        return any(child.has_text_content() for child in self.children)
    
    def get_all_text(self) -> str:
        if self.is_text():
            return self.text_content
        text_parts = [child.get_all_text() for child in self.children if child.get_all_text()]
        return ' '.join(text_parts)
