"""Element factory for creating PicTex builders."""
from typing import Optional

from pictex import Row, Column, Text, Image, Element

from ..dom import DOMNode
from ..styling import DEFAULT_STYLES
from ..warnings import get_warning_collector


class ElementFactory:
    """Factory for creating PicTex builders from DOM nodes."""
    
    def __init__(self, loader=None):
        self.warnings = get_warning_collector()
        self.loader = loader
    
    INLINE_TAGS = {'span', 'a', 'strong', 'em', 'b', 'i', 'u', 'code', 'small'}
    BLOCK_TAGS = {'div', 'section', 'article', 'main', 'header', 'footer', 'aside', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
    
    def create(self, node: DOMNode) -> Optional[Element]:
        """Create appropriate PicTex builder for a DOM node."""
        if node.tag == 'img':
            return self._create_image(node)
        
        if self._is_flex_container(node):
            return self._create_flex_container(node)
        
        if self._is_inline(node):
            return Row()

        return Column()
    
    
    def _create_image(self, node: DOMNode) -> Optional[Image]:
        src = node.attributes.get('src', '')
        if not src:
            self.warnings.warn_message("Image source is empty")
            return None
        if self.loader is not None:
            src = self.loader.localize(src, purpose='image')
            if src is None:
                return None
        return Image(src)
    
    def _create_flex_container(self, node: DOMNode) -> Element:
        direction = node.computed_styles.get('flex-direction', DEFAULT_STYLES['flex-direction'])
        if direction in ['column', 'column-reverse']:
            return Column()
        return Row()
    
    def _is_flex_container(self, node: DOMNode) -> bool:
        return node.computed_styles.get('display') == 'flex'
    
    def _is_inline(self, node: DOMNode) -> bool:
        return node.computed_styles.get('display', DEFAULT_STYLES['display']) == 'inline' 
    
    def create_text(self, content: str) -> Text:
        """Create a Text element."""
        return Text(content)

