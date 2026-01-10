"""Types of DOM nodes."""
from enum import Enum


class NodeType(Enum):
    ELEMENT = "element"
    TEXT = "text"
