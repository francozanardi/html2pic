"""
Warning system for html2pic - provides detailed debugging information
"""

import warnings
from typing import List, Dict, Any, Optional
from enum import Enum

class WarningCategory(Enum):
    """Categories of warnings for better organization"""
    HTML_PARSING = "html_parsing"
    CSS_PARSING = "css_parsing" 
    STYLE_APPLICATION = "style_application"
    TRANSLATION = "translation"
    RENDERING = "rendering"
    UNSUPPORTED_FEATURE = "unsupported_feature"

class Html2PicWarning(UserWarning):
    """Base warning class for html2pic"""
    pass

class UnsupportedFeatureWarning(Html2PicWarning):
    """Warning for unsupported HTML/CSS features"""
    pass

class StyleApplicationWarning(Html2PicWarning):
    """Warning for style application issues"""
    pass

class TranslationWarning(Html2PicWarning):
    """Warning for DOM to PicTex translation issues"""
    pass

class ParsingWarning(Html2PicWarning):
    """Warning for HTML/CSS parsing issues"""
    pass

class WarningCollector:
    """
    Collects and manages warnings during the html2pic conversion process.
    
    This provides a centralized way to track all issues that occur during
    HTML/CSS parsing, style application, and rendering.
    """
    
    def __init__(self):
        self.warnings: List[Dict[str, Any]] = []
        self._enabled = True
    
    def warn(self, message: str, category: WarningCategory, details: Optional[Dict[str, Any]] = None, 
             warning_class: type = Html2PicWarning):
        """
        Add a warning with detailed context information.
        
        Args:
            message: Human-readable warning message
            category: Category of the warning
            details: Additional context (element info, CSS rule, etc.)
            warning_class: Specific warning class to use
        """
        if not self._enabled:
            return
        
        warning_info = {
            'message': message,
            'category': category.value,
            'details': details or {},
            'warning_class': warning_class.__name__
        }
        
        self.warnings.append(warning_info)
        
        # Also emit a standard Python warning
        warnings.warn(f"[{category.value.upper()}] {message}", warning_class, stacklevel=3)
    
    def warn_unsupported_html_tag(self, tag_name: str, context: str = ""):
        """Warn about unsupported HTML tags"""
        self.warn(
            f"HTML tag '<{tag_name}>' is not supported and was skipped",
            WarningCategory.HTML_PARSING,
            {'tag': tag_name, 'context': context},
            UnsupportedFeatureWarning
        )
    
    def warn_unsupported_css_property(self, property_name: str, value: str, selector: str = ""):
        """Warn about unsupported CSS properties"""
        self.warn(
            f"CSS property '{property_name}: {value}' is not supported",
            WarningCategory.CSS_PARSING,
            {'property': property_name, 'value': value, 'selector': selector},
            UnsupportedFeatureWarning
        )
    
    def warn_css_selector_ignored(self, selector: str, reason: str):
        """Warn about CSS selectors that were ignored"""
        self.warn(
            f"CSS selector '{selector}' was ignored: {reason}",
            WarningCategory.CSS_PARSING,
            {'selector': selector, 'reason': reason},
            ParsingWarning
        )
    
    def warn_style_not_applied(self, property_name: str, value: str, element_info: str, reason: str):
        """Warn about styles that couldn't be applied"""
        self.warn(
            f"Style '{property_name}: {value}' could not be applied to {element_info}: {reason}",
            WarningCategory.STYLE_APPLICATION,
            {'property': property_name, 'value': value, 'element': element_info, 'reason': reason},
            StyleApplicationWarning
        )
    
    def warn_element_skipped(self, element_info: str, reason: str):
        """Warn about elements that were skipped during translation"""
        self.warn(
            f"Element {element_info} was skipped: {reason}",
            WarningCategory.TRANSLATION,
            {'element': element_info, 'reason': reason},
            TranslationWarning
        )
    
    def warn_color_fallback(self, original_color: str, fallback_color: str, reason: str):
        """Warn about color values that fell back to defaults"""
        self.warn(
            f"Color '{original_color}' fell back to '{fallback_color}': {reason}",
            WarningCategory.STYLE_APPLICATION,
            {'original': original_color, 'fallback': fallback_color, 'reason': reason},
            StyleApplicationWarning
        )
    
    def get_warnings(self, category: Optional[WarningCategory] = None) -> List[Dict[str, Any]]:
        """Get all warnings, optionally filtered by category"""
        if category is None:
            return self.warnings.copy()
        return [w for w in self.warnings if w['category'] == category.value]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all warnings"""
        by_category = {}
        for warning in self.warnings:
            cat = warning['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(warning)
        
        return {
            'total_warnings': len(self.warnings),
            'by_category': {cat: len(warnings) for cat, warnings in by_category.items()},
            'categories': by_category
        }
    
    def print_summary(self):
        """Print a formatted summary of warnings"""
        if not self.warnings:
            print("✅ No warnings - conversion completed successfully!")
            return
        
        summary = self.get_summary()
        print(f"\n⚠️  Conversion completed with {summary['total_warnings']} warnings:")
        
        for category, count in summary['by_category'].items():
            print(f"  {category.replace('_', ' ').title()}: {count}")
        
        print("\nDetailed warnings:")
        for i, warning in enumerate(self.warnings, 1):
            print(f"  {i}. [{warning['category'].upper()}] {warning['message']}")
            if warning['details']:
                for key, value in warning['details'].items():
                    print(f"     {key}: {value}")
    
    def clear(self):
        """Clear all collected warnings"""
        self.warnings.clear()
    
    def enable(self):
        """Enable warning collection"""
        self._enabled = True
    
    def disable(self):
        """Disable warning collection"""
        self._enabled = False

# Global warning collector instance
_global_collector = WarningCollector()

def get_warning_collector() -> WarningCollector:
    """Get the global warning collector instance"""
    return _global_collector

def reset_warnings():
    """Reset the global warning collector"""
    global _global_collector
    _global_collector.clear()