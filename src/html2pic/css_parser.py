"""
CSS parser using tinycss2 to extract style rules
"""

from typing import List, Dict
import tinycss2
from .models import CSSRule, ParsedSelector, SelectorType
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
    
    def parse(self, css_content: str) -> List[CSSRule]:
        """
        Parse CSS string into a list of CSS rules.
        
        Args:
            css_content: CSS content as string
            
        Returns:
            List of CSSRule objects
            
        Raises:
            ParseError: If CSS parsing fails
        """
        if not css_content.strip():
            return []
            
        try:
            # Parse CSS with tinycss2
            stylesheet = tinycss2.parse_stylesheet(css_content)
            
            rules = []
            for rule in stylesheet:
                if hasattr(rule, 'prelude') and hasattr(rule, 'content'):
                    # This is a qualified rule (selector + declarations)
                    css_rules = self._process_rule(rule)
                    rules.extend(css_rules)
            
            return rules
            
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
    
    def _extract_declarations(self, content) -> Dict[str, str]:
        """
        Extract property: value declarations from rule content.
        
        Args:
            content: tinycss2 rule content tokens
            
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
                
                # Check for unsupported properties
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
        """Parse border shorthand like '1px solid black'."""
        parts = value.split()
        declarations = {}
        
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
            # Assume it's a color
            else:
                declarations['border-color'] = part
        
        return declarations
    
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
            'border-radius': 'Percentage values supported, individual corners not yet',
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