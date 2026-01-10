"""Font registry for managing @font-face declarations."""
from typing import List, Optional

from .font_face import FontFace


class FontRegistry:
    """Registry for @font-face declarations and font resolution."""

    def __init__(self):
        self.font_faces: List[FontFace] = []

    def add_font_face(self, font_face: FontFace):
        self.font_faces.append(font_face)

    def clear(self):
        self.font_faces.clear()

    def resolve_font_family(
        self, 
        font_family_value: str, 
        weight: str = "400", 
        style: str = "normal"
    ) -> List[str]:
        """Resolve a CSS font-family value to a list of font paths/names."""
        font_names = [name.strip().strip('"\'') for name in font_family_value.split(',')]
        resolved_fonts = []

        for font_name in font_names:
            matching_font = self._find_exact_font_face(font_name)
            if matching_font:
                resolved_fonts.append(matching_font.src)
            else:
                resolved_fonts.append(font_name)

        return resolved_fonts

    def _find_exact_font_face(self, family: str) -> Optional[FontFace]:
        for font_face in self.font_faces:
            if font_face.family.lower() == family.lower():
                return font_face
        return None

    def get_font_families(self) -> List[str]:
        return list(set(font_face.family for font_face in self.font_faces))

    def __len__(self) -> int:
        return len(self.font_faces)
