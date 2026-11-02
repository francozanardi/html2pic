"""overflow style application."""
from typing import Any, Dict

from pictex import Element

from .base_applicator import StyleApplicator
from ...warnings import get_warning_collector


class OverflowApplicator(StyleApplicator):
    """Clips content to the padding box when overflow is anything but visible.

    In a static image, ``hidden``, ``clip``, ``scroll`` and ``auto`` all look the same (no
    scrollbars). If only one axis is hidden/scroll/auto, CSS computes a ``visible`` other axis
    to ``auto``, so clipping both axes matches browsers. The exception is ``clip`` paired with
    ``visible``, which clips a single axis; PicTex cannot do that, so both axes are clipped
    and a warning is emitted.
    """

    def __init__(self):
        self.warnings = get_warning_collector()

    def apply(self, builder: Element, styles: Dict[str, Any]) -> Element:
        values = {
            styles.get(prop, 'visible').strip().lower()
            for prop in ('overflow-x', 'overflow-y')
        }
        if values == {'visible'}:
            return builder
        if values == {'clip', 'visible'}:
            self.warnings.warn_style_not_applied(
                'overflow', 'clip/visible', 'element',
                "clipping a single axis is not supported; both axes are clipped",
            )
        return builder.overflow('hidden')
