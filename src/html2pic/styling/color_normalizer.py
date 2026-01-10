"""CSS color normalization."""
import re
from ..warnings import get_warning_collector


class ColorNormalizer:
    """Normalizes CSS color values for PicTex compatibility."""
    
    NAMED_COLORS = {
        'black', 'white', 'red', 'green', 'blue', 'yellow', 'purple', 
        'orange', 'gray', 'grey', 'pink', 'brown', 'cyan', 'magenta', 
        'transparent'
    }
    
    def __init__(self):
        self.warnings = get_warning_collector()
    
    def normalize(self, color_value: str) -> str:
        if not isinstance(color_value, str):
            return 'black'
        
        color_value = color_value.strip().lower()
        
        if color_value == 'transparent':
            return 'transparent'
        
        if color_value.startswith('rgba(') or color_value.startswith('rgb('):
            return self._parse_rgba(color_value)
        
        return color_value
    
    def _parse_rgba(self, rgba_string: str) -> str:
        values_str = rgba_string.replace('rgba(', '').replace('rgb(', '').replace(')', '').strip()
        values = [val.strip() for val in values_str.split(',')]
        
        try:
            r = max(0, min(255, int(float(values[0]))))
            g = max(0, min(255, int(float(values[1]))))
            b = max(0, min(255, int(float(values[2]))))
            
            alpha = 1.0
            if len(values) >= 4:
                alpha = float(values[3])
            
            if alpha <= 0.01:
                return 'transparent'
            
            a = int(alpha * 255)
            return f'#{r:02x}{g:02x}{b:02x}{a:02x}'
        except (ValueError, IndexError) as e:
            self.warnings.warn_unexpected_error(f"Failed to parse RGBA color '{rgba_string}': {e}")
            return 'black'
    
    def is_valid(self, color: str) -> bool:
        color = color.strip().lower()
        
        if color in self.NAMED_COLORS:
            return True
        
        if re.match(r'^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$', color):
            return True
        
        if color.startswith(('rgb(', 'rgba(', 'hsl(', 'hsla(')):
            return True
        
        return False
