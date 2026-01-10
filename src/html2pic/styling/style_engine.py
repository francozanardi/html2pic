"""Style computation engine."""
from typing import List, Dict, Any

from ..dom import DOMNode
from ..parsing import CSSRule
from ..fonts import FontRegistry
from ..warnings import get_warning_collector
from .default_styles import DEFAULT_STYLES
from .unit_converter import UnitConverter
from .color_normalizer import ColorNormalizer
from .cascade_resolver import CascadeResolver


class StyleEngine:
    """Computes final styles for DOM nodes by applying CSS rules."""
    
    INHERITED_PROPERTIES = {
        'color', 'font-family', 'font-size', 'font-weight', 'font-style',
        'line-height', 'text-align', 'text-decoration', 'text-wrap'
    }
    
    def __init__(self, base_font_size: int = 16):
        self.base_font_size = base_font_size
        self.warnings = get_warning_collector()
        self.font_registry: FontRegistry = None
        self.unit_converter = UnitConverter(base_font_size)
        self.color_normalizer = ColorNormalizer()
        self.cascade_resolver = CascadeResolver()
    
    def apply_styles(
        self, 
        dom_tree: DOMNode, 
        css_rules: List[CSSRule], 
        font_registry: FontRegistry = None
    ) -> DOMNode:
        """Apply CSS rules to a DOM tree, computing final styles for each node."""
        self.font_registry = font_registry
        self._apply_recursive(dom_tree, css_rules, {})
        return dom_tree
    
    def _apply_recursive(
        self, 
        node: DOMNode, 
        css_rules: List[CSSRule], 
        parent_styles: Dict[str, Any]
    ):
        computed = DEFAULT_STYLES.copy()
        
        for prop in self.INHERITED_PROPERTIES:
            if prop in parent_styles:
                computed[prop] = parent_styles[prop]
        
        matching_rules = self.cascade_resolver.find_matching_rules(node, css_rules)
        matching_rules.sort(key=lambda r: r.specificity)
        
        for rule in matching_rules:
            for prop, value in rule.declarations.items():
                computed[prop] = value
        
        computed = self._normalize(computed, parent_styles)
        node.computed_styles = computed
        
        for child in node.children:
            self._apply_recursive(child, css_rules, computed)
    
    def _normalize(self, styles: Dict[str, Any], parent_styles: Dict[str, Any]) -> Dict[str, Any]:
        normalized = styles.copy()
        
        if 'font-size' in normalized:
            normalized['font-size'] = self.unit_converter.to_pixels(
                normalized['font-size'],
                parent_styles.get('font-size', f'{self.base_font_size}px')
            )
        
        length_properties = [
            'width', 'height', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
            'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
            'border-width', 'border-radius', 'border-top-left-radius', 'border-top-right-radius',
            'border-bottom-left-radius', 'border-bottom-right-radius', 'gap'
        ]
        
        for prop in length_properties:
            if prop in normalized:
                normalized[prop] = self.unit_converter.to_pixels(
                    normalized[prop],
                    parent_styles.get(prop, '0px'),
                    normalized.get('font-size', f'{self.base_font_size}px')
                )
        
        normalized['display'] = self._normalize_display(normalized.get('display', 'block'))
        
        for color_prop in ['color', 'background-color', 'border-color']:
            if color_prop in normalized:
                normalized[color_prop] = self.color_normalizer.normalize(normalized[color_prop])
        
        return normalized
    
    def _normalize_display(self, display_value: str) -> str:
        display_value = display_value.strip().lower()
        
        if display_value == 'none':
            return 'none'
        elif display_value == 'flex':
            return 'flex'
        elif display_value in ['block', 'div']:
            return 'block'
        elif display_value in ['inline', 'inline-block', 'span']:
            return 'inline'

        self.warnings.warn_message(f"Unsupported display value: {display_value}")
        return 'block'
