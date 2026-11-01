"""CSS color normalization."""
import colorsys
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
        
        if color_value.startswith(('rgba(', 'rgb(')):
            return self._parse_rgba(color_value)
        
        if color_value.startswith(('hsla(', 'hsl(')):
            return self._parse_hsla(color_value)
        
        return color_value
    
    def _split_args(self, func_string: str):
        """Split the arguments of rgb()/hsl() in either legacy (commas) or modern (spaces, '/') syntax."""
        inner = func_string[func_string.index('(') + 1:func_string.rindex(')')]
        alpha = None
        if '/' in inner:
            inner, alpha = inner.split('/', 1)
            alpha = alpha.strip()
        parts = [p for p in inner.replace(',', ' ').split() if p]
        if alpha is None and len(parts) == 4:
            alpha = parts.pop()
        return parts, alpha
    
    @staticmethod
    def _parse_alpha(alpha) -> float:
        if alpha is None:
            return 1.0
        if alpha.endswith('%'):
            return max(0.0, min(1.0, float(alpha[:-1]) / 100))
        return max(0.0, min(1.0, float(alpha)))
    
    @staticmethod
    def _to_hex(r: float, g: float, b: float, alpha: float) -> str:
        if alpha <= 0.01:
            return 'transparent'
        channels = [max(0, min(255, int(round(c)))) for c in (r, g, b)]
        return '#{:02x}{:02x}{:02x}{:02x}'.format(*channels, int(alpha * 255))
    
    def _parse_rgba(self, rgba_string: str) -> str:
        try:
            parts, alpha = self._split_args(rgba_string)
            if len(parts) != 3:
                raise ValueError(f"expected 3 color channels, got {len(parts)}")
            channels = [
                float(p[:-1]) * 255 / 100 if p.endswith('%') else float(p)
                for p in parts
            ]
            return self._to_hex(*channels, self._parse_alpha(alpha))
        except ValueError as e:
            self.warnings.warn_unexpected_error(f"Failed to parse RGBA color '{rgba_string}': {e}")
            return 'black'
    
    def _parse_hsla(self, hsla_string: str) -> str:
        try:
            parts, alpha = self._split_args(hsla_string)
            if len(parts) != 3:
                raise ValueError(f"expected 3 components, got {len(parts)}")
            hue = parts[0]
            if hue.endswith('deg'):
                hue = hue[:-3]
            h = (float(hue) % 360) / 360
            s = max(0.0, min(1.0, float(parts[1].rstrip('%')) / 100))
            l = max(0.0, min(1.0, float(parts[2].rstrip('%')) / 100))
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            return self._to_hex(r * 255, g * 255, b * 255, self._parse_alpha(alpha))
        except ValueError as e:
            self.warnings.warn_unexpected_error(f"Failed to parse HSLA color '{hsla_string}': {e}")
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
