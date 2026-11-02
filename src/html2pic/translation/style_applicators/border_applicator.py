"""Border style application."""
from typing import Dict, Any, Union

from pictex import Element, SolidColor, BorderStyle

from .base_applicator import StyleApplicator
from ...warnings import get_warning_collector
from ...styling import DEFAULT_STYLES


class BorderApplicator(StyleApplicator):
    """Applies border width, style, color, and radius."""

    def __init__(self):
        self.warnings = get_warning_collector()
    
    def apply(self, builder: Element, styles: Dict[str, Any]) -> Element:
        builder = self._apply_border(builder, styles)
        builder = self._apply_border_radius(builder, styles)
        return builder
    
    def _apply_border(self, builder: Element, styles: Dict[str, Any]) -> Element:
        width = self._parse_pixels(styles.get('border-width', DEFAULT_STYLES['border-width']))
        if width <= 0:
            return builder
        
        style_str = styles.get('border-style', DEFAULT_STYLES['border-style']).lower()
        style_mapping = {
            'solid': BorderStyle.SOLID,
            'dashed': BorderStyle.DASHED,
            'dotted': BorderStyle.DOTTED,
        }
        border_style = style_mapping.get(style_str, BorderStyle.SOLID)
        
        try:
            color = SolidColor.from_str(styles.get('border-color', DEFAULT_STYLES['border-color']))
            builder = builder.border(width, color, border_style)
        except Exception as e:
            self.warnings.warn_unexpected_error(f"Failed to apply border '{styles.get('border', '0px solid black')}'")
        
        return builder
    
    def _apply_border_radius(self, builder: Element, styles: Dict[str, Any]) -> Element:
        corners = [
            self._parse_radius(styles.get(prop, DEFAULT_STYLES[prop]))
            for prop in (
                'border-top-left-radius', 'border-top-right-radius',
                'border-bottom-right-radius', 'border-bottom-left-radius',
            )
        ]
        general = self._parse_radius(styles.get('border-radius', DEFAULT_STYLES['border-radius']))
        
        if general != 0 and all(c == 0 for c in corners):
            corners = [general] * 4
        
        if all(c == corners[0] for c in corners):
            if corners[0] != 0:
                builder = builder.border_radius(corners[0])
        else:
            builder = builder.border_radius(*corners)
        
        return builder
    
    def _parse_radius(self, value: str) -> Union[float, str]:
        """Return pixels as a float, or a percentage string (PicTex resolves those itself)."""
        value = value.strip()
        if value.endswith('%'):
            try:
                return value if float(value[:-1]) != 0 else 0
            except ValueError:
                self.warnings.warn_unexpected_error(f"Failed to parse PERCENT value '{value}'")
                return 0
        return self._parse_pixels(value)
    
    def _parse_pixels(self, value: str) -> float:
        if value.endswith('px'):
            try:
                return float(value[:-2])
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Failed to parse PIXEL value '{value}': {e}")
                return 0
        return 0
