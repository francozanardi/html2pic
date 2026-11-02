"""Background style application."""
from typing import Any, Dict, Optional

from pictex import Element, SolidColor

from .base_applicator import StyleApplicator
from ..gradients import BackgroundLayers, GradientError, is_gradient, parse_gradient
from ...warnings import get_warning_collector
from ...styling import DEFAULT_STYLES


class BackgroundApplicator(StyleApplicator):
    """Applies background-color and background-image (url() images and CSS gradients)."""

    def __init__(self, loader=None):
        self.warnings = get_warning_collector()
        self.loader = loader

    def apply(self, builder: Element, styles: Dict[str, Any]) -> Element:
        color = self._background_color(styles)
        bg_image = styles.get('background-image', DEFAULT_STYLES['background-image']).strip()

        if is_gradient(bg_image):
            try:
                gradient = parse_gradient(bg_image)
            except GradientError as e:
                self.warnings.warn_style_not_applied('background-image', bg_image, 'element', str(e))
            else:
                # PicTex has a single background paint, so the color is composited under the gradient.
                return builder.background_color(BackgroundLayers(color, gradient) if color else gradient)

        if color is not None:
            builder = builder.background_color(color)

        if bg_image.startswith('url('):
            url = self._extract_url(bg_image)
            if url and self.loader is not None:
                url = self.loader.localize(url, purpose='background image')
            if url:
                size = styles.get('background-size', DEFAULT_STYLES['background-size'])
                builder = builder.background_image(url, size)
        elif bg_image != 'none' and not is_gradient(bg_image):
            self.warnings.warn_style_not_applied(
                'background-image', bg_image, 'element',
                "Only url() images and CSS gradients are supported."
            )

        return builder

    def _background_color(self, styles: Dict[str, Any]) -> Optional[SolidColor]:
        bg_color = styles.get('background-color', DEFAULT_STYLES['background-color'])
        if bg_color == 'transparent':
            return None
        try:
            return SolidColor.from_str(bg_color)
        except Exception as e:
            self.warnings.warn_unexpected_error(f"Failed to apply background-color '{bg_color}': {e}")
            return None

    def _extract_url(self, url_str: str) -> str:
        content = url_str[4:-1].strip()
        if (content.startswith('"') and content.endswith('"')) or \
           (content.startswith("'") and content.endswith("'")):
            content = content[1:-1]
        return content
