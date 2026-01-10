"""CSS positioning style application."""
from typing import Dict, Any, Union, Optional

from pictex import Element

from .base_applicator import StyleApplicator
from ...warnings import get_warning_collector
from ...styling import DEFAULT_STYLES


class PositioningApplicator(StyleApplicator):
    """Applies position: static, relative, absolute, fixed."""
    
    def __init__(self):
        self.warnings = get_warning_collector()
    
    def apply(self, builder: Element, styles: Dict[str, Any]) -> Element:
        position = styles.get('position', DEFAULT_STYLES['position'])
        
        if position == 'static':
            return builder
        
        insets = self._get_inset_values(styles)
        
        if not insets:
            return builder
        
        if position == 'absolute':
            builder = builder.absolute_position(**insets)
        elif position == 'relative':
            builder = builder.relative_position(**insets)
        elif position == 'fixed':
            builder = builder.fixed_position(**insets)
        else:
            self.warnings.warn_style_not_applied(
                'position', position, 'element',
                f"Position '{position}' is not supported."
            )
        
        return builder
    
    def _get_inset_values(self, styles: Dict[str, Any]) -> Dict[str, Union[float, str]]:
        insets = {}
        
        for prop in ['top', 'right', 'bottom', 'left']:
            value = styles.get(prop, DEFAULT_STYLES[prop])
            if value != 'auto':
                parsed = self._parse_value(value)
                if parsed is not None:
                    insets[prop] = parsed
        
        return insets
    
    def _parse_value(self, value: str) -> Optional[Union[float, str]]:
        if value == 'auto':
            return None
        
        if value.endswith('px'):
            try:
                return float(value[:-2])
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Failed to parse PIXEL value '{value}': {e}")
                return None
        
        if value.endswith('%'):
            return value
        
        if value.endswith('em'):
            try:
                return float(value[:-2]) * 16
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Failed to parse EM value '{value}': {e}")
                return None
        
        if value.endswith('rem'):
            try:
                return float(value[:-3]) * 16
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Failed to parse REM value '{value}': {e}")
                return None
        
        try:
            return float(value)
        except ValueError as e:
            self.warnings.warn_unexpected_error(f"Failed to parse value '{value}': {e}")
            return None
