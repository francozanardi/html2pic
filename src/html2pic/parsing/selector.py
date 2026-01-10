"""CSS selector parsing."""
from dataclasses import dataclass
from enum import Enum


class SelectorType(Enum):
    TAG = "tag"
    CLASS = "class"
    ID = "id"
    UNIVERSAL = "*"


@dataclass
class ParsedSelector:
    """Parsed CSS selector information."""
    
    selector_type: SelectorType
    value: str
    
    @classmethod
    def parse(cls, selector: str) -> 'ParsedSelector':
        selector = selector.strip()
        
        if selector.startswith('#'):
            return cls(SelectorType.ID, selector[1:])
        elif selector.startswith('.'):
            return cls(SelectorType.CLASS, selector[1:])
        elif selector == '*':
            return cls(SelectorType.UNIVERSAL, '*')
        else:
            return cls(SelectorType.TAG, selector.lower())
