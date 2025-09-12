"""
Core Html2Pic class and main API
"""

from typing import Dict, Any
import pictex
from .html_parser import HtmlParser
from .css_parser import CssParser
from .style_engine import StyleEngine
from .translator import PicTexTranslator
from .exceptions import ParseError, RenderError
from .warnings_system import get_warning_collector, reset_warnings

class Html2Pic:
    """
    Main class for converting HTML + CSS to images using PicTex.
    
    This class orchestrates the entire conversion process:
    1. Parse HTML into a DOM tree
    2. Parse CSS into style rules
    3. Apply styles to DOM nodes (cascading, specificity, inheritance)
    4. Translate styled DOM tree to PicTex builders
    5. Render using PicTex
    
    Example:
        ```python
        html = '<div class="card"><h1>Hello</h1><p>World</p></div>'
        css = '''
            .card { 
                display: flex; 
                flex-direction: column; 
                padding: 20px; 
                background: #f0f0f0; 
            }
            h1 { font-size: 24px; color: blue; }
            p { color: gray; }
        '''
        
        renderer = Html2Pic(html, css)
        image = renderer.render()
        image.save("output.png")
        ```
    """
    
    def __init__(self, html: str, css: str = "", base_font_size: int = 16):
        """
        Initialize the HTML to image converter.
        
        Args:
            html: HTML content as a string
            css: CSS content as a string  
            base_font_size: Base font size for relative units (default: 16px)
        """
        self.html = html
        self.css = css
        self.base_font_size = base_font_size
        
        # Initialize parsers and engines
        self.html_parser = HtmlParser()
        self.css_parser = CssParser()
        self.style_engine = StyleEngine(base_font_size=base_font_size)
        self.translator = PicTexTranslator()
        self.warnings = get_warning_collector()
        
        # Reset warnings for this new instance
        reset_warnings()
        
        # Parsed content (lazy loaded)
        self._dom_tree = None
        self._style_rules = None
        self._styled_tree = None
    
    @property
    def dom_tree(self):
        """Lazily parse and return the DOM tree"""
        if self._dom_tree is None:
            try:
                self._dom_tree = self.html_parser.parse(self.html)
            except Exception as e:
                raise ParseError(f"Failed to parse HTML: {e}") from e
        return self._dom_tree
    
    @property  
    def style_rules(self):
        """Lazily parse and return the CSS style rules"""
        if self._style_rules is None:
            try:
                self._style_rules = self.css_parser.parse(self.css)
            except Exception as e:
                raise ParseError(f"Failed to parse CSS: {e}") from e
        return self._style_rules
    
    @property
    def styled_tree(self):
        """Lazily compute and return the styled DOM tree"""
        if self._styled_tree is None:
            try:
                self._styled_tree = self.style_engine.apply_styles(
                    self.dom_tree, 
                    self.style_rules
                )
            except Exception as e:
                raise RenderError(f"Failed to apply styles: {e}") from e
        return self._styled_tree
    
    def render(self, crop_mode: pictex.CropMode = pictex.CropMode.SMART) -> pictex.BitmapImage:
        """
        Render the HTML + CSS to a bitmap image.
        
        Args:
            crop_mode: How to crop the final image (SMART, CONTENT_BOX, or NONE)
            
        Returns:
            A PicTex BitmapImage object
            
        Raises:
            Html2PicError: If any step in the conversion process fails
        """
        try:
            # Translate styled DOM tree to PicTex builders
            canvas, root_element = self.translator.translate(self.styled_tree)
            
            # Render using PicTex
            if root_element is None:
                # Empty document, just render the canvas
                return canvas.render("", crop_mode=crop_mode)
            else:
                return canvas.render(root_element, crop_mode=crop_mode)
                
        except Exception as e:
            raise RenderError(f"Failed to render image: {e}") from e
    
    def render_as_svg(self, embed_font: bool = True) -> pictex.VectorImage:
        """
        Render the HTML + CSS to an SVG vector image.
        
        Args:
            embed_font: Whether to embed fonts in the SVG (default: True)
            
        Returns:
            A PicTex VectorImage object
            
        Raises:
            Html2PicError: If any step in the conversion process fails
        """
        try:
            # Translate styled DOM tree to PicTex builders  
            canvas, root_element = self.translator.translate(self.styled_tree)
            
            # Render as SVG using PicTex
            if root_element is None:
                return canvas.render_as_svg("", embed_font=embed_font)
            else:
                return canvas.render_as_svg(root_element, embed_font=embed_font)
                
        except Exception as e:
            raise RenderError(f"Failed to render SVG: {e}") from e
    
    def debug_info(self) -> Dict[str, Any]:
        """
        Get debugging information about the conversion process.
        
        Returns:
            Dictionary containing DOM tree, style rules, styled tree, and warnings info
        """
        return {
            "dom_tree": self.dom_tree,
            "style_rules": self.style_rules, 
            "styled_tree": self.styled_tree,
            "base_font_size": self.base_font_size,
            "warnings": self.get_warnings(),
            "warnings_summary": self.get_warnings_summary()
        }
    
    def get_warnings(self) -> list:
        """Get all warnings from the conversion process"""
        return self.warnings.get_warnings()
    
    def get_warnings_summary(self) -> dict:
        """Get a summary of warnings from the conversion process"""
        return self.warnings.get_summary()
    
    def print_warnings(self):
        """Print a formatted summary of all warnings"""
        self.warnings.print_summary()