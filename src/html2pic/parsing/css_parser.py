"""CSS parser using tinycss2."""
from typing import List, Tuple

import tinycss2

from .css_rule import CSSRule
from .selector import ParsedSelector, SelectorType
from .shorthand_expander import ShorthandExpander
from ..fonts import FontFace, FontRegistry, FontSrcParser
from ..warnings import get_warning_collector
from ..exceptions import ParseError
from ..styiling import DEFAULT_STYLES


class CssParser:
    """Parses CSS content into structured rules."""
    
    SUPPORTED_PROPERTIES = {
        'display', 'flex-direction', 'justify-content', 'align-items', 'gap',
        'flex-grow', 'flex-shrink', 'align-self', 'flex-wrap',
        'width', 'height', 'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
        'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
        'border', 'border-width', 'border-style', 'border-color', 'border-radius',
        'border-top-left-radius', 'border-top-right-radius', 'border-bottom-left-radius', 'border-bottom-right-radius',
        'min-width', 'max-width', 'min-height', 'max-height', 'aspect-ratio',
        'background-color', 'background-image', 'background-size', 'box-shadow', 'text-shadow',
        'color', 'font-family', 'font-size', 'font-weight', 'font-style',
        'text-align', 'line-height', 'text-decoration', 'text-wrap',
        'position', 'left', 'top', 'right', 'bottom',
        'transform'
    }
    
    def __init__(self):
        self.warnings = get_warning_collector()
        self.font_registry = FontRegistry()
        self.shorthand_expander = ShorthandExpander()
        self.font_src_parser = FontSrcParser()
    
    def parse(self, css_content: str) -> Tuple[List[CSSRule], FontRegistry]:
        """Parse CSS string into rules and font registry."""
        if not css_content.strip():
            return [], self.font_registry
        
        try:
            self.font_registry.clear()
            stylesheet = tinycss2.parse_stylesheet(css_content)
            
            rules = []
            for rule in stylesheet:
                if hasattr(rule, 'at_keyword') and rule.at_keyword == 'font-face':
                    self._process_font_face(rule)
                elif hasattr(rule, 'prelude') and hasattr(rule, 'content'):
                    rules.extend(self._process_rule(rule))
            
            return rules, self.font_registry
        except Exception as e:
            raise ParseError(f"Failed to parse CSS: {e}") from e
    
    def _process_rule(self, rule) -> List[CSSRule]:
        selectors = self._extract_selectors(rule.prelude)
        declarations = self._extract_declarations(rule.content)
        
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
        selectors = []
        current = []
        
        for token in prelude:
            if token.type == 'literal' and token.value == ',':
                if current:
                    selector_str = ''.join(t.serialize() for t in current).strip()
                    if selector_str:
                        selectors.append(selector_str)
                    current = []
            else:
                current.append(token)
        
        if current:
            selector_str = ''.join(t.serialize() for t in current).strip()
            if selector_str:
                selectors.append(selector_str)
        
        return selectors or ['*']
    
    def _extract_declarations(self, content) -> dict:
        declarations = {}
        declaration_list = tinycss2.parse_declaration_list(content)
        
        for item in declaration_list:
            if not hasattr(item, 'name'):
                continue
            
            prop_name = item.name.lower()
            prop_value = ''.join(token.serialize() for token in item.value).strip()
            
            self._check_property(prop_name, prop_value)
            
            if prop_name == 'padding':
                declarations.update(self.shorthand_expander.expand_padding(prop_value))
            elif prop_name == 'margin':
                declarations.update(self.shorthand_expander.expand_margin(prop_value))
            elif prop_name == 'border':
                declarations.update(self.shorthand_expander.expand_border(prop_value))
            else:
                declarations[prop_name] = prop_value
        
        return declarations
    
    def _calculate_specificity(self, selector: str) -> int:
        try:
            parsed = ParsedSelector.parse(selector)
            if parsed.selector_type == SelectorType.ID:
                return 100
            elif parsed.selector_type == SelectorType.CLASS:
                return 10
            elif parsed.selector_type == SelectorType.TAG:
                return 1
            return 0
        except Exception as e:
            self.warnings.warn_unexpected_error(f"Failed to calculate specificity for selector '{selector}': {e}")
            return 1
    
    def _check_property(self, name: str, value: str):
        if name not in self.SUPPORTED_PROPERTIES:
            self.warnings.warn_unsupported_css_property(name, value)
    
    def _process_font_face(self, rule):
        try:
            declarations = {}
            declaration_list = tinycss2.parse_declaration_list(rule.content)
            
            for item in declaration_list:
                if hasattr(item, 'name'):
                    prop_name = item.name.lower()
                    prop_value = ''.join(token.serialize() for token in item.value).strip()
                    declarations[prop_name] = prop_value
            
            family = declarations.get('font-family', '').strip('"\'')
            src = declarations.get('src', '')
            
            if not family or not src:
                return
            
            font_src = self.font_src_parser.parse(src)
            if not font_src:
                return
            
            weight = self._normalize_weight(declarations.get('font-weight', DEFAULT_STYLES['font-weight']))
            style = declarations.get('font-style', DEFAULT_STYLES['font-style'])
            
            self.font_registry.add_font_face(FontFace(
                family=family,
                src=font_src,
                weight=weight,
                style=style
            ))
        except Exception as e:
            self.warnings.warn_unexpected_error(f"Failed to process font face: {e}")
    
    def _normalize_weight(self, weight: str) -> str:
        weight = weight.strip().lower()
        weight_map = {'normal': '400', 'bold': '700', 'lighter': '300', 'bolder': '700'}
        if weight in weight_map:
            return weight_map[weight]
        if weight.isdigit() and 100 <= int(weight) <= 900:
            return weight
        return '400'
