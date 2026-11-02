"""A stylesheet's text together with the URL its relative url()s resolve against."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Stylesheet:
    css: str
    base_url: Optional[str] = None
    origin: str = "css"  # 'style' (<style>), 'link' (<link>), 'import' (@import) or 'css' (argument)
