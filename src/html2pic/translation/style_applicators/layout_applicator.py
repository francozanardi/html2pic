"""Layout style application (flex, gap, justify, align)."""
from typing import Dict, Any, Union

from pictex import Row, Column

from .base_applicator import StyleApplicator
from ...warnings import get_warning_collector
from ...styling import DEFAULT_STYLES

class LayoutApplicator(StyleApplicator):
    """Applies flexbox layout styles to Row/Column containers."""
    
    JUSTIFY_MAPPING = {
        'flex-start': 'start', 'start': 'start',
        'center': 'center',
        'flex-end': 'end', 'end': 'end',
        'space-between': 'space-between',
        'space-around': 'space-around',
        'space-evenly': 'space-evenly',
    }
    
    ALIGN_MAPPING = {
        'flex-start': 'start', 'start': 'start',
        'center': 'center',
        'flex-end': 'end', 'end': 'end',
        'stretch': 'stretch',
    }

    def __init__(self):
        self.warnings = get_warning_collector()
    
    def apply(self, builder: Union[Row, Column], styles: Dict[str, Any]) -> Union[Row, Column]:
        builder = self._apply_gap(builder, styles)
        builder = self._apply_justify(builder, styles)
        builder = self._apply_align(builder, styles)
        builder = self._apply_wrap(builder, styles)
        return builder
    
    def _apply_gap(self, builder: Union[Row, Column], styles: Dict[str, Any]) -> Union[Row, Column]:
        gap = styles.get('gap', DEFAULT_STYLES['gap'])
        if gap.endswith('px'):
            try:
                gap_value = float(gap[:-2])
                if gap_value > 0:
                    builder = builder.gap(gap_value)
            except ValueError as e:
                self.warnings.warn_unexpected_error(f"Failed to parse PIXEL value '{gap}': {e}")
        return builder
    
    def _apply_justify(self, builder: Union[Row, Column], styles: Dict[str, Any]) -> Union[Row, Column]:
        justify = styles.get('justify-content', DEFAULT_STYLES['justify-content'])
        pictex_value = self.JUSTIFY_MAPPING.get(justify, 'start')
        return builder.justify_content(pictex_value)
    
    def _apply_align(self, builder: Union[Row, Column], styles: Dict[str, Any]) -> Union[Row, Column]:
        align = styles.get('align-items', DEFAULT_STYLES['align-items'])
        pictex_value = self.ALIGN_MAPPING.get(align, 'stretch')
        return builder.align_items(pictex_value)
    
    def _apply_wrap(self, builder: Union[Row, Column], styles: Dict[str, Any]) -> Union[Row, Column]:
        wrap = styles.get('flex-wrap', DEFAULT_STYLES['flex-wrap'])
        
        if wrap == 'wrap':
            builder = builder.flex_wrap('wrap')
        elif wrap == 'wrap-reverse':
            builder = builder.flex_wrap('wrap-reverse')
        
        return builder
