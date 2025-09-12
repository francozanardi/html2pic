"""
Exception classes for html2pic
"""

class Html2PicError(Exception):
    """Base exception for all html2pic errors"""
    pass

class ParseError(Html2PicError):
    """Raised when HTML or CSS parsing fails"""
    pass

class RenderError(Html2PicError):
    """Raised when rendering to PicTex fails"""
    pass

class UnsupportedFeatureError(Html2PicError):
    """Raised when an unsupported HTML/CSS feature is encountered"""
    pass