"""Shadow style application."""
from typing import Dict, Any, List, Optional

from pictex import Element, SolidColor, Shadow

from .base_applicator import StyleApplicator
from ...warnings import get_warning_collector
from ...styling import DEFAULT_STYLES


class ShadowApplicator(StyleApplicator):
    """Applies box-shadow styles."""
    
    def __init__(self):
        self.warnings = get_warning_collector()
    
    def apply(self, builder: Element, styles: Dict[str, Any]) -> Element:
        box_shadow = styles.get('box-shadow', DEFAULT_STYLES['box-shadow'])
        if box_shadow == 'none':
            return builder
        
        shadows = self._parse_shadows(box_shadow)
        if shadows:
            builder = builder.box_shadows(*shadows)
        
        return builder
    
    def _parse_shadows(self, shadow_str: str) -> List[Shadow]:
        shadows = []
        shadow_parts = self._split_shadows(shadow_str)
        
        for part in shadow_parts:
            shadow = self._parse_single_shadow(part.strip())
            if shadow:
                shadows.append(shadow)
        
        return shadows
    
    def _split_shadows(self, shadow_str: str) -> List[str]:
        parts = []
        current = ''
        paren_depth = 0
        
        for char in shadow_str:
            if char == '(':
                paren_depth += 1
                current += char
            elif char == ')':
                paren_depth -= 1
                current += char
            elif char == ',' and paren_depth == 0:
                if current.strip():
                    parts.append(current.strip())
                current = ''
            else:
                current += char
        
        if current.strip():
            parts.append(current.strip())
        
        return parts
    
    def _parse_single_shadow(self, shadow_str: str) -> Optional[Shadow]:
        tokens = self._tokenize(shadow_str)
        
        offset_x = 0.0
        offset_y = 0.0
        blur = 0.0
        spread = 0.0
        color = 'rgba(0,0,0,0.3)'
        
        numeric_values = []
        color_parts = []
        
        for token in tokens:
            if self._is_length(token):
                numeric_values.append(self._parse_length(token))
            else:
                color_parts.append(token)
        
        if len(numeric_values) >= 2:
            offset_x = numeric_values[0]
            offset_y = numeric_values[1]
        if len(numeric_values) >= 3:
            blur = numeric_values[2]
        if len(numeric_values) >= 4:
            spread = numeric_values[3]
        
        if color_parts:
            color = ' '.join(color_parts)
        
        try:
            color_obj = SolidColor.from_str(color)
            return Shadow(offset_x, offset_y, blur, spread, color_obj)
        except Exception as e:
            self.warnings.warn_unexpected_error(f"Failed to apply shadow '{shadow_str}': {e}")
            return None
    
    def _tokenize(self, s: str) -> List[str]:
        tokens = []
        current = ''
        paren_depth = 0
        
        for char in s:
            if char == '(':
                paren_depth += 1
                current += char
            elif char == ')':
                paren_depth -= 1
                current += char
            elif char == ' ' and paren_depth == 0:
                if current.strip():
                    tokens.append(current.strip())
                current = ''
            else:
                current += char
        
        if current.strip():
            tokens.append(current.strip())
        
        return tokens
    
    def _is_length(self, token: str) -> bool:
        return any(token.endswith(u) for u in ['px', 'em', 'rem', '%']) or \
               token.lstrip('-').replace('.', '').isdigit()
    
    def _parse_length(self, value: str) -> float:
        for suffix in ['px', 'em', 'rem', '%']:
            if value.endswith(suffix):
                try:
                    return float(value[:-len(suffix)])
                except ValueError as e:
                    self.warnings.warn_unexpected_error(f"Failed to parse length '{value}': {e}")
                    return 0
        try:
            return float(value)
        except ValueError as e:
            self.warnings.warn_unexpected_error(f"Failed to parse length '{value}': {e}")
            return 0
