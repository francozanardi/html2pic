"""
html2pic: Convert HTML + CSS to images using PicTex

A Python library that translates a subset of HTML and CSS to beautiful images
without requiring a browser engine. Built on top of PicTex for high-quality
rendering with flexbox-like layout support.

Example:
    ```python
    from html2pic import Html2Pic

    html = '<div class="card"><h1>Hello World</h1></div>'
    css = '.card { padding: 20px; background: blue; color: white; }'
    
    renderer = Html2Pic(html, css)
    image = renderer.render()
    image.save("output.png")
    ```
"""

from .core import Html2Pic
from .exceptions import Html2PicError, ParseError, RenderError
from .warnings_system import (
    get_warning_collector, reset_warnings, WarningCategory,
    Html2PicWarning, UnsupportedFeatureWarning, StyleApplicationWarning,
    TranslationWarning, ParsingWarning
)

__version__ = "0.1.3"
__all__ = [
    "Html2Pic", "Html2PicError", "ParseError", "RenderError",
    "get_warning_collector", "reset_warnings", "WarningCategory",
    "Html2PicWarning", "UnsupportedFeatureWarning", "StyleApplicationWarning", 
    "TranslationWarning", "ParsingWarning"
]