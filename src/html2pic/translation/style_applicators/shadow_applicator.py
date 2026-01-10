from typing import Dict, Any

from pictex import Element

from .base_applicator import StyleApplicator
from ...warnings import get_warning_collector
from ...styling import DEFAULT_STYLES
from ..shadow_parser import ShadowParser


class ShadowApplicator(StyleApplicator):
    
    def __init__(self):
        self.warnings = get_warning_collector()
        self.parser = ShadowParser(self.warnings)
    
    def apply(self, builder: Element, styles: Dict[str, Any]) -> Element:
        box_shadow = styles.get('box-shadow', DEFAULT_STYLES['box-shadow'])
        if box_shadow == 'none':
            return builder
        
        shadows = self.parser.parse_shadows(box_shadow, include_spread=True)
        if shadows:
            builder = builder.box_shadows(*shadows)
        
        return builder
