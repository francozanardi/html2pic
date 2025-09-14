"""
CSS parser using tinycss2 to extract style rules
"""

from typing import List, Dict, Tuple, Optional
import tinycss2
from .models import CSSRule, ParsedSelector, SelectorType, FontFace, FontRegistry
from .exceptions import ParseError
from .warnings_system import get_warning_collector, WarningCategory

class CssParser:
    """
    Parses CSS content into structured rules for the style engine.
    
    Uses tinycss2 for robust CSS parsing and extracts:
    - Selectors (class, id, tag)
    - Declarations (property: value pairs)  
    - Specificity calculations for cascade resolution
    """
    
    def __init__(self):
        self.warnings = get_warning_collector()
        self.font_registry = FontRegistry()
    
    def parse(self, css_content: str) -> Tuple[List[CSSRule], FontRegistry]:
        """
        Parse CSS string into a list of CSS rules and font registry.

        Args:
            css_content: CSS content as string

        Returns:
            Tuple of (List of CSSRule objects, FontRegistry with @font-face declarations)

        Raises:
            ParseError: If CSS parsing fails
        """
        if not css_content.strip():
            return [], self.font_registry

        try:
            # Clear existing font registry
            self.font_registry.clear()

            # Parse CSS with tinycss2
            stylesheet = tinycss2.parse_stylesheet(css_content)

            rules = []
            for rule in stylesheet:
                if hasattr(rule, 'at_keyword') and rule.at_keyword == 'font-face':
                    # This is a @font-face at-rule
                    self._process_font_face_rule(rule)
                elif hasattr(rule, 'prelude') and hasattr(rule, 'content'):
                    # This is a qualified rule (selector + declarations)
                    css_rules = self._process_rule(rule)
                    rules.extend(css_rules)

            return rules, self.font_registry

        except Exception as e:
            raise ParseError(f"Failed to parse CSS: {e}") from e
    
    def _process_rule(self, rule) -> List[CSSRule]:
        """
        Process a tinycss2 QualifiedRule into our CSSRule objects.
        
        Args:
            rule: tinycss2 QualifiedRule object
            
        Returns:
            List of CSSRule objects (one per selector if multiple selectors)
        """
        # Extract selectors from the rule prelude
        selectors = self._extract_selectors(rule.prelude)
        
        # Extract declarations from the rule content
        declarations = self._extract_declarations(rule.content)
        
        # Create a CSSRule for each selector
        css_rules = []
        for selector in selectors:
            specificity = self._calculate_specificity(selector)
            css_rules.append(CSSRule(
                selector=selector.strip(),
                declarations=declarations,
                specificity=specificity
            ))
        
        return css_rules
    
    def _extract_selectors(self, prelude) -> List[str]:
        """
        Extract selector strings from rule prelude.
        
        Handles multiple selectors separated by commas.
        For now, we only support simple selectors.
        """
        selectors = []
        current_selector = []
        
        for token in prelude:
            if token.type == 'literal' and token.value == ',':
                # End of current selector, start next one
                if current_selector:
                    selector_str = ''.join(t.serialize() for t in current_selector).strip()
                    if selector_str:
                        selectors.append(selector_str)
                    current_selector = []
            else:
                current_selector.append(token)
        
        # Add the last selector
        if current_selector:
            selector_str = ''.join(t.serialize() for t in current_selector).strip()
            if selector_str:
                selectors.append(selector_str)
        
        return selectors if selectors else ['*']  # Fallback to universal selector
    
    def _extract_declarations(self, content, skip_validation: bool = False) -> Dict[str, str]:
        """
        Extract property: value declarations from rule content.

        Args:
            content: tinycss2 rule content tokens
            skip_validation: Skip validation for @font-face properties

        Returns:
            Dictionary mapping property names to values
        """
        declarations = {}
        
        # Parse declarations from the content
        declaration_list = tinycss2.parse_declaration_list(content)
        
        for item in declaration_list:
            if hasattr(item, 'name') and hasattr(item, 'value'):
                # This is a Declaration
                property_name = item.name.lower()
                property_value = ''.join(token.serialize() for token in item.value).strip()
                
                # Check for unsupported properties (skip for @font-face)
                if not skip_validation:
                    self._check_unsupported_property(property_name, property_value)
                
                # Handle shorthand properties
                if property_name == 'padding':
                    padding_values = self._parse_shorthand_values(property_value)
                    declarations.update(self._expand_padding(padding_values))
                elif property_name == 'margin':
                    margin_values = self._parse_shorthand_values(property_value)
                    declarations.update(self._expand_margin(margin_values))
                elif property_name == 'border':
                    border_declarations = self._parse_border_shorthand(property_value)
                    declarations.update(border_declarations)
                else:
                    declarations[property_name] = property_value
            elif hasattr(item, 'type') and item.type == 'error':
                # CSS parsing error
                self.warnings.warn(
                    f"CSS parsing error in declaration: {getattr(item, 'message', 'unknown error')}",
                    WarningCategory.CSS_PARSING,
                    {'error_type': 'declaration_error'}
                )
        
        return declarations
    
    def _parse_shorthand_values(self, value: str) -> List[str]:
        """Parse shorthand values like '10px 20px' into individual values."""
        values = value.split()
        
        if len(values) == 1:
            # all sides same
            return [values[0]] * 4
        elif len(values) == 2:
            # vertical, horizontal
            return [values[0], values[1], values[0], values[1]]
        elif len(values) == 3:
            # top, horizontal, bottom
            return [values[0], values[1], values[2], values[1]]
        elif len(values) >= 4:
            # top, right, bottom, left
            return values[:4]
        else:
            return ['0px'] * 4
    
    def _expand_padding(self, values: List[str]) -> Dict[str, str]:
        """Expand padding shorthand into individual properties."""
        return {
            'padding-top': values[0],
            'padding-right': values[1], 
            'padding-bottom': values[2],
            'padding-left': values[3]
        }
    
    def _expand_margin(self, values: List[str]) -> Dict[str, str]:
        """Expand margin shorthand into individual properties."""
        return {
            'margin-top': values[0],
            'margin-right': values[1],
            'margin-bottom': values[2], 
            'margin-left': values[3]
        }
    
    def _parse_border_shorthand(self, value: str) -> Dict[str, str]:
        """Parse border shorthand like '1px solid black' or '2px solid rgba(255, 0, 0, 0.5)'."""
        declarations = {}

        # Split by spaces but preserve function calls like rgba()
        parts = self._split_preserving_functions(value)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check if it's a width (ends with px, em, etc.)
            if any(part.endswith(unit) for unit in ['px', 'em', 'rem', '%']):
                declarations['border-width'] = part
            # Check if it's a style
            elif part in ['solid', 'dashed', 'dotted', 'none']:
                declarations['border-style'] = part
            # Assume it's a color (including rgba(), rgb(), etc.)
            else:
                declarations['border-color'] = part

        return declarations

    def _split_preserving_functions(self, value: str) -> List[str]:
        """
        Split a CSS value by spaces while preserving function calls like rgba().

        Examples:
        - '2px solid black' -> ['2px', 'solid', 'black']
        - '2px solid rgba(255, 0, 0, 0.5)' -> ['2px', 'solid', 'rgba(255, 0, 0, 0.5)']
        """
        parts = []
        current_part = ''
        paren_depth = 0

        i = 0
        while i < len(value):
            char = value[i]

            if char == '(':
                paren_depth += 1
                current_part += char
            elif char == ')':
                paren_depth -= 1
                current_part += char
            elif char == ' ' and paren_depth == 0:
                # Space outside of parentheses - end current part
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = ''
            else:
                current_part += char

            i += 1

        # Add the last part
        if current_part.strip():
            parts.append(current_part.strip())

        return parts
    
    def _calculate_specificity(self, selector: str) -> int:
        """
        Calculate CSS specificity for a selector.
        
        Simplified specificity calculation:
        - ID: 100 points
        - Class: 10 points  
        - Tag: 1 point
        - Universal (*): 0 points
        
        Args:
            selector: CSS selector string
            
        Returns:
            Specificity score as integer
        """
        try:
            parsed = ParsedSelector.parse(selector)
            
            if parsed.selector_type == SelectorType.ID:
                return 100
            elif parsed.selector_type == SelectorType.CLASS:
                return 10
            elif parsed.selector_type == SelectorType.TAG:
                return 1
            else:  # UNIVERSAL
                return 0
                
        except Exception:
            # Fallback for complex selectors we don't support yet
            return 1
    
    def _check_unsupported_property(self, property_name: str, property_value: str):
        """Check if a CSS property is unsupported and warn if so"""
        
        # Properties we fully support
        supported_properties = {
            # Layout
            'display', 'flex-direction', 'justify-content', 'align-items', 'gap',
            # Box model
            'width', 'height', 'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
            'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
            'border', 'border-width', 'border-style', 'border-color', 'border-radius',
            'border-top-left-radius', 'border-top-right-radius', 'border-bottom-left-radius', 'border-bottom-right-radius',
            # Visual
            'background-color', 'background-image', 'background-size', 'box-shadow', 'text-shadow',
            # Typography
            'color', 'font-family', 'font-size', 'font-weight', 'font-style',
            'text-align', 'line-height', 'text-decoration', 'text-wrap',
            # Positioning (absolute only)
            'position', 'left', 'top'
        }
        
        # Properties we partially support or have limitations
        partially_supported = {
            'background': 'Use background-color or background-image instead',
            'font': 'Use individual font properties instead',
            'right': 'Only left/top positioning supported with position absolute',
            'bottom': 'Only left/top positioning supported with position absolute',
        }
        
        if property_name not in supported_properties and property_name not in partially_supported:
            self.warnings.warn_unsupported_css_property(
                property_name, 
                property_value,
                f"Property not supported in html2pic"
            )
        elif property_name in partially_supported:
            self.warnings.warn(
                f"CSS property '{property_name}' has limited support: {partially_supported[property_name]}",
                WarningCategory.CSS_PARSING,
                {'property': property_name, 'value': property_value, 'limitation': partially_supported[property_name]}
            )

    def _process_font_face_rule(self, rule):
        """
        Process a @font-face CSS rule and add it to the font registry.

        Args:
            rule: tinycss2 AtRule object for @font-face
        """
        try:
            # Extract declarations from the @font-face rule (skip validation)
            declarations = self._extract_declarations(rule.content, skip_validation=True)

            # Extract required font-face properties
            font_family = declarations.get('font-family', '').strip('"\'')
            src = declarations.get('src', '')

            if not font_family:
                self.warnings.warn(
                    "@font-face rule missing font-family property",
                    WarningCategory.CSS_PARSING,
                    {'rule_type': 'font-face', 'issue': 'missing_font_family'}
                )
                return

            if not src:
                self.warnings.warn(
                    f"@font-face rule for '{font_family}' missing src property",
                    WarningCategory.CSS_PARSING,
                    {'rule_type': 'font-face', 'font_family': font_family, 'issue': 'missing_src'}
                )
                return

            # Parse src property to extract font file path
            font_src = self._parse_font_src(src)
            if not font_src:
                self.warnings.warn(
                    f"@font-face rule for '{font_family}' has invalid src: {src}",
                    WarningCategory.CSS_PARSING,
                    {'rule_type': 'font-face', 'font_family': font_family, 'src': src, 'issue': 'invalid_src'}
                )
                return

            # Extract optional properties with defaults
            font_weight = self._normalize_font_weight(declarations.get('font-weight', 'normal'))
            font_style = declarations.get('font-style', 'normal')

            # Create FontFace and add to registry
            font_face = FontFace(
                family=font_family,
                src=font_src,
                weight=font_weight,
                style=font_style
            )

            self.font_registry.add_font_face(font_face)

        except Exception as e:
            self.warnings.warn(
                f"Failed to process @font-face rule: {e}",
                WarningCategory.CSS_PARSING,
                {'rule_type': 'font-face', 'error': str(e)}
            )

    def _parse_font_src(self, src: str) -> Optional[str]:
        """
        Parse CSS font src property and extract the font file path.

        Supports:
        - url("path/to/font.woff2")
        - url('path/to/font.ttf')
        - url(path/to/font.otf)
        - url('font.ttf') format('truetype')
        - url('font.woff2') format('woff2')
        - Multiple src values (returns the first valid one)

        Args:
            src: CSS src property value

        Returns:
            Font file path/URL or None if parsing fails
        """
        src = src.strip()

        # Handle multiple src values separated by comma
        src_values = [s.strip() for s in src.split(',')]

        for src_value in src_values:
            # Parse src value which may contain url() and format()
            font_url = self._extract_url_from_src(src_value)
            if font_url:
                return font_url

        return None

    def _extract_url_from_src(self, src_value: str) -> Optional[str]:
        """
        Extract URL from a single src value that may contain url() and format().

        Examples:
        - url("font.ttf") -> "font.ttf"
        - url('font.woff2') format('woff2') -> "font.woff2"
        - url(font.otf) format("opentype") -> "font.otf"
        """
        src_value = src_value.strip()

        # Find url() function
        url_start = src_value.find('url(')
        if url_start == -1:
            return None

        # Find the matching closing parenthesis for url()
        paren_count = 0
        url_end = -1

        for i in range(url_start + 4, len(src_value)):
            if src_value[i] == '(':
                paren_count += 1
            elif src_value[i] == ')':
                if paren_count == 0:
                    url_end = i
                    break
                paren_count -= 1

        if url_end == -1:
            return None

        # Extract content between url( and )
        url_content = src_value[url_start + 4:url_end].strip()

        # Remove quotes if present
        if (url_content.startswith('"') and url_content.endswith('"')) or \
           (url_content.startswith("'") and url_content.endswith("'")):
            url_content = url_content[1:-1]

        return url_content

    def _normalize_font_weight(self, weight: str) -> str:
        """
        Normalize CSS font-weight value to numeric string.

        Args:
            weight: CSS font-weight value (normal, bold, 100-900, etc.)

        Returns:
            Normalized weight as string (400, 700, etc.)
        """
        weight = weight.strip().lower()

        # Map named weights to numeric values
        weight_map = {
            'normal': '400',
            'bold': '700',
            'lighter': '300',  # Simplified
            'bolder': '700'    # Simplified
        }

        if weight in weight_map:
            return weight_map[weight]

        # Check if it's already numeric (100, 200, ..., 900)
        if weight.isdigit() and 100 <= int(weight) <= 900:
            return weight

        # Default to normal weight
        return '400'