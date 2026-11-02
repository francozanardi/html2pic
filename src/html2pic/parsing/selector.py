"""CSS selector parsing and matching."""
import re
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import List, Optional, Tuple

from ..dom import DOMNode


class SelectorType(Enum):
    TAG = "tag"
    CLASS = "class"
    ID = "id"
    UNIVERSAL = "*"


@dataclass
class ParsedSelector:
    """Parsed information about a single simple selector (kept for backwards compatibility)."""

    selector_type: SelectorType
    value: str

    @classmethod
    def parse(cls, selector: str) -> 'ParsedSelector':
        selector = selector.strip()

        if selector.startswith('#'):
            return cls(SelectorType.ID, selector[1:])
        elif selector.startswith('.'):
            return cls(SelectorType.CLASS, selector[1:])
        elif selector == '*':
            return cls(SelectorType.UNIVERSAL, '*')
        else:
            return cls(SelectorType.TAG, selector.lower())


class UnsupportedSelectorError(ValueError):
    """Raised when a selector uses syntax html2pic does not support."""


DESCENDANT = ' '
CHILD = '>'

_IDENT = r'-?[_a-zA-Z][\w-]*'
_TOKEN = re.compile(
    rf'(?P<ws>\s+)|(?P<child>>)|(?P<universal>\*)|(?P<tag>{_IDENT})'
    rf'|(?P<pseudo>::?(?:before|after)\b)'
    rf'|#(?P<id>{_IDENT})|\.(?P<cls>{_IDENT})|(?P<other>.)'
)
_UNSUPPORTED_HINTS = {
    ':': 'pseudo-classes and pseudo-elements other than ::before/::after',
    '[': 'attribute selectors',
    '+': 'the adjacent sibling combinator (+)',
    '~': 'the general sibling combinator (~)',
}


@dataclass
class CompoundSelector:
    """A sequence of simple selectors with no combinator, e.g. ``div.card#main``."""

    tag: Optional[str] = None
    ids: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return self.tag is None and not self.ids and not self.classes

    def matches(self, node: DOMNode) -> bool:
        if not node.is_element():
            return False
        if self.tag not in (None, '*') and node.tag != self.tag:
            return False
        if any(node.get_id() != id_ for id_ in self.ids):
            return False
        node_classes = node.get_classes()
        return all(cls in node_classes for cls in self.classes)


@dataclass
class Selector:
    """A complex selector: compound selectors joined by descendant/child combinators.

    ``parts`` is ordered left to right; each entry holds the combinator that links it
    to the previous compound (``None`` for the first one).
    """

    text: str
    parts: List[Tuple[Optional[str], CompoundSelector]]
    # 'before' or 'after' when the selector targets a pseudo-element of the matched element.
    pseudo_element: Optional[str] = None

    @property
    def specificity(self) -> Tuple[int, int, int]:
        ids = sum(len(c.ids) for _, c in self.parts)
        classes = sum(len(c.classes) for _, c in self.parts)
        tags = sum(1 for _, c in self.parts if c.tag not in (None, '*'))
        if self.pseudo_element:
            tags += 1
        return ids, classes, tags

    def matches(self, node: DOMNode) -> bool:
        return self._matches_at(node, len(self.parts) - 1)

    def _matches_at(self, node: DOMNode, index: int) -> bool:
        combinator, compound = self.parts[index]
        if not compound.matches(node):
            return False
        if index == 0:
            return True

        if combinator == CHILD:
            parent = node.parent
            return self._is_document_node(parent) and self._matches_at(parent, index - 1)

        ancestor = node.parent
        while self._is_document_node(ancestor):
            if self._matches_at(ancestor, index - 1):
                return True
            ancestor = ancestor.parent
        return False

    @staticmethod
    def _is_document_node(node: Optional[DOMNode]) -> bool:
        # The synthetic root added by the HTML parser has no parent; it is not part of
        # the user's document, so it can never satisfy an ancestor/parent constraint.
        return node is not None and node.parent is not None

    @classmethod
    def parse(cls, text: str) -> 'Selector':
        return _parse_selector(text.strip())


@lru_cache(maxsize=1024)
def _parse_selector(text: str) -> Selector:
    if not text:
        raise UnsupportedSelectorError("empty selector")

    parts: List[Tuple[Optional[str], CompoundSelector]] = []
    current = CompoundSelector()
    pending: Optional[str] = None
    pseudo: Optional[str] = None

    def flush():
        nonlocal current
        if current.is_empty():
            raise UnsupportedSelectorError(f"dangling combinator in '{text}'")
        parts.append((pending if parts else None, current))
        current = CompoundSelector()

    for match in _TOKEN.finditer(text):
        kind = match.lastgroup
        value = match.group(kind)

        if pseudo is not None:
            raise UnsupportedSelectorError(f"a pseudo-element must be the last part of '{text}'")

        if kind == 'pseudo':
            pseudo = value.lstrip(':').lower()
            if current.is_empty():
                current.tag = '*'  # '::after' alone means '*::after'
            continue

        if kind in ('ws', 'child'):
            if not current.is_empty():
                flush()
                pending = DESCENDANT
            if kind == 'child':
                if not parts or pending == CHILD:
                    raise UnsupportedSelectorError(f"misplaced '>' in '{text}'")
                pending = CHILD
            continue

        if kind == 'other':
            hint = _UNSUPPORTED_HINTS.get(value)
            if hint:
                raise UnsupportedSelectorError(f"{hint} are not supported")
            raise UnsupportedSelectorError(f"unexpected character '{value}'")

        if kind in ('universal', 'tag'):
            if current.tag is not None or current.ids or current.classes:
                raise UnsupportedSelectorError(f"type selector must come first in '{text}'")
            current.tag = value.lower()
        elif kind == 'id':
            current.ids.append(value)
        elif kind == 'cls':
            current.classes.append(value)

    flush()
    return Selector(text=text, parts=parts, pseudo_element=pseudo)


def specificity_to_int(specificity: Tuple[int, int, int]) -> int:
    """Collapse an (ids, classes, tags) specificity into a sortable integer."""
    ids, classes, tags = specificity
    return ids * 10_000 + classes * 100 + tags
