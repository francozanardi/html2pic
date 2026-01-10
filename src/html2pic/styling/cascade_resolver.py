"""CSS cascade resolution - selector matching and specificity."""
from typing import List

from ..dom import DOMNode
from ..parsing import CSSRule, ParsedSelector, SelectorType
from ..warnings import get_warning_collector


class CascadeResolver:
    """Handles CSS selector matching and specificity calculation."""
    
    def __init__(self):
        self.warnings = get_warning_collector()
    
    def find_matching_rules(self, node: DOMNode, css_rules: List[CSSRule]) -> List[CSSRule]:
        """Find all CSS rules that match the given DOM node."""
        matching = []
        for rule in css_rules:
            if self._selector_matches(rule.selector, node):
                matching.append(rule)
        return matching
    
    def calculate_specificity(self, selector: str) -> int:
        """Calculate CSS specificity for a selector."""
        try:
            parsed = ParsedSelector.parse(selector)
            
            if parsed.selector_type == SelectorType.ID:
                return 100
            elif parsed.selector_type == SelectorType.CLASS:
                return 10
            elif parsed.selector_type == SelectorType.TAG:
                return 1
            return 0
        except Exception as e:
            self.warnings.warn_unexpected_error(f"Failed to calculate specificity for selector '{selector}': {e}")
            return 1
    
    def _selector_matches(self, selector: str, node: DOMNode) -> bool:
        if not node.is_element():
            return False
        
        try:
            parsed = ParsedSelector.parse(selector)
            
            if parsed.selector_type == SelectorType.UNIVERSAL:
                return True
            elif parsed.selector_type == SelectorType.TAG:
                return node.tag == parsed.value
            elif parsed.selector_type == SelectorType.CLASS:
                return parsed.value in node.get_classes()
            elif parsed.selector_type == SelectorType.ID:
                return node.get_id() == parsed.value
            return False
        except Exception as e:
            self.warnings.warn_unexpected_error(f"Failed to match selector '{selector}': {e}")
            return False
