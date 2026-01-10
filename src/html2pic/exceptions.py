"""Custom exceptions for html2pic."""


class Html2PicError(Exception):
    """Base exception for html2pic errors."""
    pass


class ParseError(Html2PicError):
    """Error during HTML or CSS parsing."""
    pass


class RenderError(Html2PicError):
    """Error during rendering."""
    pass