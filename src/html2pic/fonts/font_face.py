"""Font face representation."""
from dataclasses import dataclass


@dataclass
class FontFace:
    """Represents a @font-face declaration from CSS."""
    
    family: str
    src: str
    weight: str = "400"
    style: str = "normal"

    def matches(self, family: str, weight: str = "400", style: str = "normal") -> bool:
        return (
            self.family.lower() == family.lower() and
            self.weight == weight and
            self.style == style
        )
