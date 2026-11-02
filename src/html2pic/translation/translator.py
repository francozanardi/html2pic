"""DOM to PicTex translator."""
from typing import Tuple, Optional, List, Dict, Any, Union

from pictex import Canvas, Row, Column, Text, Element

from ..dom import DOMNode
from ..fonts import FontRegistry
from ..warnings import get_warning_collector
from ..exceptions import RenderError
from ..resources import ResourceLoader
from .element_factory import ElementFactory
from .inline_formatting import InlineFormatter, is_inline_level
from .style_applicators import (
    StyleApplicator,
    SizeApplicator,
    SpacingApplicator,
    BackgroundApplicator,
    BorderApplicator,
    ShadowApplicator,
    LayoutApplicator,
    TypographyApplicator,
    PositioningApplicator,
    TransformApplicator,
    OverflowApplicator,
)


class PicTexTranslator:
    """Translates a styled DOM tree into PicTex builders."""
    
    def __init__(self):
        self.warnings = get_warning_collector()
        self.element_factory = ElementFactory()
        self.font_registry: FontRegistry = None
        self.loader: Optional[ResourceLoader] = None
        self._applicators: List[StyleApplicator] = []
        self._layout_applicator: LayoutApplicator = None
    
    def translate(
        self, 
        styled_dom: DOMNode, 
        font_registry: FontRegistry = None,
        loader: Optional[ResourceLoader] = None,
    ) -> Tuple[Canvas, Optional[Element]]:
        """Translate a styled DOM tree to PicTex builders.
        
        ``loader`` turns image/font URLs into local files PicTex can read; without it URLs
        are passed to PicTex unchanged.
        """
        self.font_registry = font_registry
        self.loader = loader
        self.element_factory.loader = loader
        self._applicators = self._create_applicators()
        self._layout_applicator = LayoutApplicator()
        typography = TypographyApplicator(self.font_registry, self.loader)
        self._inline_formatter = InlineFormatter(
            style_text=typography.apply,
            style_span=typography.apply_inline,
            translate_atomic=self._translate_node,
        )
        
        try:
            canvas = Canvas()
            root_element = self._translate_node(styled_dom)
            return canvas, root_element
        except Exception as e:
            raise RenderError(f"Translation failed: {e}") from e
    
    def _create_applicators(self) -> List[StyleApplicator]:
        return [
            SizeApplicator(),
            SpacingApplicator(),
            BackgroundApplicator(self.loader),
            BorderApplicator(),
            ShadowApplicator(),
            TypographyApplicator(self.font_registry, self.loader),
            PositioningApplicator(),
            TransformApplicator(),
            OverflowApplicator(),
        ]
    
    def _translate_node(self, node: DOMNode) -> Optional[Element]:
        if node.is_text():
            return self._create_text(node)
        return self._create_element(node)
    
    def _create_text(self, node: DOMNode) -> Optional[Text]:
        # Text normally goes through InlineFormatter (see _add_children); this only handles
        # a text node translated on its own.
        content = node.text_content.strip()
        if not content:
            return None
        return self.element_factory.create_text(content)
    
    def _create_element(self, node: DOMNode) -> Optional[Element]:
        styles = node.computed_styles
        
        if styles.get('display') == 'none':
            return None
        
        builder = self.element_factory.create(node)
        if builder is None:
            return None
            
        if isinstance(builder, (Row, Column)):
            builder = self._add_children(builder, node)
        
        builder = self._apply_styles(builder, styles)
        
        if isinstance(builder, (Row, Column)):
            builder = self._layout_applicator.apply(builder, styles)
        
        return builder
    
    def _apply_styles(self, builder: Element, styles: Dict[str, Any]) -> Element:
        for applicator in self._applicators:
            builder = applicator.apply(builder, styles)
        return builder
    
    def _add_children(
        self, 
        container: Union[Row, Column], 
        node: DOMNode
    ) -> Union[Row, Column]:
        children: List[Element] = []
        run: List[DOMNode] = []
        # In a flex container every child element is a flex item ("blockified"); only
        # contiguous text becomes an anonymous item. Elsewhere, consecutive inline-level
        # content (text, inline elements, <br>) flows together as rich text.
        is_flex = node.computed_styles.get('display') == 'flex'
        
        def flush():
            if run:
                element = self._inline_formatter.build(list(run), node)
                if element is not None:
                    children.append(element)
                run.clear()
        
        for child in node.children:
            if child.is_element() and child.computed_styles.get('display') == 'none':
                continue  # generates nothing, and must not split the surrounding text
            if child.is_text() or (not is_flex and is_inline_level(child)):
                run.append(child)
                continue
            flush()
            child_element = self._translate_node(child)
            if child_element is not None:
                children.append(child_element)
        flush()
        
        if not children:
            return container
        
        if self._is_reversed_flex(node):
            # PicTex has no *-reverse directions: lay the items out in reverse order instead
            # (LayoutApplicator mirrors flex-start/flex-end accordingly).
            children.reverse()
        
        if isinstance(container, Row):
            return Row(*children)
        return Column(*children)
    
    @staticmethod
    def _is_reversed_flex(node: DOMNode) -> bool:
        styles = node.computed_styles
        return styles.get('display') == 'flex' and styles.get('flex-direction', '').endswith('-reverse')
