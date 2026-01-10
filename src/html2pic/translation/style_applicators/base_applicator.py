"""Base class for style applicators."""
from abc import ABC, abstractmethod
from typing import Dict, Any

from pictex import Element


class StyleApplicator(ABC):
    """Base class for applying CSS styles to PicTex builders."""
    
    @abstractmethod
    def apply(self, builder: Element, styles: Dict[str, Any]) -> Element:
        """Apply relevant styles to the builder."""
        pass
