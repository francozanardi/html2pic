"""CSS unit conversion utilities."""

from ..warnings import get_warning_collector

class UnitConverter:
    """Converts CSS units to pixels."""
    
    def __init__(self, base_font_size: int = 16):
        self.base_font_size = base_font_size
        self.warnings = get_warning_collector()
    
    def to_pixels(
        self, 
        value: str, 
        parent_value: str = '0px',
        font_size: str = None
    ) -> str:
        """Convert CSS length value to pixels."""
        if not isinstance(value, str):
            return str(value)
        
        value = value.strip().lower()
        font_size = font_size or f'{self.base_font_size}px'
        
        if value.endswith('px') or value in ['auto', 'none', 'inherit', 'initial']:
            return value
        
        if value.endswith('em'):
            try:
                em_value = float(value[:-2])
                base_size = float(font_size.rstrip('px')) if font_size.endswith('px') else self.base_font_size
                return f'{em_value * base_size}px'
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Failed to convert EM value '{value}': {e}")
                return value
        
        if value.endswith('rem'):
            try:
                rem_value = float(value[:-3])
                return f'{rem_value * self.base_font_size}px'
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Failed to convert REM value '{value}': {e}")
                return value
        
        if value.endswith('%'):
            try:
                percent_value = float(value[:-1])
                if parent_value.endswith('px'):
                    parent_px = float(parent_value[:-2])
                    return f'{(percent_value / 100) * parent_px}px'
                return value
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Failed to convert PERCENT value '{value}': {e}")
                return value
        
        try:
            float_val = float(value)
            return f'{float_val}px'
        except ValueError as e:
            self.warnings.warn_unexpected_error(f"Failed to convert value '{value}': {e}")
            return value
