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
