"""CSS value parsing utilities."""
from typing import Union, Optional
from ..warnings import get_warning_collector


class ValueParser:
    """Utility class for parsing CSS values."""

    warnings = get_warning_collector()
    
    @staticmethod
    def parse_pixels(value: str) -> float:
        if value.endswith('px'):
            try:
                return float(value[:-2])
            except ValueError as e:
                ValueParser.warnings.warn_unexpected_error(f"Failed to parse PIXEL value '{value}': {e}")
                return 0
        return 0
    
    @staticmethod
    def parse_dimension(value: str) -> Optional[Union[float, str]]:
        if value == 'auto':
            return None
        if value.endswith('px'):
            try:
                return float(value[:-2])
            except ValueError as e:
                ValueParser.warnings.warn_unexpected_error(f"Failed to parse PIXEL value '{value}': {e}")
                return None
        if value.endswith('%'):
            return value
        if value in ['fit-content', 'fit-background-image']:
            return value
        return None
    
    @staticmethod
    def parse_length(value: str, base_em: float = 16) -> Optional[float]:
        if value.endswith('px'):
            try:
                return float(value[:-2])
            except ValueError as e:
                ValueParser.warnings.warn_unexpected_error(f"Failed to parse PIXEL value '{value}': {e}")
                return None
        if value.endswith('em'):
            try:
                return float(value[:-2]) * base_em
            except ValueError as e:
                ValueParser.warnings.warn_unexpected_error(f"Failed to parse EM value '{value}': {e}")
                return None
        if value.endswith('rem'):
            try:
                return float(value[:-3]) * 16
            except ValueError as e:
                ValueParser.warnings.warn_unexpected_error(f"Failed to parse REM value '{value}': {e}")
                return None
        try:
            return float(value)
        except ValueError as e:
            ValueParser.warnings.warn_unexpected_error(f"Failed to parse value '{value}': {e}")
            return None
