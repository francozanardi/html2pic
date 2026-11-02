"""CSS parser using tinycss2."""
from typing import Dict, Iterable, List, Optional, Set, Tuple

import tinycss2

from .css_rule import CSSRule
from .selector import Selector, UnsupportedSelectorError, specificity_to_int
from .shorthand_expander import ShorthandExpander
from ..fonts import FontFace, FontRegistry, FontSrcParser
from ..warnings import get_warning_collector
from ..exceptions import ParseError
from ..styling import DEFAULT_STYLES
from ..resources import ResourceLoader, Stylesheet


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
        'background', 'background-color', 'background-image', 'background-size', 'box-shadow', 'text-shadow',
        'color', 'font-family', 'font-size', 'font-weight', 'font-style',
        'text-align', 'line-height', 'text-decoration', 'text-wrap',
        'position', 'left', 'top', 'right', 'bottom',
        'transform'
    }
    
    MAX_IMPORT_DEPTH = 16
    APPLICABLE_MEDIA = {'', 'all', 'screen'}
    
    def __init__(self, loader: Optional[ResourceLoader] = None):
        self.warnings = get_warning_collector()
        self.font_registry = FontRegistry()
        self.shorthand_expander = ShorthandExpander()
        self.font_src_parser = FontSrcParser()
        self.loader = loader
    
    def parse(self, css_content: str, base_url: Optional[str] = None) -> Tuple[List[CSSRule], FontRegistry]:
        """Parse a single CSS string into rules and a font registry."""
        return self.parse_stylesheets([Stylesheet(css_content, base_url)])
    
    def parse_stylesheets(self, stylesheets: Iterable[Stylesheet]) -> Tuple[List[CSSRule], FontRegistry]:
        """Parse several stylesheets in cascade order (later sheets win ties)."""
        self.font_registry.clear()
        rules: List[CSSRule] = []
        for sheet in stylesheets:
            rules.extend(self._parse_sheet(sheet.css, sheet.base_url, visited=set(), depth=0))
        return rules, self.font_registry
    
    def parse_inline(self, style: str, base_url: Optional[str] = None) -> Dict[str, str]:
        """Parse the declarations of an HTML style="" attribute."""
        try:
            return self._extract_declarations(style, base_url)
        except Exception as e:
            self.warnings.warn_unexpected_error(f"Failed to parse style attribute '{style}': {e}")
            return {}
    
    def _parse_sheet(self, css_content: str, base_url: Optional[str], visited: Set[str], depth: int) -> List[CSSRule]:
        if not css_content.strip():
            return []
        try:
            stylesheet = tinycss2.parse_stylesheet(css_content, skip_comments=True, skip_whitespace=True)
            
            rules = []
            for rule in stylesheet:
                if rule.type == 'at-rule' and rule.lower_at_keyword == 'font-face':
                    self._process_font_face(rule, base_url)
                elif rule.type == 'at-rule' and rule.lower_at_keyword == 'import':
                    rules.extend(self._process_import(rule, base_url, visited, depth))
                elif rule.type == 'at-rule':
                    self.warnings.warn_css_selector_ignored(
                        f"@{rule.at_keyword}", "at-rule is not supported"
                    )
                elif rule.type == 'qualified-rule':
                    rules.extend(self._process_rule(rule, base_url))
            
            return rules
        except Exception as e:
            raise ParseError(f"Failed to parse CSS: {e}") from e
    
    def _process_import(self, rule, base_url: Optional[str], visited: Set[str], depth: int) -> List[CSSRule]:
        tokens = [t for t in rule.prelude if t.type not in ('whitespace', 'comment')]
        if not tokens:
            return []
        first = tokens[0]
        if first.type in ('url', 'string'):
            href = first.value
        elif first.type == 'function' and first.lower_name == 'url':
            href = next((a.value for a in first.arguments if a.type == 'string'), '')
        else:
            self.warnings.warn_unexpected_error(f"Invalid @import: {rule.serialize()}")
            return []
        
        media = ''.join(t.serialize() for t in tokens[1:]).strip().lower()
        if media not in self.APPLICABLE_MEDIA:
            self.warnings.warn_css_selector_ignored(f"@import {href} {media}", "media-conditional imports are not supported")
            return []
        if self.loader is None:
            self.warnings.warn_resource(f"Skipped @import '{href}': no resource loader configured")
            return []
        
        url = self.loader.resolve(href, base_url)
        if url in visited or depth >= self.MAX_IMPORT_DEPTH:
            self.warnings.warn_resource(f"Skipped @import '{url}': import cycle or nesting too deep")
            return []
        css = self.loader.fetch_text(url, purpose='@import')
        if css is None:
            return []
        return self._parse_sheet(css, url, visited | {url}, depth + 1)
    
    def _process_rule(self, rule, base_url: Optional[str] = None) -> List[CSSRule]:
        selectors = self._extract_selectors(rule.prelude)
        declarations = self._extract_declarations(rule.content, base_url)
        
        css_rules = []
        for selector in selectors:
            try:
                parsed = Selector.parse(selector)
            except UnsupportedSelectorError as e:
                self.warnings.warn_css_selector_ignored(selector, str(e))
                continue
            css_rules.append(CSSRule(
                selector=parsed.text,
                declarations=declarations,
                specificity=specificity_to_int(parsed.specificity)
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
    
    def _extract_declarations(self, content, base_url: Optional[str] = None) -> dict:
        declarations = {}
        declaration_list = tinycss2.parse_declaration_list(content, skip_comments=True, skip_whitespace=True)
        
        for item in declaration_list:
            if item.type != 'declaration':
                continue
            
            prop_name = item.lower_name
            prop_value = self._serialize_value(item.value, base_url)
            
            self._check_property(prop_name, prop_value)
            
            if prop_name == 'padding':
                declarations.update(self.shorthand_expander.expand_padding(prop_value))
            elif prop_name == 'margin':
                declarations.update(self.shorthand_expander.expand_margin(prop_value))
            elif prop_name == 'border':
                declarations.update(self.shorthand_expander.expand_border(prop_value))
            elif prop_name == 'background':
                declarations.update(self.shorthand_expander.expand_background(prop_value))
            else:
                declarations[prop_name] = prop_value
        
        return declarations
    
    def _serialize_value(self, tokens, base_url: Optional[str]) -> str:
        """Serialize a declaration value, resolving url()s to absolute URLs."""
        parts = []
        for token in tokens:
            if token.type == 'url':
                parts.append(self._absolute_url(token.value, base_url))
            elif token.type == 'function' and token.lower_name == 'url':
                arg = next((a for a in token.arguments if a.type == 'string'), None)
                parts.append(self._absolute_url(arg.value, base_url) if arg else token.serialize())
            else:
                parts.append(token.serialize())
        return ''.join(parts).strip()
    
    def _absolute_url(self, url: str, base_url: Optional[str]) -> str:
        if self.loader is not None:
            url = self.loader.resolve(url, base_url)
        return 'url("' + url.replace('\\', '\\\\').replace('"', '\\"') + '")'
    
    def _check_property(self, name: str, value: str):
        if name not in self.SUPPORTED_PROPERTIES:
            self.warnings.warn_unsupported_css_property(name, value)
    
    def _process_font_face(self, rule, base_url: Optional[str] = None):
        try:
            declarations = {}
            declaration_list = tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True)
            
            for item in declaration_list:
                if item.type == 'declaration':
                    declarations[item.lower_name] = self._serialize_value(item.value, base_url)
            
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
