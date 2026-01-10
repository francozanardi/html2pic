"""DOM to PicTex translator."""
from typing import Tuple, Optional, List, Dict, Any, Union

from pictex import Canvas, Row, Column, Text, Element

from ..dom import DOMNode
from ..fonts import FontRegistry
from ..warnings import get_warning_collector
from ..exceptions import RenderError
from .element_factory import ElementFactory
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
)


class PicTexTranslator:
    """Translates a styled DOM tree into PicTex builders."""
    
    def __init__(self):
        self.warnings = get_warning_collector()
        self.element_factory = ElementFactory()
        self.font_registry: FontRegistry = None
        self._applicators: List[StyleApplicator] = []
        self._layout_applicator: LayoutApplicator = None
    
    def translate(
        self, 
        styled_dom: DOMNode, 
        font_registry: FontRegistry = None
    ) -> Tuple[Canvas, Optional[Element]]:
        """Translate a styled DOM tree to PicTex builders."""
        self.font_registry = font_registry
        self._applicators = self._create_applicators()
        self._layout_applicator = LayoutApplicator()
        
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
            BackgroundApplicator(),
            BorderApplicator(),
            ShadowApplicator(),
            TypographyApplicator(self.font_registry),
            PositioningApplicator(),
            TransformApplicator(),
        ]
    
    def _translate_node(self, node: DOMNode) -> Optional[Element]:
        if node.is_text():
            return self._create_text(node)
        return self._create_element(node)
    
    def _create_text(self, node: DOMNode) -> Optional[Text]:
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
        children = []
        
        for child in node.children:
            child_element = self._translate_node(child)
            if child_element is not None:
                if isinstance(child_element, Text):
                    child_element = self._style_text(child_element, child)
                children.append(child_element)
        
        if not children:
            return container
        
        if isinstance(container, Row):
            return Row(*children)
        return Column(*children)
    
    def _style_text(self, text: Text, node: DOMNode) -> Text:
        parent = node.parent
        if parent and parent.computed_styles:
            applicator = TypographyApplicator(self.font_registry)
            text = applicator.apply(text, parent.computed_styles)
        return text
