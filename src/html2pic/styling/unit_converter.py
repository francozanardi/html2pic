"""CSS unit conversion utilities."""
from typing import Optional

from ..warnings import get_warning_collector


class UnitConverter:
    """Converts CSS units to pixels."""

    KEYWORDS = {'auto', 'none', 'inherit', 'initial', 'fit-content', 'fit-background-image'}

    def __init__(self, base_font_size: int = 16):
        self.base_font_size = base_font_size
        self.warnings = get_warning_collector()

    def to_pixels(
        self,
        value: str,
        parent_value: Optional[str] = None,
        font_size: Optional[str] = None,
    ) -> str:
        """Convert a CSS length value to pixels.

        Args:
            value: The CSS value (e.g. ``"2em"``, ``"1.5rem"``, ``"50%"``, ``"10"``).
            parent_value: Reference length that percentages resolve against. When it is
                not given (or not in pixels), percentages are returned unchanged so the
                layout engine can resolve them.
            font_size: Font size that ``em`` resolves against. Defaults to the base font size.
        """
        if not isinstance(value, str):
            return str(value)

        value = value.strip().lower()

        if value.endswith('px') or value in self.KEYWORDS:
            return value

        # 'rem' must be checked before 'em', since every rem value also ends with 'em'.
        if value.endswith('rem'):
            return self._scale(value, 3, self.base_font_size, 'REM')

        if value.endswith('em'):
            base = self._px_or_none(font_size)
            return self._scale(value, 2, base if base is not None else self.base_font_size, 'EM')

        if value.endswith('%'):
            reference = self._px_or_none(parent_value)
            if reference is None:
                return value
            return self._scale(value, 1, reference / 100, 'PERCENT')

        try:
            return f'{float(value)}px'
        except ValueError as e:
            self.warnings.warn_unexpected_error(f"Failed to convert value '{value}': {e}")
            return value

    def _scale(self, value: str, suffix_len: int, factor: float, unit_name: str) -> str:
        try:
            return f'{float(value[:-suffix_len]) * factor}px'
        except ValueError as e:
            self.warnings.warn_unexpected_error(f"Failed to convert {unit_name} value '{value}': {e}")
            return value

    @staticmethod
    def _px_or_none(value: Optional[str]) -> Optional[float]:
        if not isinstance(value, str) or not value.strip().lower().endswith('px'):
            return None
        try:
            return float(value.strip()[:-2])
        except ValueError:
            return None
