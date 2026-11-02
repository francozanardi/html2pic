"""Spacing style application (padding, margin)."""
from typing import Dict, Any, List

from pictex import Element

from .base_applicator import StyleApplicator
from ...styling import DEFAULT_STYLES
from ...warnings import get_warning_collector


class SpacingApplicator(StyleApplicator):
    """Applies padding and margin styles."""
    
    def __init__(self):
        self.warnings = get_warning_collector()
    
    def apply(self, builder: Element, styles: Dict[str, Any]) -> Element:
        builder = self._apply_padding(builder, styles)
        builder = self._apply_margin(builder, styles)
        return builder
    
    def _apply_padding(self, builder: Element, styles: Dict[str, Any]) -> Element:
        values = self._get_box_values(styles, 'padding')
        return self._apply_box_spacing(builder, values, builder.padding, 'padding')
    
    def _apply_margin(self, builder: Element, styles: Dict[str, Any]) -> Element:
        values = self._get_box_values(styles, 'margin')
        return self._apply_box_spacing(builder, values, builder.margin, 'margin')
    
    def _get_box_values(self, styles: Dict[str, Any], prefix: str) -> List[str]:
        return [
            styles.get(f'{prefix}-top', DEFAULT_STYLES[f'{prefix}-top']),
            styles.get(f'{prefix}-right', DEFAULT_STYLES[f'{prefix}-right']),
            styles.get(f'{prefix}-bottom', DEFAULT_STYLES[f'{prefix}-bottom']),
            styles.get(f'{prefix}-left', DEFAULT_STYLES[f'{prefix}-left']),
        ]
    
    def _apply_box_spacing(self, builder: Element, values: List[str], method, prop: str) -> Element:
        pixels = []
        for v in values:
            if v.endswith('px'):
                pixels.append(float(v[:-2]))
            else:
                if v.endswith('%'):
                    self.warnings.warn_style_not_applied(
                        prop, v, 'element', "Percentage values are not supported; use px, em or rem."
                    )
                pixels.append(0)
        
        if all(p == 0 for p in pixels):
            return builder
        
        if all(p == pixels[0] for p in pixels):
            return method(pixels[0])
        elif pixels[0] == pixels[2] and pixels[1] == pixels[3]:
            return method(pixels[0], pixels[1])
        else:
            return method(pixels[0], pixels[1], pixels[2], pixels[3])
