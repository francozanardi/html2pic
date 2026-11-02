"""CSS rule representation."""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class CSSRule:
    """Represents a single CSS rule (selector + declarations)."""
    
    selector: str
    declarations: Dict[str, str]
    specificity: int = 0
    # 'before' / 'after' for rules that style a pseudo-element of the matched element.
    pseudo_element: Optional[str] = None
