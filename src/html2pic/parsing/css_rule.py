"""CSS rule representation."""
from dataclasses import dataclass
from typing import Dict


@dataclass
class CSSRule:
    """Represents a single CSS rule (selector + declarations)."""
    
    selector: str
    declarations: Dict[str, str]
    specificity: int = 0
