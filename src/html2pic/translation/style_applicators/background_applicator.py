"""Background style application."""
from typing import Dict, Any, List, Tuple, Optional

from pictex import Element, SolidColor, LinearGradient

from .base_applicator import StyleApplicator
from ...warnings import get_warning_collector
from ...styling import DEFAULT_STYLES


class BackgroundApplicator(StyleApplicator):
    """Applies background-color and background-image."""

    def __init__(self):
        self.warnings = get_warning_collector()
    
    def apply(self, builder: Element, styles: Dict[str, Any]) -> Element:
        builder = self._apply_background_color(builder, styles)
        builder = self._apply_background_image(builder, styles)
        return builder
    
    def _apply_background_color(self, builder: Element, styles: Dict[str, Any]) -> Element:
        bg_color = styles.get('background-color', DEFAULT_STYLES['background-color'])
        if bg_color != 'transparent':
            try:
                color = SolidColor.from_str(bg_color)
                builder = builder.background_color(color)
            except Exception as e:
                self.warnings.warn_unexpected_error(f"Failed to apply background-color '{bg_color}': {e}")
        return builder
    
    def _apply_background_image(self, builder: Element, styles: Dict[str, Any]) -> Element:
        bg_image = styles.get('background-image', DEFAULT_STYLES['background-image'])
        
        if bg_image == 'none':
            return builder
        
        if bg_image.startswith('linear-gradient('):
            gradient = self._parse_gradient(bg_image)
            if gradient:
                builder = builder.background_color(gradient)
        elif bg_image.startswith('url('):
            url = self._extract_url(bg_image)
            if url:
                size = styles.get('background-size', DEFAULT_STYLES['background-size'])
                builder = builder.background_image(url, size)
        
        return builder
    
    def _parse_gradient(self, gradient_str: str) -> Optional[LinearGradient]:
        try:
            content = gradient_str[16:-1].strip()
            parts = self._split_gradient_parts(content)
            
            direction_mapping = {
                'to right': ((0.0, 0.5), (1.0, 0.5)),
                'to left': ((1.0, 0.5), (0.0, 0.5)),
                'to bottom': ((0.5, 0.0), (0.5, 1.0)),
                'to top': ((0.5, 1.0), (0.5, 0.0)),
                'to bottom right': ((0.0, 0.0), (1.0, 1.0)),
                'to bottom left': ((1.0, 0.0), (0.0, 1.0)),
                'to top right': ((0.0, 1.0), (1.0, 0.0)),
                'to top left': ((1.0, 1.0), (0.0, 0.0)),
            }
            
            start_point = (0.5, 0.0)
            end_point = (0.5, 1.0)
            color_parts = parts
            
            if parts:
                first_part = parts[0].strip().lower()
                
                if first_part in direction_mapping:
                    start_point, end_point = direction_mapping[first_part]
                    color_parts = parts[1:]
                elif first_part.endswith('deg'):
                    start_point, end_point = self._angle_to_points(first_part)
                    color_parts = parts[1:]
            
            colors = []
            stops = []
            for i, part in enumerate(color_parts):
                color_str, position = self._parse_color_stop(part.strip(), i, len(color_parts))
                try:
                    color = SolidColor.from_str(color_str)
                    colors.append(color)
                    stops.append(position)
                except Exception as e:
                    self.warnings.warn_unexpected_error(f"Failed to parse color stop '{color_str}': {e}")
            
            if len(colors) >= 2:
                return LinearGradient(colors, stops, start_point, end_point)
        except Exception as e:
            self.warnings.warn_unexpected_error(f"Failed to parse gradient '{gradient_str}': {e}")
        return None
    
    def _angle_to_points(self, angle_str: str) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        import math
        try:
            angle = float(angle_str[:-3])
            rad = math.radians(angle - 90)
            
            x = 0.5 + 0.5 * math.cos(rad)
            y = 0.5 + 0.5 * math.sin(rad)
            
            start_x = 0.5 - 0.5 * math.cos(rad)
            start_y = 0.5 - 0.5 * math.sin(rad)
            
            return ((start_x, start_y), (x, y))
        except:
            return ((0.5, 0.0), (0.5, 1.0))
    
    def _split_gradient_parts(self, content: str) -> List[str]:
        parts = []
        current = ''
        paren_depth = 0
        
        for char in content:
            if char == '(':
                paren_depth += 1
                current += char
            elif char == ')':
                paren_depth -= 1
                current += char
            elif char == ',' and paren_depth == 0:
                parts.append(current.strip())
                current = ''
            else:
                current += char
        
        if current.strip():
            parts.append(current.strip())
        
        return parts
    
    def _parse_color_stop(self, stop_str: str, index: int, total: int) -> Tuple[str, float]:
        parts = stop_str.rsplit(None, 1)
        
        if len(parts) == 2 and (parts[1].endswith('%') or parts[1].endswith('px')):
            color = parts[0]
            if parts[1].endswith('%'):
                position = float(parts[1][:-1]) / 100
            else:
                position = index / max(1, total - 1)
        else:
            color = stop_str
            position = index / max(1, total - 1)
        
        return color, position
    
    def _extract_url(self, url_str: str) -> str:
        content = url_str[4:-1].strip()
        if (content.startswith('"') and content.endswith('"')) or \
           (content.startswith("'") and content.endswith("'")):
            content = content[1:-1]
        return content
