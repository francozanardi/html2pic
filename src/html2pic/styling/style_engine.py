"""Style computation engine."""
from typing import Any, Callable, Dict, List, Optional

import tinycss2

from ..dom import DOMNode, NodeType
from ..parsing import CSSRule
from ..fonts import FontRegistry
from ..warnings import get_warning_collector
from .default_styles import DEFAULT_STYLES, INLINE_ELEMENTS
from .unit_converter import UnitConverter
from .color_normalizer import ColorNormalizer
from .cascade_resolver import CascadeResolver
from .margin_collapse import collapse_margins


class StyleEngine:
    """Computes final styles for DOM nodes by applying CSS rules."""
    
    INHERITED_PROPERTIES = {
        'color', 'font-family', 'font-size', 'font-weight', 'font-style',
        'line-height', 'text-align', 'text-decoration', 'text-wrap'
    }
    
    def __init__(self, base_font_size: int = 16):
        self.base_font_size = base_font_size
        self.warnings = get_warning_collector()
        self.font_registry: FontRegistry = None
        self.unit_converter = UnitConverter(base_font_size)
        self.color_normalizer = ColorNormalizer()
        self.cascade_resolver = CascadeResolver()
        self.inline_style_parser: Optional[Callable[[str], Dict[str, str]]] = None
    
    def apply_styles(
        self, 
        dom_tree: DOMNode, 
        css_rules: List[CSSRule], 
        font_registry: FontRegistry = None,
        inline_style_parser: Optional[Callable[[str], Dict[str, str]]] = None,
    ) -> DOMNode:
        """Apply CSS rules to a DOM tree, computing final styles for each node.
        
        ``inline_style_parser`` turns a ``style=""`` attribute into declarations; those are
        applied after every matching rule, like in browsers. Without it the attribute is ignored.
        """
        self.font_registry = font_registry
        self.inline_style_parser = inline_style_parser
        # The top node is the synthetic wrapper created by the HTML parser, not part of
        # the user's document, so CSS rules (e.g. `div { padding: 10px }`) must not match it.
        self._apply_recursive(dom_tree, css_rules, {}, match_rules=False)
        collapse_margins(dom_tree)
        return dom_tree
    
    def _apply_recursive(
        self, 
        node: DOMNode, 
        css_rules: List[CSSRule], 
        parent_styles: Dict[str, Any],
        match_rules: bool = True,
    ):
        computed = DEFAULT_STYLES.copy()
        if node.is_element() and node.tag in INLINE_ELEMENTS:
            computed['display'] = 'inline'
        
        for prop in self.INHERITED_PROPERTIES:
            if prop in parent_styles:
                computed[prop] = parent_styles[prop]
        
        if match_rules:
            matching_rules = self.cascade_resolver.find_matching_rules(node, css_rules)
            matching_rules.sort(key=lambda r: r.specificity)
            
            for rule in matching_rules:
                for prop, value in rule.declarations.items():
                    computed[prop] = value
            
            inline = node.attributes.get('style') if node.is_element() else None
            if inline and self.inline_style_parser is not None:
                computed.update(self.inline_style_parser(inline))
        
        computed = self._normalize(computed, parent_styles)
        node.computed_styles = computed
        
        if match_rules and node.is_element():
            self._attach_pseudo_elements(node, css_rules, computed)
        
        for child in node.children:
            if child.pseudo_element is None:
                self._apply_recursive(child, css_rules, computed)
    
    def _attach_pseudo_elements(self, node: DOMNode, css_rules: List[CSSRule], node_styles: Dict[str, Any]):
        """Generate ::before / ::after children for ``node`` from the matching rules."""
        node.children = [child for child in node.children if child.pseudo_element is None]
        
        for pseudo in ('before', 'after'):
            rules = self.cascade_resolver.find_matching_rules(node, css_rules, pseudo)
            if not rules:
                continue
            rules.sort(key=lambda r: r.specificity)
            
            styles = DEFAULT_STYLES.copy()
            styles['display'] = 'inline'  # pseudo-elements are inline by default
            for prop in self.INHERITED_PROPERTIES:
                styles[prop] = node_styles[prop]
            for rule in rules:
                styles.update(rule.declarations)
            
            content = self._resolve_content(styles.get('content', 'normal'), node)
            if content is None:
                continue  # 'content: none/normal' generates no box
            
            styles = self._normalize(styles, node_styles)
            if styles['display'] == 'none':
                continue
            
            pseudo_node = DOMNode(
                node_type=NodeType.ELEMENT,
                tag=f'::{pseudo}',
                parent=node,
                computed_styles=styles,
                pseudo_element=pseudo,
            )
            if content:
                text = DOMNode(node_type=NodeType.TEXT, text_content=content, parent=pseudo_node)
                self._apply_recursive(text, [], styles)
                pseudo_node.children.append(text)
            
            if pseudo == 'before':
                node.children.insert(0, pseudo_node)
            else:
                node.children.append(pseudo_node)
    
    QUOTES = {'open-quote': '\u201c', 'close-quote': '\u201d', 'no-open-quote': '', 'no-close-quote': ''}
    
    def _resolve_content(self, value: str, node: DOMNode) -> Optional[str]:
        """Evaluate a ``content`` value. Returns None when no box should be generated."""
        tokens = [
            t for t in tinycss2.parse_component_value_list(value or '')
            if t.type not in ('whitespace', 'comment')
        ]
        if not tokens or (len(tokens) == 1 and tokens[0].type == 'ident' and tokens[0].lower_value in ('none', 'normal')):
            return None
        
        parts = []
        for token in tokens:
            if token.type == 'string':
                parts.append(token.value)
            elif token.type == 'function' and token.lower_name == 'attr':
                names = [a.value for a in token.arguments if a.type == 'ident']
                parts.append(str(node.attributes.get(names[0], '')) if names else '')
            elif token.type == 'ident' and token.lower_value in self.QUOTES:
                parts.append(self.QUOTES[token.lower_value])
            else:
                self.warnings.warn_style_not_applied(
                    'content', token.serialize(), f'<{node.tag}>',
                    "only strings, attr() and quotes are supported"
                )
        return ''.join(parts)
    
    LENGTH_PROPERTIES = (
        'width', 'height', 'min-width', 'max-width', 'min-height', 'max-height',
        'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
        'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
        'border-width', 'border-radius', 'border-top-left-radius', 'border-top-right-radius',
        'border-bottom-left-radius', 'border-bottom-right-radius', 'gap',
        'top', 'right', 'bottom', 'left',
    )

    def _normalize(self, styles: Dict[str, Any], parent_styles: Dict[str, Any]) -> Dict[str, Any]:
        normalized = styles.copy()
        
        # font-size: em and % are relative to the parent's font size.
        parent_font_size = parent_styles.get('font-size', f'{self.base_font_size}px')
        normalized['font-size'] = self.unit_converter.to_pixels(
            normalized['font-size'],
            parent_value=parent_font_size,
            font_size=parent_font_size,
        )
        
        # Other lengths: em is relative to the element's own font size. Percentages are
        # left untouched; they are resolved by the layout engine (or reported as unsupported
        # by the applicator) because their reference box is only known at layout time.
        for prop in self.LENGTH_PROPERTIES:
            if prop in normalized:
                normalized[prop] = self.unit_converter.to_pixels(
                    normalized[prop],
                    font_size=normalized['font-size'],
                )
        
        normalized['display'] = self._normalize_display(normalized.get('display', 'block'))
        
        for color_prop in ['color', 'background-color', 'border-color']:
            if color_prop in normalized:
                normalized[color_prop] = self.color_normalizer.normalize(normalized[color_prop])
        
        return normalized
    
    def _normalize_display(self, display_value: str) -> str:
        display_value = display_value.strip().lower()
        
        if display_value == 'none':
            return 'none'
        elif display_value == 'flex':
            return 'flex'
        elif display_value in ['block', 'div']:
            return 'block'
        elif display_value in ['inline', 'inline-block', 'span']:
            return 'inline'

        self.warnings.warn_message(f"Unsupported display value: {display_value}")
        return 'block'
