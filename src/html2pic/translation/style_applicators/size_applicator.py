"""Size-related style application."""
from typing import Dict, Any, Union, Optional

from pictex import Element

from .base_applicator import StyleApplicator
from ...warnings import get_warning_collector
from ...styling import DEFAULT_STYLES


class SizeApplicator(StyleApplicator):
    """Applies width, height, min/max constraints, and aspect-ratio."""
    
    def __init__(self):
        self.warnings = get_warning_collector()
    
    def apply(self, builder: Element, styles: Dict[str, Any]) -> Element:
        builder = self._apply_dimensions(builder, styles)
        builder = self._apply_constraints(builder, styles)
        builder = self._apply_aspect_ratio(builder, styles)
        builder = self._apply_flex_item(builder, styles)
        return builder
    
    def _apply_dimensions(self, builder: Element, styles: Dict[str, Any]) -> Element:
        width = styles.get('width', DEFAULT_STYLES['width'])
        height = styles.get('height', DEFAULT_STYLES['height'])
        
        if width == 'auto' and height == 'auto':
            return builder
        
        width_val = self._parse_dimension(width)
        height_val = self._parse_dimension(height)
        
        if width_val is not None or height_val is not None:
            builder = builder.size(width_val, height_val)
        
        return builder
    
    def _apply_constraints(self, builder: Element, styles: Dict[str, Any]) -> Element:
        constraints = [
            ('min-width', DEFAULT_STYLES['min-width'], 'min_width'),
            ('max-width', DEFAULT_STYLES['max-width'], 'max_width'),
            ('min-height', DEFAULT_STYLES['min-height'], 'min_height'),
            ('max-height', DEFAULT_STYLES['max-height'], 'max_height'),
        ]
        
        for css_prop, default, method in constraints:
            value = styles.get(css_prop, default)
            if value != default:
                parsed = self._parse_constraint(value)
                if parsed is not None:
                    builder = getattr(builder, method)(parsed)
        
        return builder
    
    def _apply_aspect_ratio(self, builder: Element, styles: Dict[str, Any]) -> Element:
        aspect_ratio = styles.get('aspect-ratio', DEFAULT_STYLES['aspect-ratio'])
        if aspect_ratio == 'auto':
            return builder
        
        try:
            if '/' in aspect_ratio:
                parts = aspect_ratio.split('/')
                ratio = float(parts[0].strip()) / float(parts[1].strip())
            else:
                ratio = float(aspect_ratio)
            builder = builder.aspect_ratio(ratio)
        except (ValueError, ZeroDivisionError) as e:
            self.warnings.warn_unexpected_error(f"Failed to apply aspect ratio '{aspect_ratio}': {e}")
        
        return builder
    
    def _apply_flex_item(self, builder: Element, styles: Dict[str, Any]) -> Element:
        flex_grow = styles.get('flex-grow', DEFAULT_STYLES['flex-grow'])
        if flex_grow not in ('auto', '0'):
            try:
                builder = builder.flex_grow(float(flex_grow))
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Failed to apply flex grow '{flex_grow}': {e}")
        
        flex_shrink = styles.get('flex-shrink', DEFAULT_STYLES['flex-shrink'])
        if flex_shrink not in ('auto', '1'):
            try:
                builder = builder.flex_shrink(float(flex_shrink))
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Failed to apply flex shrink '{flex_shrink}': {e}")
        
        align_self = styles.get('align-self', DEFAULT_STYLES['align-self'])
        if align_self != 'auto':
            mapping = {
                'flex-start': 'start', 'start': 'start',
                'center': 'center',
                'flex-end': 'end', 'end': 'end',
                'stretch': 'stretch'
            }
            if align_self in mapping:
                builder = builder.align_self(mapping[align_self])
        
        return builder
    
    def _parse_dimension(self, value: str) -> Optional[Union[float, str]]:
        if value == 'auto':
            return None
        if value.endswith('px'):
            return float(value[:-2])
        if value.endswith('%'):
            return value
        if value in ['fit-content', 'fit-background-image']:
            return value
        return None
    
    def _parse_constraint(self, value: str) -> Optional[Union[float, str]]:
        if value in ['auto', 'none']:
            return None
        if value.endswith('px'):
            return float(value[:-2])
        if value.endswith('%'):
            return value
        if value.endswith('em'):
            return float(value[:-2]) * 16
        if value.endswith('rem'):
            return float(value[:-3]) * 16
        return None
