"""CSS transform style application (translate only)."""
import re
from typing import Dict, Any, Tuple, Optional

from pictex import Element

from .base_applicator import StyleApplicator
from ...warnings import get_warning_collector
from ...styling import DEFAULT_STYLES


class TransformApplicator(StyleApplicator):
    """Applies transform: translate() for anchor-based positioning."""
    
    UNSUPPORTED_TRANSFORMS = ['rotate', 'scale', 'skew', 'matrix', 'perspective']
    
    def __init__(self):
        self.warnings = get_warning_collector()
    
    def apply(self, builder: Element, styles: Dict[str, Any]) -> Element:
        transform = styles.get('transform', DEFAULT_STYLES['transform'])
        
        if transform == 'none' or not transform:
            return builder
        
        transform = transform.strip().lower()
        
        translate_x, translate_y = self._parse_translate(transform)
        print(f"element: {builder}")
        print(f"children: {builder._children}")
        print(f"translate_x: {translate_x}")
        print(f"translate_y: {translate_y}")
        
        if translate_x is not None or translate_y is not None:
            kwargs = {}
            if translate_x is not None:
                kwargs['x'] = translate_x
            if translate_y is not None:
                kwargs['y'] = translate_y
            builder = builder.translate(**kwargs)
        
        self._warn_unsupported(transform)
        
        return builder
    
    def _parse_translate(self, transform: str) -> Tuple[Optional[str], Optional[str]]:
        x, y = None, None
        
        if 'translate(' in transform:
            x, y = self._parse_function(transform, 'translate')
        
        if 'translatex(' in transform:
            parsed_x, _ = self._parse_function(transform, 'translatex')
            if parsed_x is not None:
                x = parsed_x
        
        if 'translatey(' in transform:
            _, parsed_y = self._parse_function(transform, 'translatey')
            if parsed_y is not None:
                y = parsed_y
        
        return x, y
    
    def _parse_function(self, transform: str, func_name: str) -> Tuple[Optional[str], Optional[str]]:
        pattern = rf'{func_name}\s*\(\s*([^)]+)\s*\)'
        match = re.search(pattern, transform, re.IGNORECASE)
        
        if not match:
            return None, None
        
        args = match.group(1)
        parts = [p.strip() for p in args.split(',')]
        
        if func_name == 'translate':
            x = self._parse_value(parts[0]) if len(parts) >= 1 else None
            y = self._parse_value(parts[1]) if len(parts) >= 2 else None
            return x, y
        elif func_name == 'translatex':
            return self._parse_value(parts[0]) if parts else None, None
        elif func_name == 'translatey':
            return None, self._parse_value(parts[0]) if parts else None
        
        return None, None
    
    def _parse_value(self, value: str) -> Optional[str]:
        value = value.strip()
        
        if not value:
            return None
        
        if value.endswith('%'):
            return value
        
        if value.endswith('px'):
            try:
                return str(float(value[:-2]))
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Failed to parse PIXEL value '{value}': {e}")
                return None
        
        if value.endswith('em'):
            try:
                return str(float(value[:-2]) * 16)
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Failed to parse EM value '{value}': {e}")
                return None
        
        if value.endswith('rem'):
            try:
                return str(float(value[:-3]) * 16)
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Failed to parse REM value '{value}': {e}")
                return None
        
        try:
            return str(float(value))
        except ValueError as e:
            self.warnings.warn_unexpected_error(f"Failed to parse value '{value}': {e}")
            return None
    
    def _warn_unsupported(self, transform: str):
        for func in self.UNSUPPORTED_TRANSFORMS:
            if f'{func}(' in transform:
                self.warnings.warn_style_not_applied(
                    'transform', transform, 'element',
                    f"Only translate() is supported. {func}() is not implemented."
                )
                break
