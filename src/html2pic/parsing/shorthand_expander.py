"""CSS shorthand property expansion."""
from typing import List, Dict


class ShorthandExpander:
    """Expands CSS shorthand properties into individual properties."""
    
    def expand_padding(self, value: str) -> Dict[str, str]:
        values = self._parse_box_values(value)
        return {
            'padding-top': values[0],
            'padding-right': values[1],
            'padding-bottom': values[2],
            'padding-left': values[3]
        }
    
    def expand_margin(self, value: str) -> Dict[str, str]:
        values = self._parse_box_values(value)
        return {
            'margin-top': values[0],
            'margin-right': values[1],
            'margin-bottom': values[2],
            'margin-left': values[3]
        }
    
    def expand_border(self, value: str) -> Dict[str, str]:
        declarations = {}
        parts = self._split_preserving_functions(value)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if any(part.endswith(unit) for unit in ['px', 'em', 'rem', '%']):
                declarations['border-width'] = part
            elif part in ['solid', 'dashed', 'dotted', 'none']:
                declarations['border-style'] = part
            else:
                declarations['border-color'] = part
        
        return declarations
    
    # Tokens of the background shorthand that html2pic does not support (repeat,
    # position, attachment, origin/clip boxes). They are skipped, not mistaken for colors.
    BACKGROUND_IGNORED_KEYWORDS = {
        'repeat', 'no-repeat', 'repeat-x', 'repeat-y', 'space', 'round',
        'left', 'right', 'top', 'bottom', 'center',
        'scroll', 'fixed', 'local',
        'border-box', 'padding-box', 'content-box', 'text',
        'auto', 'cover', 'contain', '/',
    }
    BACKGROUND_IMAGE_FUNCTIONS = (
        'url(', 'linear-gradient(', 'radial-gradient(', 'conic-gradient(',
        'repeating-linear-gradient(', 'repeating-radial-gradient(', 'repeating-conic-gradient(',
    )

    def expand_background(self, value: str) -> Dict[str, str]:
        """Expand the `background` shorthand into background-color and background-image.

        Like in CSS, sub-properties that are not given are reset to their initial values.
        Only the last layer of a multi-layer background may carry a color; html2pic
        renders a single layer, so only the first image is kept.
        """
        declarations = {'background-color': 'transparent', 'background-image': 'none'}
        layers = self._split_top_level(value, ',')
        image_found = False

        for index, layer in enumerate(layers):
            is_last = index == len(layers) - 1
            for part in self._split_preserving_functions(layer):
                lowered = part.lower()
                if lowered.startswith(self.BACKGROUND_IMAGE_FUNCTIONS):
                    if not image_found:
                        declarations['background-image'] = part
                        image_found = True
                elif lowered == 'none':
                    continue
                elif is_last and self._looks_like_color(lowered):
                    declarations['background-color'] = part

        return declarations

    def expand_overflow(self, value: str) -> Dict[str, str]:
        values = value.split() or ['visible']
        return {'overflow-x': values[0], 'overflow-y': values[1] if len(values) > 1 else values[0]}

    def _looks_like_color(self, token: str) -> bool:
        if token in self.BACKGROUND_IGNORED_KEYWORDS or '/' in token:
            return False
        if token.startswith(('#', 'rgb(', 'rgba(', 'hsl(', 'hsla(')):
            return True
        return token.isalpha()

    def _split_top_level(self, value: str, separator: str) -> List[str]:
        parts, current, depth = [], '', 0
        for char in value:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            if char == separator and depth == 0:
                parts.append(current.strip())
                current = ''
            else:
                current += char
        if current.strip():
            parts.append(current.strip())
        return parts

    def _parse_box_values(self, value: str) -> List[str]:
        values = value.split()
        
        if len(values) == 1:
            return [values[0]] * 4
        elif len(values) == 2:
            return [values[0], values[1], values[0], values[1]]
        elif len(values) == 3:
            return [values[0], values[1], values[2], values[1]]
        elif len(values) >= 4:
            return values[:4]
        return ['0px'] * 4
    
    def _split_preserving_functions(self, value: str) -> List[str]:
        parts = []
        current_part = ''
        paren_depth = 0
        
        for char in value:
            if char == '(':
                paren_depth += 1
                current_part += char
            elif char == ')':
                paren_depth -= 1
                current_part += char
            elif char == ' ' and paren_depth == 0:
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = ''
            else:
                current_part += char
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        return parts
