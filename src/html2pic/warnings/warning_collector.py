"""Warning collection and management."""
import warnings
from typing import List, Dict, Any, Optional

from .warning_category import WarningCategory


class Html2PicWarning(UserWarning):
    pass


class UnsupportedFeatureWarning(Html2PicWarning):
    pass


class StyleApplicationWarning(Html2PicWarning):
    pass


class TranslationWarning(Html2PicWarning):
    pass


class ParsingWarning(Html2PicWarning):
    pass


class WarningCollector:
    """Collects and manages warnings during html2pic conversion."""
    
    def __init__(self):
        self.warnings: List[Dict[str, Any]] = []
        self._enabled = True
    
    def warn(
        self, 
        message: str, 
        category: WarningCategory, 
        details: Optional[Dict[str, Any]] = None,
        warning_class: type = Html2PicWarning
    ):
        if not self._enabled:
            return
        
        warning_info = {
            'message': message,
            'category': category.value,
            'details': details or {},
            'warning_class': warning_class.__name__
        }
        self.warnings.append(warning_info)
        warnings.warn(f"[{category.value.upper()}] {message}", warning_class, stacklevel=3)

    def warn_message(self, message: str):
        self.warn(
            message,
            WarningCategory.MESSAGE,
            {'message': message},
            Html2PicWarning
        )

    def warn_unexpected_error(self, message: str):
        self.warn(
            message,
            WarningCategory.UNEXPECTED_ERROR,
            {'message': message},
            Html2PicWarning
        )
    
    def warn_unsupported_html_tag(self, tag_name: str, context: str = ""):
        self.warn(
            f"HTML tag '<{tag_name}>' is not supported and was skipped",
            WarningCategory.HTML_PARSING,
            {'tag': tag_name, 'context': context},
            UnsupportedFeatureWarning
        )
    
    def warn_unsupported_css_property(self, property_name: str, value: str, selector: str = ""):
        self.warn(
            f"CSS property '{property_name}: {value}' is not supported",
            WarningCategory.CSS_PARSING,
            {'property': property_name, 'value': value, 'selector': selector},
            UnsupportedFeatureWarning
        )
    
    def warn_css_selector_ignored(self, selector: str, reason: str):
        self.warn(
            f"CSS selector '{selector}' was ignored: {reason}",
            WarningCategory.CSS_PARSING,
            {'selector': selector, 'reason': reason},
            ParsingWarning
        )
    
    def warn_style_not_applied(self, property_name: str, value: str, element_info: str, reason: str):
        self.warn(
            f"Style '{property_name}: {value}' could not be applied to {element_info}: {reason}",
            WarningCategory.STYLE_APPLICATION,
            {'property': property_name, 'value': value, 'element': element_info, 'reason': reason},
            StyleApplicationWarning
        )
    
    def warn_element_skipped(self, element_info: str, reason: str):
        self.warn(
            f"Element {element_info} was skipped: {reason}",
            WarningCategory.UNSUPPORTED_FEATURE,
            {'element': element_info, 'reason': reason},
            TranslationWarning
        )
    
    def warn_color_fallback(self, original_color: str, fallback_color: str, reason: str):
        self.warn(
            f"Color '{original_color}' fell back to '{fallback_color}': {reason}",
            WarningCategory.STYLE_APPLICATION,
            {'original': original_color, 'fallback': fallback_color, 'reason': reason},
            StyleApplicationWarning
        )
    
    def get_warnings(self, category: Optional[WarningCategory] = None) -> List[Dict[str, Any]]:
        if category is None:
            return self.warnings.copy()
        return [w for w in self.warnings if w['category'] == category.value]
    
    def get_summary(self) -> Dict[str, Any]:
        by_category = {}
        for warning in self.warnings:
            cat = warning['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(warning)
        
        return {
            'total_warnings': len(self.warnings),
            'by_category': {cat: len(warns) for cat, warns in by_category.items()},
            'categories': by_category
        }
    
    def print_summary(self):
        if not self.warnings:
            return
        
        summary = self.get_summary()
        print(f"\nCompleted with {summary['total_warnings']} warnings:")
        
        for category, count in summary['by_category'].items():
            print(f"  {category.replace('_', ' ').title()}: {count}")
        
        print("\nDetailed warnings:")
        for i, warning in enumerate(self.warnings, 1):
            print(f"  {i}. [{warning['category'].upper()}] {warning['message']}")
    
    def clear(self):
        self.warnings.clear()
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False


_global_collector = WarningCollector()


def get_warning_collector() -> WarningCollector:
    return _global_collector


def reset_warnings():
    _global_collector.clear()
