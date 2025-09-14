"""
Style computation engine - handles cascading, specificity, and inheritance
"""

from typing import List, Dict, Any
from .models import DOMNode, CSSRule, ParsedSelector, SelectorType, DEFAULT_STYLES, FontRegistry
from pictex import SolidColor
from .warnings_system import get_warning_collector, WarningCategory

class StyleEngine:
    """
    Computes final styles for DOM nodes by applying CSS rules.
    
    Handles:
    - Selector matching (which rules apply to which elements)
    - Cascade resolution (specificity, source order)
    - Property inheritance (color, font-family, etc.)
    - Unit conversion (px, em, %, etc.)
    """
    
    # Properties that inherit from parent to child
    INHERITED_PROPERTIES = {
        'color', 'font-family', 'font-size', 'font-weight', 'font-style',
        'line-height', 'text-align', 'text-decoration', 'text-wrap'
    }
    
    def __init__(self, base_font_size: int = 16):
        """
        Initialize the style engine.

        Args:
            base_font_size: Base font size in pixels for em/rem calculations
        """
        self.base_font_size = base_font_size
        self.warnings = get_warning_collector()
        self.font_registry: FontRegistry = None
    
    def apply_styles(self, dom_tree: DOMNode, css_rules: List[CSSRule], font_registry: FontRegistry = None) -> DOMNode:
        """
        Apply CSS rules to a DOM tree, computing final styles for each node.

        Args:
            dom_tree: Root DOM node
            css_rules: List of parsed CSS rules
            font_registry: FontRegistry containing @font-face declarations

        Returns:
            DOM tree with computed_styles populated
        """
        # Store font registry for use in font resolution
        self.font_registry = font_registry

        # Apply styles recursively, starting from root
        self._apply_styles_recursive(dom_tree, css_rules, parent_styles={})
        return dom_tree
    
    def _apply_styles_recursive(self, node: DOMNode, css_rules: List[CSSRule], parent_styles: Dict[str, Any]):
        """
        Recursively apply styles to a node and its children.
        
        Args:
            node: Current DOM node
            css_rules: CSS rules to apply
            parent_styles: Computed styles from parent node (for inheritance)
        """
        # Start with default styles
        computed_styles = DEFAULT_STYLES.copy()
        
        # Apply inherited styles from parent
        for prop in self.INHERITED_PROPERTIES:
            if prop in parent_styles:
                computed_styles[prop] = parent_styles[prop]
        
        # Find matching CSS rules for this node
        matching_rules = self._find_matching_rules(node, css_rules)
        
        # Sort by specificity (lowest to highest) for proper cascade
        matching_rules.sort(key=lambda rule: rule.specificity)
        
        # Apply each matching rule's declarations
        for rule in matching_rules:
            for prop, value in rule.declarations.items():
                computed_styles[prop] = value
        
        # Convert units and normalize values
        computed_styles = self._normalize_styles(computed_styles, parent_styles)
        
        # Store computed styles on the node
        node.computed_styles = computed_styles
        
        # Recursively apply to children
        for child in node.children:
            self._apply_styles_recursive(child, css_rules, computed_styles)
    
    def _find_matching_rules(self, node: DOMNode, css_rules: List[CSSRule]) -> List[CSSRule]:
        """
        Find all CSS rules that match the given DOM node.
        
        Args:
            node: DOM node to match against
            css_rules: List of CSS rules
            
        Returns:
            List of matching CSS rules
        """
        matching_rules = []
        
        for rule in css_rules:
            if self._selector_matches_node(rule.selector, node):
                matching_rules.append(rule)
        
        return matching_rules
    
    def _selector_matches_node(self, selector: str, node: DOMNode) -> bool:
        """
        Check if a CSS selector matches a DOM node.
        
        For now, we only support simple selectors:
        - tag: div, p, h1
        - class: .my-class
        - id: #my-id
        - universal: *
        
        Args:
            selector: CSS selector string
            node: DOM node to test
            
        Returns:
            True if selector matches the node
        """
        if not node.is_element():
            return False
        
        try:
            parsed = ParsedSelector.parse(selector)
            
            if parsed.selector_type == SelectorType.UNIVERSAL:
                return True
            elif parsed.selector_type == SelectorType.TAG:
                return node.tag == parsed.value
            elif parsed.selector_type == SelectorType.CLASS:
                return parsed.value in node.get_classes()
            elif parsed.selector_type == SelectorType.ID:
                return node.get_id() == parsed.value
            else:
                return False
                
        except Exception:
            # If we can't parse the selector, assume it doesn't match
            return False
    
    def _normalize_styles(self, styles: Dict[str, Any], parent_styles: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize and convert style values.
        
        - Convert units (em to px, etc.)
        - Resolve relative values
        - Validate and clean up values
        
        Args:
            styles: Raw style dictionary
            parent_styles: Parent's computed styles (for relative units)
            
        Returns:
            Normalized style dictionary
        """
        normalized = styles.copy()
        
        # Validate CSS values and warn about unexpected ones
        for prop, value in normalized.items():
            if isinstance(value, str):
                self._validate_css_value(prop, value)
        
        # Convert font-size first (needed for em calculations)
        if 'font-size' in normalized:
            normalized['font-size'] = self._convert_to_pixels(
                normalized['font-size'], 
                parent_styles.get('font-size', f'{self.base_font_size}px'),
                'font-size'
            )
        
        # Convert other length values
        length_properties = [
            'width', 'height', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
            'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
            'border-width', 'border-radius', 'border-top-left-radius', 'border-top-right-radius',
            'border-bottom-left-radius', 'border-bottom-right-radius', 'gap'
        ]
        
        for prop in length_properties:
            if prop in normalized:
                normalized[prop] = self._convert_to_pixels(
                    normalized[prop],
                    parent_styles.get(prop, '0px'),
                    prop,
                    font_size=normalized.get('font-size', f'{self.base_font_size}px')
                )
        
        # Normalize display property to our layout system
        normalized['display'] = self._normalize_display(normalized.get('display', 'block'))
        
        # Clean up color values
        for color_prop in ['color', 'background-color', 'border-color']:
            if color_prop in normalized:
                normalized[color_prop] = self._normalize_color(normalized[color_prop])
        
        return normalized
    
    def _convert_to_pixels(self, value: str, parent_value: str = '0px', property_name: str = '', font_size: str = '16px') -> str:
        """
        Convert CSS length values to pixels.
        
        Supports: px, em, rem, %
        For unsupported units or 'auto', returns original value.
        """
        if not isinstance(value, str):
            return str(value)
        
        value = value.strip().lower()
        
        # Already in pixels or special values
        if value.endswith('px') or value in ['auto', 'none', 'inherit', 'initial']:
            return value
        
        # Convert em (relative to font size)
        if value.endswith('em'):
            try:
                em_value = float(value[:-2])
                base_size = float(font_size.rstrip('px')) if font_size.endswith('px') else self.base_font_size
                return f'{em_value * base_size}px'
            except ValueError:
                return value
        
        # Convert rem (relative to root font size)
        if value.endswith('rem'):
            try:
                rem_value = float(value[:-3])
                return f'{rem_value * self.base_font_size}px'
            except ValueError:
                return value
        
        # Convert percentage (depends on property and parent value)
        if value.endswith('%'):
            try:
                percent_value = float(value[:-1])
                if parent_value.endswith('px'):
                    parent_px = float(parent_value[:-2])
                    return f'{(percent_value / 100) * parent_px}px'
                else:
                    return value  # Can't convert without pixel parent value
            except ValueError:
                return value
        
        # If it's just a number, assume pixels
        try:
            float_val = float(value)
            return f'{float_val}px'
        except ValueError:
            return value
    
    def _normalize_display(self, display_value: str) -> str:
        """
        Normalize display property to values we understand.
        
        Maps various CSS display values to our internal system:
        - flex -> flex
        - block, div -> block  
        - inline, span -> inline
        """
        display_value = display_value.strip().lower()
        
        if display_value in ['flex']:
            return 'flex'
        elif display_value in ['block', 'div']:
            return 'block'
        elif display_value in ['inline', 'inline-block', 'span']:
            return 'inline'
        else:
            return 'block'  # Default fallback
    
    def _normalize_color(self, color_value: str) -> str:
        """
        Normalize color values for PicTex compatibility.
        
        Ensures color format is compatible with PicTex's SolidColor.from_str()
        """
        if not isinstance(color_value, str):
            return 'black'
        
        color_value = color_value.strip().lower()
        
        # Handle transparent - PicTex doesn't support rgba, so we'll skip transparent backgrounds
        if color_value == 'transparent':
            return 'transparent'  # Keep as transparent, translator will handle this
        
        # Handle rgba/rgb - extract RGB values and convert to hex
        if color_value.startswith('rgba(') or color_value.startswith('rgb('):
            parsed_color = self._parse_rgba_color(color_value)
            if parsed_color != color_value and parsed_color == 'black':
                # Parsing failed, warn about it
                self.warnings.warn_color_fallback(
                    color_value, 'black', 'Failed to parse RGBA/RGB color'
                )
            return parsed_color
        
        return color_value  # Return as-is for hex codes and named colors
    
    def _validate_css_value(self, property_name: str, value: str) -> bool:
        """
        Validate CSS property values and warn about unexpected values.
        
        Returns True if value is valid, False if invalid (but still allows processing)
        """
        value = value.strip().lower()
        
        # Valid values for specific properties
        valid_values = {
            'display': ['none', 'block', 'inline', 'inline-block', 'flex'],
            'flex-direction': ['row', 'column', 'row-reverse', 'column-reverse'],
            'justify-content': ['flex-start', 'center', 'flex-end', 'space-between', 'space-around', 'space-evenly'],
            'align-items': ['flex-start', 'center', 'flex-end', 'stretch', 'baseline'],
            'text-align': ['left', 'center', 'right', 'justify'],
            'font-weight': ['normal', 'bold', 'bolder', 'lighter', '100', '200', '300', '400', '500', '600', '700', '800', '900'],
            'font-style': ['normal', 'italic', 'oblique'],
            'text-decoration': ['none', 'underline', 'overline', 'line-through'],
            'border-style': ['none', 'solid', 'dashed', 'dotted', 'double'],
            'position': ['static', 'relative', 'absolute', 'fixed', 'sticky'],
            'text-wrap': ['wrap', 'nowrap', 'balance'],
        }
        
        # Check if property has restricted values
        if property_name in valid_values:
            if value not in valid_values[property_name]:
                self.warnings.warn(
                    f"Unexpected value '{value}' for CSS property '{property_name}'. Expected one of: {', '.join(valid_values[property_name])}",
                    WarningCategory.CSS_PARSING,
                    {'property': property_name, 'value': value, 'expected': valid_values[property_name]}
                )
                return False
        
        # Validate length values (px, em, rem, %)
        length_properties = [
            'width', 'height', 'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
            'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
            'border-width', 'border-radius', 'border-top-left-radius', 'border-top-right-radius',
            'border-bottom-left-radius', 'border-bottom-right-radius', 'font-size', 'gap', 'left', 'top'
        ]
        
        if property_name in length_properties and value not in ['auto', 'none', 'inherit', 'initial']:
            # Check if it's a valid length value
            import re
            if not re.match(r'^-?(\d+\.?\d*|\.\d+)(px|em|rem|%|in|cm|mm|pt|pc)$|^\d+$', value):
                self.warnings.warn(
                    f"Invalid length value '{value}' for CSS property '{property_name}'. Expected format: number + unit (px, em, rem, %) or keywords (auto, none)",
                    WarningCategory.CSS_PARSING,
                    {'property': property_name, 'value': value}
                )
                return False
        
        # Validate color values
        color_properties = ['color', 'background-color', 'border-color']
        if property_name in color_properties:
            if not self._is_valid_color(value):
                self.warnings.warn(
                    f"Invalid color value '{value}' for CSS property '{property_name}'",
                    WarningCategory.CSS_PARSING,
                    {'property': property_name, 'value': value}
                )
                return False
        
        return True
    
    def _is_valid_color(self, color: str) -> bool:
        """Check if a color value is valid"""
        color = color.strip().lower()
        
        # Named colors
        named_colors = [
            'black', 'white', 'red', 'green', 'blue', 'yellow', 'purple', 'orange', 
            'gray', 'grey', 'pink', 'brown', 'cyan', 'magenta', 'transparent'
        ]
        
        if color in named_colors:
            return True
        
        # Hex colors
        import re
        if re.match(r'^#([0-9a-f]{3}|[0-9a-f]{6})$', color):
            return True
        
        # RGB/RGBA colors
        if color.startswith('rgb(') or color.startswith('rgba('):
            return True
        
        # HSL colors (not fully supported but valid CSS)
        if color.startswith('hsl(') or color.startswith('hsla('):
            return True
        
        return False
    
    def _parse_rgba_color(self, rgba_string: str) -> str:
        """
        Parse rgba() and rgb() color values and convert to hex format.
        
        Args:
            rgba_string: Color string like 'rgba(255, 0, 0, 0.5)' or 'rgb(255, 0, 0)'
            
        Returns:
            Hex color string like '#ff0000' or 'transparent' for fully transparent colors
        """
        import re
        
        # Remove function name and parentheses, keep only the values
        values_str = rgba_string.replace('rgba(', '').replace('rgb(', '').replace(')', '').strip()
        
        # Split by comma and clean up values
        values = [val.strip() for val in values_str.split(',')]
        
        try:
            # Parse RGB values
            r = int(float(values[0]))
            g = int(float(values[1]))  
            b = int(float(values[2]))
            
            # Parse alpha if present (rgba)
            alpha = 1.0  # Default for rgb()
            if len(values) >= 4:
                alpha = float(values[3])
            
            # Clamp RGB values to 0-255
            r = max(0, min(255, r))
            g = max(0, min(255, g)) 
            b = max(0, min(255, b))
            
            # If fully transparent, return transparent
            if alpha <= 0.01:  # Allow for floating point precision issues
                return 'transparent'
            
            # Convert to hex format
            hex_color = f'#{r:02x}{g:02x}{b:02x}'
            
            # If alpha is less than 1, we could add alpha to hex (RGBA hex)
            # But PicTex might not support it, so for now we ignore partial transparency
            # and just return the RGB part
            return hex_color
            
        except (ValueError, IndexError) as e:
            # If parsing fails, return a sensible default
            return 'black'