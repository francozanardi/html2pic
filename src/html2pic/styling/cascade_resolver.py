"""CSS cascade resolution - selector matching and specificity."""
from typing import List

from ..dom import DOMNode
from ..parsing import CSSRule
from ..parsing.selector import Selector, UnsupportedSelectorError, specificity_to_int
from ..warnings import get_warning_collector


class CascadeResolver:
    """Handles CSS selector matching and specificity calculation."""
    
    def __init__(self):
        self.warnings = get_warning_collector()
    
    def find_matching_rules(self, node: DOMNode, css_rules: List[CSSRule]) -> List[CSSRule]:
        """Find all CSS rules that match the given DOM node."""
        return [rule for rule in css_rules if self._selector_matches(rule.selector, node)]
    
    def calculate_specificity(self, selector: str) -> int:
        """Calculate CSS specificity for a selector (ids, then classes, then tags)."""
        try:
            return specificity_to_int(Selector.parse(selector).specificity)
        except UnsupportedSelectorError:
            return 0
    
    def _selector_matches(self, selector: str, node: DOMNode) -> bool:
        if not node.is_element():
            return False
        try:
            return Selector.parse(selector).matches(node)
        except UnsupportedSelectorError as e:
            self.warnings.warn_unexpected_error(f"Failed to match selector '{selector}': {e}")
            return False
