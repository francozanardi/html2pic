from typing import Dict, Any, List, Optional

from pictex import Element, SolidColor

from .base_applicator import StyleApplicator
from ...fonts import FontRegistry
from ...warnings import get_warning_collector
from ...styling.default_styles import DEFAULT_STYLES
from ..shadow_parser import ShadowParser

class TypographyApplicator(StyleApplicator):
    
    def __init__(self, font_registry: FontRegistry = None):
        self.font_registry = font_registry
        self.warnings = get_warning_collector()
        self.shadow_parser = ShadowParser(self.warnings)
    
    def apply(self, builder: Element, styles: Dict[str, Any]) -> Element:
        builder = self._apply_font_family(builder, styles)
        builder = self._apply_font_size(builder, styles)
        builder = self._apply_font_weight(builder, styles)
        builder = self._apply_font_style(builder, styles)
        builder = self._apply_text_color(builder, styles)
        builder = self._apply_text_align(builder, styles)
        builder = self._apply_line_height(builder, styles)
        builder = self._apply_text_wrap(builder, styles)
        builder = self._apply_text_shadow(builder, styles)
        return builder
    
    def _apply_font_family(self, builder: Element, styles: Dict[str, Any]) -> Element:
        font_family = styles.get('font-family', DEFAULT_STYLES['font-family'])
        font_weight = styles.get('font-weight', DEFAULT_STYLES['font-weight'])
        font_style = styles.get('font-style', DEFAULT_STYLES['font-style'])
        
        weight_str = self._normalize_weight(font_weight)
        
        if self.font_registry:
            font_list = self.font_registry.resolve_font_family(font_family, weight_str, font_style)
        else:
            font_list = [name.strip().strip('"\'') for name in font_family.split(',')]
        
        if len(font_list) > 1:
            builder = builder.font_family(font_list[0])
            builder = builder.font_fallbacks(*font_list[1:])
        elif font_list:
            builder = builder.font_family(font_list[0])
        
        return builder
    
    def _apply_font_size(self, builder: Element, styles: Dict[str, Any]) -> Element:
        font_size = styles.get('font-size', DEFAULT_STYLES['font-size'])
        if font_size.endswith('px'):
            try:
                builder = builder.font_size(float(font_size[:-2]))
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Unable to apply font size {font_size}: {str(e)}")
        return builder
    
    def _apply_font_weight(self, builder: Element, styles: Dict[str, Any]) -> Element:
        font_weight = styles.get('font-weight', DEFAULT_STYLES['font-weight'])
        weight_str = self._normalize_weight(font_weight)
        
        try:
            weight = int(weight_str)
            builder = builder.font_weight(weight)
        except ValueError as e:
            self.warnings.warn_unexpected_error(f"Unable to apply font weight {font_weight}: {str(e)}")
        
        return builder
    
    def _apply_font_style(self, builder: Element, styles: Dict[str, Any]) -> Element:
        font_style = styles.get('font-style', DEFAULT_STYLES['font-style'])
        if font_style == 'italic':
            builder = builder.font_style('italic')
        return builder
    
    def _apply_text_color(self, builder: Element, styles: Dict[str, Any]) -> Element:
        color = styles.get('color', DEFAULT_STYLES['color'])

        try:
            color_obj = SolidColor.from_str(color)
            builder = builder.color(color_obj)
        except Exception as e:
            self.warnings.warn_unexpected_error(f"Unable to apply text color {color}: {str(e)}")
        return builder
    
    def _apply_text_align(self, builder: Element, styles: Dict[str, Any]) -> Element:
        text_align = styles.get('text-align', DEFAULT_STYLES['text-align'])
        if text_align in ['left', 'center', 'right', 'justify']:
            builder = builder.text_align(text_align)
        return builder
    
    def _apply_line_height(self, builder: Element, styles: Dict[str, Any]) -> Element:
        line_height = styles.get('line-height', DEFAULT_STYLES['line-height'])
        try:
            if line_height.endswith('px'):
                builder = builder.line_height(float(line_height[:-2]))
            else:
                builder = builder.line_height(float(line_height))
        except ValueError as e:
            self.warnings.warn_unexpected_error(f"Unable to apply line height {line_height}: {str(e)}")
        return builder
    
    def _apply_text_wrap(self, builder: Element, styles: Dict[str, Any]) -> Element:
        text_wrap = styles.get('text-wrap', DEFAULT_STYLES['text-wrap'])
        wrap_mapping = {
            'wrap': 'normal',
            'normal': 'normal',
            'nowrap': 'nowrap',
            'balance': 'normal',
        }
        if text_wrap in wrap_mapping:
            builder = builder.text_wrap(wrap_mapping[text_wrap])
        return builder
    
    def _apply_text_shadow(self, builder: Element, styles: Dict[str, Any]) -> Element:
        text_shadow = styles.get('text-shadow', DEFAULT_STYLES['text-shadow'])
        if text_shadow != 'none':
            shadows = self.shadow_parser.parse_shadows(text_shadow, include_spread=False)
            if shadows:
                builder = builder.text_shadows(*shadows)
        return builder
    
    def _normalize_weight(self, weight: str) -> str:
        if weight.isdigit():
            return weight
        weight_map = {'bold': '700', 'bolder': '700', 'normal': '400', 'lighter': '300'}
        return weight_map.get(weight, DEFAULT_STYLES['font-weight'])

