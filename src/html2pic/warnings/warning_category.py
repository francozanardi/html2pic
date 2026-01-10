"""Warning categories for html2pic."""
from enum import Enum


class WarningCategory(Enum):
    HTML_PARSING = "html_parsing"
    CSS_PARSING = "css_parsing"
    STYLE_APPLICATION = "style_application"
    RENDERING = "rendering"
    FONT = "font"
    UNSUPPORTED_FEATURE = "unsupported_feature"
    UNEXPECTED_ERROR = "unexpected_error"
    MESSAGE = "message"
