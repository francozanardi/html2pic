"""
html2pic - Convert HTML + CSS to images using PicTex

A pure Python library for rendering HTML and CSS to images without requiring
a browser or headless rendering engine.
"""

from .html2pic import Html2Pic
from .exceptions import ParseError, RenderError, Html2PicError

__all__ = [
    "Html2Pic",
    "ParseError",
    "RenderError", 
    "Html2PicError",
]

__version__ = "0.2.2"