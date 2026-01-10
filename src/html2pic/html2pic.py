"""Main Html2Pic class for converting HTML + CSS to images."""
from typing import Dict, Any

import pictex

from .parsing import HtmlParser, CssParser
from .styling import StyleEngine
from .translation import PicTexTranslator
from .warnings import get_warning_collector, reset_warnings
from .exceptions import RenderError
from .dom import DOMNode
from .parsing import CSSRule
from .fonts import FontRegistry
from typing import Optional, List

class Html2Pic:
    """Convert HTML + CSS to images using PicTex.
    
    Example:
        ```python
        html = '<div class="card"><h1>Hello</h1></div>'
        css = '.card { padding: 20px; background: #f0f0f0; }'
        
        renderer = Html2Pic(html, css)
        image = renderer.render()
        image.save("output.png")
        ```
    """
    
    def __init__(self, html: str, css: str = ""):
        self.html = html
        self.css = css
        
        self._html_parser: HtmlParser = HtmlParser()
        self._css_parser: CssParser = CssParser()
        self._style_engine: StyleEngine = StyleEngine()
        self._translator: PicTexTranslator = PicTexTranslator()
        self._warnings = get_warning_collector()
        
        reset_warnings()
        
        self._dom_tree: Optional[DOMNode] = None
        self._style_rules: Optional[List[CSSRule]] = None
        self._font_registry: Optional[FontRegistry] = None
        self._styled_tree: Optional[DOMNode] = None
    
    @property
    def dom_tree(self) -> DOMNode:
        if self._dom_tree is None:
            self._dom_tree = self._html_parser.parse(self.html)
        return self._dom_tree
    
    @property
    def style_rules(self) -> List[CSSRule]:
        if self._style_rules is None:
            self._style_rules, self._font_registry = self._css_parser.parse(self.css)
        return self._style_rules

    @property
    def font_registry(self) -> FontRegistry:
        if self._font_registry is None:
            _ = self.style_rules
        return self._font_registry
    
    @property
    def styled_tree(self) -> DOMNode:
        if self._styled_tree is None:
            self._styled_tree = self._style_engine.apply_styles(
                self.dom_tree,
                self.style_rules,
                self.font_registry
            )
        return self._styled_tree
    
    def render(self, crop_mode: pictex.CropMode = pictex.CropMode.CONTENT_BOX) -> pictex.BitmapImage:
        """Render to a bitmap image."""
        try:
            canvas, root = self._translator.translate(self.styled_tree, self.font_registry)
            if root is None:
                result = canvas.render("", crop_mode=crop_mode)
                self._print_warnings()
                return result
            else:
                result = canvas.render(root, crop_mode=crop_mode)
                self._print_warnings()
                return result
        except Exception as e:
            self._print_warnings()
            raise RenderError(f"Failed to render: {e}") from e
    
    def render_as_svg(self, embed_font: bool = True) -> pictex.VectorImage:
        """Render to an SVG vector image."""
        try:
            canvas, root = self._translator.translate(self.styled_tree, self.font_registry)
            if root is None:
                result = canvas.render_as_svg("", embed_font=embed_font)
                self._print_warnings()
                return result
            else:
                result = canvas.render_as_svg(root, embed_font=embed_font)
                self._print_warnings()
                return result
        except Exception as e:
            self._print_warnings()
            raise RenderError(f"Failed to render SVG: {e}") from e
    
    def debug_info(self) -> Dict[str, Any]:
        return {
            "dom_tree": self.dom_tree,
            "style_rules": self.style_rules,
            "font_registry": self.font_registry,
            "styled_tree": self.styled_tree,
            "warnings": self.get_warnings(),
        }
    
    def get_warnings(self) -> list:
        return self._warnings.get_warnings()
    
    def get_warnings_summary(self) -> dict:
        return self._warnings.get_summary()
    
    def _print_warnings(self):
        self._warnings.print_summary()
